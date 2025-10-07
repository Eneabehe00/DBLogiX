"""
Servizio per il processamento delle fatture tramite API GEMINI
Gestisce l'estrazione dati, normalizzazione e aggiornamento fornitori/ingredienti
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import requests
from werkzeug.utils import secure_filename
from flask import current_app
from app.models import db, Fornitore, Ingrediente, IngredienteFornitore

logger = logging.getLogger(__name__)

class InvoiceProcessor:
    """Processore per fatture elettroniche"""
    
    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        self.data_dir = os.path.join(current_app.root_path, '..', 'data', 'fatture')
        self.metadata_file = os.path.join(self.data_dir, 'metadata.json')
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Crea le directory necessarie se non esistono"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calcola l'hash SHA256 di un file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _load_metadata(self) -> Dict:
        """Carica l'indice delle fatture"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Errore nel caricamento metadata: {e}")
                return {"invoices": [], "last_updated": None}
        return {"invoices": [], "last_updated": None}
    
    def _save_metadata(self, metadata: Dict):
        """Salva l'indice delle fatture"""
        metadata["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Errore nel salvataggio metadata: {e}")
            raise
    
    def _check_duplicate(self, file_hash: str, supplier_name: str, invoice_number: str) -> Optional[str]:
        """Controlla se la fattura è duplicata"""
        metadata = self._load_metadata()
        
        for invoice in metadata["invoices"]:
            # Controllo per hash file
            if invoice.get("file_hash") == file_hash:
                return f"File duplicato (hash: {file_hash[:8]}...)"
            
            # Controllo per fornitore + numero fattura
            if (invoice.get("supplier", {}).get("name", "").lower() == supplier_name.lower() and
                invoice.get("invoice", {}).get("number", "") == invoice_number):
                return f"Fattura duplicata: {supplier_name} - {invoice_number}"
        
        return None
    
    def _extract_data_with_gemini(self, file_path: str) -> Dict:
        """Estrae i dati dalla fattura usando l'API GEMINI"""
        
        # Prompt per l'estrazione strutturata
        prompt = """
        Analizza questa fattura PDF ed estrai i seguenti dati in formato JSON strutturato:

        {
            "supplier": {
                "name": "Nome fornitore",
                "vat_number": "Partita IVA o VAT number se presente",
                "tax_code": "Codice fiscale se presente", 
                "address": "Indirizzo completo se presente",
                "email": "Email se presente",
                "phone": "Telefono se presente",
                "iban": "IBAN se presente",
                "sdi_code": "Codice SDI se presente"
            },
            "invoice": {
                "number": "Numero fattura",
                "date": "Data fattura in formato YYYY-MM-DD",
                "due_date": "Scadenza in formato YYYY-MM-DD se presente",
                "currency": "Valuta (EUR se non specificato)",
                "subtotal": numero_senza_iva,
                "tax_amount": importo_iva,
                "total": totale_con_iva,
                "payment_terms": "Condizioni pagamento se presenti"
            },
            "items": [
                {
                    "description": "Descrizione prodotto/ingrediente",
                    "quantity": numero_quantità,
                    "unit": "Unità di misura (kg, pz, lt, etc.)",
                    "unit_price": prezzo_unitario,
                    "tax_rate": aliquota_iva_percentuale,
                    "amount": importo_totale_riga
                }
            ]
        }

        REGOLE IMPORTANTI:
        - Se un campo non è presente o non è chiaro, usa null
        - Le date devono essere in formato YYYY-MM-DD
        - I numeri devono essere numerici, non stringhe
        - Identifica ingredienti alimentari nelle righe (farina, olio, pomodori, etc.)
        - Mantieni le descrizioni originali dei prodotti
        """
        
        try:
            # Qui implementeresti la chiamata effettiva all'API GEMINI
            # Per ora simulo una risposta di esempio
            
            # TODO: Implementare chiamata reale a GEMINI API
            # response = requests.post(
            #     f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={self.gemini_api_key}",
            #     json={
            #         "contents": [{"parts": [{"text": prompt}]}],
            #         "generationConfig": {
            #             "temperature": 0.1,
            #             "maxOutputTokens": 2048
            #         }
            #     }
            # )
            
            # Simulazione risposta per sviluppo
            mock_response = {
                "supplier": {
                    "name": "Fornitore Alimentare SRL",
                    "vat_number": "IT12345678901",
                    "tax_code": None,
                    "address": "Via Roma 123, 20100 Milano MI",
                    "email": "info@fornitore.it",
                    "phone": "+39 02 1234567",
                    "iban": None,
                    "sdi_code": "ABC123"
                },
                "invoice": {
                    "number": f"FAT-{datetime.now().strftime('%Y%m%d')}-001",
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "due_date": None,
                    "currency": "EUR",
                    "subtotal": 100.00,
                    "tax_amount": 22.00,
                    "total": 122.00,
                    "payment_terms": "30 giorni"
                },
                "items": [
                    {
                        "description": "Farina 00 per pizza",
                        "quantity": 10.0,
                        "unit": "kg",
                        "unit_price": 2.50,
                        "tax_rate": 10.0,
                        "amount": 25.00
                    },
                    {
                        "description": "Olio extravergine d'oliva",
                        "quantity": 5.0,
                        "unit": "lt",
                        "unit_price": 15.00,
                        "tax_rate": 22.0,
                        "amount": 75.00
                    }
                ]
            }
            
            return mock_response
            
        except Exception as e:
            logger.error(f"Errore nell'estrazione con GEMINI: {e}")
            raise
    
    def _normalize_data(self, raw_data: Dict) -> Dict:
        """Normalizza i dati estratti"""
        try:
            normalized = {
                "supplier": {
                    "name": raw_data.get("supplier", {}).get("name"),
                    "vat_number": raw_data.get("supplier", {}).get("vat_number"),
                    "tax_code": raw_data.get("supplier", {}).get("tax_code"),
                    "address": raw_data.get("supplier", {}).get("address"),
                    "email": raw_data.get("supplier", {}).get("email"),
                    "phone": raw_data.get("supplier", {}).get("phone"),
                    "iban": raw_data.get("supplier", {}).get("iban"),
                    "sdi_code": raw_data.get("supplier", {}).get("sdi_code")
                },
                "invoice": {
                    "number": raw_data.get("invoice", {}).get("number"),
                    "date": raw_data.get("invoice", {}).get("date"),
                    "due_date": raw_data.get("invoice", {}).get("due_date"),
                    "currency": raw_data.get("invoice", {}).get("currency", "EUR"),
                    "subtotal": self._safe_decimal(raw_data.get("invoice", {}).get("subtotal")),
                    "tax_amount": self._safe_decimal(raw_data.get("invoice", {}).get("tax_amount")),
                    "total": self._safe_decimal(raw_data.get("invoice", {}).get("total")),
                    "payment_terms": raw_data.get("invoice", {}).get("payment_terms")
                },
                "items": []
            }
            
            # Normalizza le righe
            for item in raw_data.get("items", []):
                normalized_item = {
                    "description": item.get("description"),
                    "quantity": self._safe_decimal(item.get("quantity")),
                    "unit": item.get("unit"),
                    "unit_price": self._safe_decimal(item.get("unit_price")),
                    "tax_rate": self._safe_decimal(item.get("tax_rate")),
                    "amount": self._safe_decimal(item.get("amount"))
                }
                normalized["items"].append(normalized_item)
            
            return normalized
            
        except Exception as e:
            logger.error(f"Errore nella normalizzazione: {e}")
            raise
    
    def _safe_decimal(self, value) -> Optional[float]:
        """Converte un valore in decimal in modo sicuro"""
        if value is None:
            return None
        try:
            return float(Decimal(str(value)))
        except:
            return None
    
    def _update_suppliers_and_ingredients(self, normalized_data: Dict, invoice_file: str) -> List[str]:
        """Aggiorna fornitori e ingredienti nel database"""
        updates_log = []
        
        try:
            supplier_data = normalized_data.get("supplier", {})
            supplier_name = supplier_data.get("name")
            
            if not supplier_name:
                return updates_log
            
            # Cerca o crea il fornitore
            fornitore = Fornitore.query.filter_by(nome=supplier_name).first()
            
            if not fornitore:
                # Crea nuovo fornitore
                fornitore = Fornitore(
                    nome=supplier_name,
                    email=supplier_data.get("email", ""),
                    telefono=supplier_data.get("phone", ""),
                    indirizzo=supplier_data.get("address", ""),
                    partita_iva=supplier_data.get("vat_number", ""),
                    codice_fiscale=supplier_data.get("tax_code", ""),
                    iban=supplier_data.get("iban", ""),
                    note=f"Creato automaticamente da fattura: {os.path.basename(invoice_file)}",
                    attivo=True
                )
                db.session.add(fornitore)
                db.session.flush()  # Per ottenere l'ID
                updates_log.append(f"Creato nuovo fornitore: {supplier_name}")
            else:
                # Aggiorna fornitore esistente con dati mancanti
                updated_fields = []
                if not fornitore.email and supplier_data.get("email"):
                    fornitore.email = supplier_data.get("email")
                    updated_fields.append("email")
                if not fornitore.telefono and supplier_data.get("phone"):
                    fornitore.telefono = supplier_data.get("phone")
                    updated_fields.append("telefono")
                if not fornitore.indirizzo and supplier_data.get("address"):
                    fornitore.indirizzo = supplier_data.get("address")
                    updated_fields.append("indirizzo")
                if not fornitore.partita_iva and supplier_data.get("vat_number"):
                    fornitore.partita_iva = supplier_data.get("vat_number")
                    updated_fields.append("P.IVA")
                
                if updated_fields:
                    fornitore.updated_at = datetime.utcnow()
                    updates_log.append(f"Aggiornato fornitore {supplier_name}: {', '.join(updated_fields)}")
            
            # Processa gli ingredienti dalle righe fattura
            for item in normalized_data.get("items", []):
                description = item.get("description", "").strip()
                unit_price = item.get("unit_price")
                unit = item.get("unit", "kg")
                
                if not description or not unit_price:
                    continue
                
                # Cerca ingrediente esistente (match fuzzy sul nome)
                ingrediente = self._find_or_create_ingredient(description, unit)
                
                if ingrediente:
                    # Gestisci associazione ingrediente-fornitore
                    association_log = self._manage_ingredient_supplier_association(
                        ingrediente, fornitore, unit_price, invoice_file
                    )
                    updates_log.extend(association_log)
            
            db.session.commit()
            return updates_log
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore nell'aggiornamento fornitori/ingredienti: {e}")
            updates_log.append(f"ERRORE: {str(e)}")
            return updates_log
    
    def _find_or_create_ingredient(self, description: str, unit: str) -> Optional[Ingrediente]:
        """Trova o crea un ingrediente basandosi sulla descrizione"""
        
        # Prima cerca per nome esatto
        ingrediente = Ingrediente.query.filter(
            Ingrediente.nome.ilike(f"%{description}%")
        ).first()
        
        if not ingrediente:
            # Crea nuovo ingrediente
            ingrediente = Ingrediente(
                nome=description,
                descrizione=f"Creato automaticamente da fattura",
                unita_misura=unit,
                categoria="Importato",
                attivo=True
            )
            db.session.add(ingrediente)
            db.session.flush()
        
        return ingrediente
    
    def _manage_ingredient_supplier_association(self, ingrediente: Ingrediente, fornitore: Fornitore, 
                                               unit_price: float, invoice_file: str) -> List[str]:
        """Gestisce l'associazione ingrediente-fornitore e aggiornamento prezzi"""
        updates_log = []
        
        try:
            # Cerca associazione esistente
            associazione = IngredienteFornitore.query.filter_by(
                ingrediente_id=ingrediente.id,
                fornitore_id=fornitore.id
            ).first()
            
            if not associazione:
                # Crea nuova associazione
                associazione = IngredienteFornitore(
                    ingrediente_id=ingrediente.id,
                    fornitore_id=fornitore.id,
                    prezzo_unitario=Decimal(str(unit_price)),
                    note=f"Prezzo da fattura: {os.path.basename(invoice_file)}",
                    attivo=True
                )
                db.session.add(associazione)
                updates_log.append(f"Nuova associazione: {ingrediente.nome} ← {fornitore.nome} (€{unit_price:.2f})")
                
                # Imposta come fornitore preferito se è il primo
                if not ingrediente.fornitore_preferito_id:
                    ingrediente.fornitore_preferito_id = fornitore.id
                    updates_log.append(f"Fornitore {fornitore.nome} impostato come preferito per {ingrediente.nome}")
            
            else:
                # Aggiorna prezzo esistente
                old_price = float(associazione.prezzo_unitario)
                new_price = float(unit_price)
                
                if abs(old_price - new_price) > 0.01:  # Soglia di 1 centesimo
                    # Registra storico prezzi
                    self._log_price_change(ingrediente, fornitore, old_price, new_price, invoice_file)
                    
                    associazione.prezzo_unitario = Decimal(str(unit_price))
                    associazione.updated_at = datetime.utcnow()
                    associazione.note = f"Aggiornato da fattura: {os.path.basename(invoice_file)}"
                    
                    updates_log.append(
                        f"Aggiornato prezzo {ingrediente.nome} da {fornitore.nome}: "
                        f"€{old_price:.2f} → €{new_price:.2f}"
                    )
                
                # Riattiva se era disattivata
                if not associazione.attivo:
                    associazione.attivo = True
                    updates_log.append(f"Riattivata associazione: {ingrediente.nome} ← {fornitore.nome}")
            
            return updates_log
            
        except Exception as e:
            logger.error(f"Errore nella gestione associazione: {e}")
            return [f"ERRORE associazione {ingrediente.nome}: {str(e)}"]
    
    def _log_price_change(self, ingrediente: Ingrediente, fornitore: Fornitore, 
                         old_price: float, new_price: float, invoice_file: str):
        """Registra il cambio di prezzo nello storico"""
        
        # Crea entry di log nello storico prezzi (file JSON)
        price_history_file = os.path.join(self.data_dir, 'price_history.json')
        
        try:
            if os.path.exists(price_history_file):
                with open(price_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = {"changes": []}
            
            history["changes"].append({
                "timestamp": datetime.now().isoformat(),
                "ingredient_id": ingrediente.id,
                "ingredient_name": ingrediente.nome,
                "supplier_id": fornitore.id,
                "supplier_name": fornitore.nome,
                "old_price": old_price,
                "new_price": new_price,
                "change_percent": ((new_price - old_price) / old_price * 100) if old_price > 0 else 0,
                "source_invoice": os.path.basename(invoice_file)
            })
            
            with open(price_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Errore nel log dello storico prezzi: {e}")
    
    def process_invoice(self, file_path: str, original_filename: str) -> Dict:
        """Processa una fattura completa"""
        
        result = {
            "success": False,
            "file_hash": None,
            "duplicate": None,
            "raw_data": None,
            "normalized_data": None,
            "updates_log": [],
            "error": None
        }
        
        try:
            # Calcola hash del file
            file_hash = self._calculate_file_hash(file_path)
            result["file_hash"] = file_hash
            
            # Estrai dati con GEMINI
            logger.info(f"Estraendo dati da {original_filename}")
            raw_data = self._extract_data_with_gemini(file_path)
            result["raw_data"] = raw_data
            
            # Normalizza dati
            normalized_data = self._normalize_data(raw_data)
            result["normalized_data"] = normalized_data
            
            # Controlla duplicati
            supplier_name = normalized_data.get("supplier", {}).get("name", "")
            invoice_number = normalized_data.get("invoice", {}).get("number", "")
            
            duplicate_check = self._check_duplicate(file_hash, supplier_name, invoice_number)
            if duplicate_check:
                result["duplicate"] = duplicate_check
                result["success"] = True  # Tecnicamente è successo, ma è duplicato
                return result
            
            # Aggiorna fornitori e ingredienti
            updates_log = self._update_suppliers_and_ingredients(normalized_data, file_path)
            result["updates_log"] = updates_log
            
            # Salva file JSON
            base_name = os.path.splitext(file_path)[0]
            
            # Salva raw data
            with open(f"{base_name}.raw.json", 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
            
            # Salva normalized data
            with open(f"{base_name}.norm.json", 'w', encoding='utf-8') as f:
                json.dump(normalized_data, f, indent=2, ensure_ascii=False)
            
            # Aggiorna metadata
            metadata = self._load_metadata()
            invoice_entry = {
                "id": file_hash[:12],  # Primi 12 caratteri dell'hash come ID
                "filename": original_filename,
                "file_path": os.path.relpath(file_path, self.data_dir),
                "file_hash": file_hash,
                "uploaded_at": datetime.now().isoformat(),
                "processed_at": datetime.now().isoformat(),
                "status": "processed",
                "supplier": normalized_data.get("supplier", {}),
                "invoice": normalized_data.get("invoice", {}),
                "items_count": len(normalized_data.get("items", [])),
                "updates_count": len(updates_log),
                "error": None
            }
            
            metadata["invoices"].append(invoice_entry)
            self._save_metadata(metadata)
            
            result["success"] = True
            logger.info(f"Fattura {original_filename} processata con successo")
            
        except Exception as e:
            logger.error(f"Errore nel processamento di {original_filename}: {e}")
            result["error"] = str(e)
            
            # Aggiorna metadata con errore
            try:
                metadata = self._load_metadata()
                invoice_entry = {
                    "id": file_hash[:12] if file_hash else f"error_{int(datetime.now().timestamp())}",
                    "filename": original_filename,
                    "file_path": os.path.relpath(file_path, self.data_dir) if os.path.exists(file_path) else None,
                    "file_hash": file_hash,
                    "uploaded_at": datetime.now().isoformat(),
                    "processed_at": None,
                    "status": "error",
                    "supplier": {},
                    "invoice": {},
                    "items_count": 0,
                    "updates_count": 0,
                    "error": str(e)
                }
                metadata["invoices"].append(invoice_entry)
                self._save_metadata(metadata)
            except:
                pass  # Non fallire se non riusciamo a salvare i metadata
        
        return result
    
    def get_invoices_list(self, search: str = "", supplier_filter: str = "", 
                         date_from: str = "", date_to: str = "", 
                         status_filter: str = "") -> List[Dict]:
        """Ottiene la lista delle fatture con filtri"""
        
        metadata = self._load_metadata()
        invoices = metadata.get("invoices", [])
        
        # Applica filtri
        if search:
            search_lower = search.lower()
            invoices = [inv for inv in invoices if 
                       search_lower in inv.get("filename", "").lower() or
                       search_lower in inv.get("supplier", {}).get("name", "").lower() or
                       search_lower in inv.get("invoice", {}).get("number", "").lower()]
        
        if supplier_filter:
            invoices = [inv for inv in invoices if 
                       supplier_filter.lower() in inv.get("supplier", {}).get("name", "").lower()]
        
        if status_filter:
            invoices = [inv for inv in invoices if inv.get("status") == status_filter]
        
        if date_from:
            invoices = [inv for inv in invoices if 
                       inv.get("invoice", {}).get("date", "") >= date_from]
        
        if date_to:
            invoices = [inv for inv in invoices if 
                       inv.get("invoice", {}).get("date", "") <= date_to]
        
        # Ordina per data di upload (più recenti primi)
        invoices.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
        
        return invoices
    
    def get_invoice_detail(self, invoice_id: str) -> Optional[Dict]:
        """Ottiene il dettaglio di una fattura"""
        
        metadata = self._load_metadata()
        invoices = metadata.get("invoices", [])
        
        invoice = next((inv for inv in invoices if inv.get("id") == invoice_id), None)
        if not invoice:
            return None
        
        # Carica i dati completi dai file JSON
        file_path = os.path.join(self.data_dir, invoice["file_path"])
        base_name = os.path.splitext(file_path)[0]
        
        try:
            # Carica raw data
            raw_file = f"{base_name}.raw.json"
            if os.path.exists(raw_file):
                with open(raw_file, 'r', encoding='utf-8') as f:
                    invoice["raw_data"] = json.load(f)
            
            # Carica normalized data
            norm_file = f"{base_name}.norm.json"
            if os.path.exists(norm_file):
                with open(norm_file, 'r', encoding='utf-8') as f:
                    invoice["normalized_data"] = json.load(f)
            
            # Carica log di processing se esiste
            log_file = f"{base_name}.log.json"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    invoice["processing_log"] = json.load(f)
            
        except Exception as e:
            logger.error(f"Errore nel caricamento dettagli fattura {invoice_id}: {e}")
        
        return invoice
    
    def delete_invoice(self, invoice_id: str) -> bool:
        """Elimina una fattura e tutti i file associati"""
        
        try:
            metadata = self._load_metadata()
            invoices = metadata.get("invoices", [])
            
            invoice = next((inv for inv in invoices if inv.get("id") == invoice_id), None)
            if not invoice:
                return False
            
            # Rimuovi file PDF e JSON associati
            file_path = os.path.join(self.data_dir, invoice["file_path"])
            base_name = os.path.splitext(file_path)[0]
            
            files_to_remove = [
                file_path,  # PDF
                f"{base_name}.raw.json",
                f"{base_name}.norm.json",
                f"{base_name}.log.json"
            ]
            
            for file_to_remove in files_to_remove:
                if os.path.exists(file_to_remove):
                    os.remove(file_to_remove)
            
            # Rimuovi dall'indice
            metadata["invoices"] = [inv for inv in invoices if inv.get("id") != invoice_id]
            self._save_metadata(metadata)
            
            logger.info(f"Fattura {invoice_id} eliminata con successo")
            return True
            
        except Exception as e:
            logger.error(f"Errore nell'eliminazione fattura {invoice_id}: {e}")
            return False
    
    def reprocess_invoice(self, invoice_id: str) -> Dict:
        """Riprocessa una fattura esistente"""
        
        invoice = self.get_invoice_detail(invoice_id)
        if not invoice:
            return {"success": False, "error": "Fattura non trovata"}
        
        file_path = os.path.join(self.data_dir, invoice["file_path"])
        if not os.path.exists(file_path):
            return {"success": False, "error": "File PDF non trovato"}
        
        # Riprocessa
        result = self.process_invoice(file_path, invoice["filename"])
        
        # Aggiorna metadata
        if result["success"]:
            metadata = self._load_metadata()
            invoices = metadata.get("invoices", [])
            
            for i, inv in enumerate(invoices):
                if inv.get("id") == invoice_id:
                    invoices[i].update({
                        "processed_at": datetime.now().isoformat(),
                        "status": "processed" if not result.get("duplicate") else "duplicate",
                        "updates_count": len(result.get("updates_log", [])),
                        "error": None
                    })
                    break
            
            self._save_metadata(metadata)
        
        return result
