"""
DBLogiX - PDF Invoice Processing Service
Sistema per l'elaborazione automatica di fatture PDF e aggiornamento ingredienti/fornitori
"""

import os
import re
import pdfplumber
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process
import logging
from datetime import datetime
from flask import has_app_context, current_app

from app.models import db, Ingrediente, Fornitore, IngredienteFornitore
from .invoice_parser import InvoiceParserService

logger = logging.getLogger(__name__)

class PDFInvoiceProcessor:
    """Classe principale per l'elaborazione delle fatture PDF con database integration"""
    
    def __init__(self):
        self.parser = InvoiceParserService()
        
        # Manteniamo per compatibilità con codice esistente
        self.food_keywords = self.parser.food_keywords
    
    def _ensure_flask_context(self):
        """Verifica che siamo in un contesto Flask valido"""
        if not has_app_context():
            raise RuntimeError(
                "PDFInvoiceProcessor deve essere utilizzato all'interno di un contesto Flask valido. "
                "Assicurati che venga chiamato da una view o da un endpoint API Flask."
            )
        return True
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Estrae tutto il testo dal PDF - Wrapper per compatibilità"""
        return self.parser.extract_text_from_pdf(pdf_path)
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[List[List]]:
        """Estrae le tabelle dal PDF - Wrapper per compatibilità"""
        return self.parser.extract_tables_from_pdf(pdf_path)
    
    def extract_supplier_info(self, text: str) -> Dict[str, str]:
        """Estrae informazioni del fornitore dal testo"""
        supplier_info = {
            'nome': '',
            'email': '',
            'telefono': '',
            'indirizzo': '',
            'partita_iva': '',
            'codice_fiscale': ''
        }
        
        lines = text.split('\n')
        
        # Pattern per email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Pattern per telefono
        phone_pattern = r'(?:\+39\s?)?(?:\d{3}\s?\d{3}\s?\d{4}|\d{3}\.\d{3}\.\d{4}|\d{10})'
        
        # Pattern per P.IVA (formato italiano)
        piva_pattern = r'(?:P\.?\s*IVA|PARTITA\s*IVA)[\s:]*(\d{11})'
        
        # Pattern per Codice Fiscale
        cf_pattern = r'(?:C\.?\s*F\.|CODICE\s*FISCALE)[\s:]*([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])'
        
        # Parole chiave da ignorare per il nome fornitore
        ignore_keywords = [
            'cedente', 'prestatore', 'fornitore', 'supplier', 'venditore', 'seller', 
            'fattura da', 'invoice from', 'ragione sociale', 'denominazione',
            'dati del fornitore', 'dati fornitore', 'intestazione', 'header'
        ]
        
        # Prima passa: cerca P.IVA e Codice Fiscale per avere riferimenti
        for line in lines:
            line_upper = line.upper()
            
            # Cerca P.IVA
            piva_match = re.search(piva_pattern, line_upper)
            if piva_match and not supplier_info['partita_iva']:
                supplier_info['partita_iva'] = piva_match.group(1)
            
            # Cerca Codice Fiscale
            cf_match = re.search(cf_pattern, line_upper)
            if cf_match and not supplier_info['codice_fiscale']:
                supplier_info['codice_fiscale'] = cf_match.group(1)
            
            # Cerca email
            email_match = re.search(email_pattern, line)
            if email_match and not supplier_info['email']:
                supplier_info['email'] = email_match.group(0)
            
            # Cerca telefono
            phone_match = re.search(phone_pattern, line)
            if phone_match and not supplier_info['telefono']:
                supplier_info['telefono'] = phone_match.group(0)
            
            # Cerca indirizzo (linea che contiene numeri civici, CAP, città)
            if not supplier_info['indirizzo'] and re.search(r'\d{5}|\d{1,4}\s+[A-Za-z]', line):
                supplier_info['indirizzo'] = line.strip()
        
        # Seconda passa: cerca nome fornitore usando strategie multiple
        supplier_candidates = []
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            line_upper = line.upper()
            
            if len(line_clean) < 3:
                continue
            
            # Salta righe che sono chiaramente intestazioni generiche
            if any(ignore_word in line_upper for ignore_word in ignore_keywords):
                continue
            
            # Salta righe che sono solo numeri o date
            if re.match(r'^[\d\s\-\/\.]+$', line_clean):
                continue
                
            # Salta righe che contengono solo P.IVA o CF
            if re.search(r'^(?:P\.?\s*IVA|PARTITA\s*IVA|C\.?\s*F\.|CODICE\s*FISCALE)', line_upper):
                continue
            
            # Candidati con alta priorità: righe con forme societarie
            if any(keyword in line_upper for keyword in ['S.R.L.', 'S.P.A.', 'S.N.C.', 'S.A.S.', 'S.R.L', 'S.P.A', 'S.N.C', 'S.A.S']):
                supplier_candidates.append(('high', line_clean, i))
            
            # Candidati con media priorità: righe nelle prime posizioni che sembrano nomi aziendali
            elif i < 15 and len(line_clean) > 5:
                # Verifica che non sia solo testo generico
                if not re.search(r'^(via|v\.le|corso|piazza|c\.so)', line_upper):  # Non indirizzi
                    # Ha caratteristiche di nome aziendale
                    word_count = len(line_clean.split())
                    if 1 <= word_count <= 6 and not line_clean.isdigit():
                        supplier_candidates.append(('medium', line_clean, i))
            
            # Candidati con bassa priorità: righe che potrebbero essere nomi
            elif 5 < i < 20 and 3 < len(line_clean) < 80:
                if not any(char in line_clean for char in ['@', 'www', 'http']):  # Non email o siti
                    supplier_candidates.append(('low', line_clean, i))
        
        # Seleziona il miglior candidato
        if supplier_candidates:
            # Ordina per priorità e posizione nel testo
            supplier_candidates.sort(key=lambda x: (
                {'high': 0, 'medium': 1, 'low': 2}[x[0]], 
                x[2]  # posizione nel testo
            ))
            
            best_candidate = supplier_candidates[0][1]
            supplier_info['nome'] = best_candidate
            logger.info(f"Nome fornitore selezionato: '{best_candidate}' (candidati totali: {len(supplier_candidates)})")
        
        # Se ancora non abbiamo un nome, prova estratti dalle prime righe valide
        if not supplier_info['nome']:
            for i, line in enumerate(lines[:20]):
                line_clean = line.strip()
                if (len(line_clean) > 3 and 
                    not any(ignore_word in line_clean.upper() for ignore_word in ignore_keywords) and
                    not re.match(r'^[\d\s\-\/\.]+$', line_clean)):
                    supplier_info['nome'] = line_clean
                    logger.info(f"Nome fornitore di fallback: '{line_clean}'")
                    break
        
        logger.info(f"Info fornitore estratte: {supplier_info}")
        return supplier_info
    
    def extract_items_from_tables(self, tables: List[List[List]]) -> List[Dict]:
        """Estrae gli articoli/ingredienti dalle tabelle"""
        items = []
        
        logger.info(f"📊 Analisi {len(tables)} tabelle trovate nel PDF")
        
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:
                logger.info(f"   ⏭️ Tabella {table_idx+1} saltata: troppo piccola ({len(table) if table else 0} righe)")
                continue
            
            logger.info(f"🔍 Analisi tabella {table_idx+1}: {len(table)} righe, {len(table[0]) if table[0] else 0} colonne")
            
            # Analizza l'header per identificare le colonne
            header = table[0] if table[0] else []
            header_lower = [str(col).lower() if col else '' for col in header]
            
            logger.info(f"   📋 Header: {header}")
            
            # Trova gli indici delle colonne importanti con logging esteso
            desc_idx = self._find_column_index(header_lower, ['descrizione', 'description', 'prodotto', 'articolo', 'desc'])
            qty_idx = self._find_column_index(header_lower, ['quantità', 'quantity', 'qta', 'qt', 'q.tà'])
            price_idx = self._find_column_index(header_lower, ['prezzo', 'price', 'unitario', 'costo', 'euro'])
            total_idx = self._find_column_index(header_lower, ['importo', 'total', 'totale', 'imponibile'])
            
            logger.info(f"   🗂️ Indici colonne - Desc: {desc_idx}, Qty: {qty_idx}, Price: {price_idx}, Total: {total_idx}")
            
            # Se non trova colonna descrizione, prova colonne alternative
            if desc_idx is None:
                # Prova la prima colonna che contiene testo significativo
                for i, col in enumerate(header_lower):
                    if len(col) > 2 and not col.isdigit():
                        desc_idx = i
                        logger.info(f"   📝 Usando colonna {i} come descrizione: '{header[i]}'")
                        break
            
            table_items_count = 0
            
            # Processa le righe della tabella
            for row_idx, row in enumerate(table[1:], 1):
                if not row or len(row) == 0:
                    continue
                
                logger.info(f"   🔄 Riga {row_idx}: {row}")
                
                # Estrae descrizione
                description = ''
                if desc_idx is not None and desc_idx < len(row):
                    raw_desc = row[desc_idx]
                    description = str(raw_desc).strip() if raw_desc is not None else ''
                
                # Salta righe senza descrizione o con descrizioni troppo corte
                if not description or len(description) < 3:
                    logger.info(f"   ⏭️ Riga saltata: descrizione troppo corta o mancante ('{description}')")
                    continue
                
                # Salta righe che sembrano essere totali o intestazioni
                if any(word in description.lower() for word in ['totale', 'subtotale', 'total', 'iva', 'imposta', 'sconto']):
                    logger.info(f"   ⏭️ Riga saltata: sembra un totale ('{description}')")
                    continue
                
                # Verifica se la descrizione contiene più articoli separati
                split_descriptions = self._split_multiple_items(description)
                
                for single_desc in split_descriptions:
                    # Estrae quantità
                    quantity = None
                    if qty_idx is not None and qty_idx < len(row):
                        qty_str = str(row[qty_idx]).strip() if row[qty_idx] is not None else ''
                        quantity = self._parse_number(qty_str)
                    
                    # Estrae prezzo unitario
                    unit_price = None
                    if price_idx is not None and price_idx < len(row):
                        price_str = str(row[price_idx]).strip() if row[price_idx] is not None else ''
                        unit_price = self._parse_number(price_str)
                    
                    # Estrae totale
                    total_amount = None
                    if total_idx is not None and total_idx < len(row):
                        total_str = str(row[total_idx]).strip() if row[total_idx] is not None else ''
                        total_amount = self._parse_number(total_str)
                    
                    # Calcola prezzo unitario se mancante
                    if unit_price is None and quantity and total_amount and quantity > 0:
                        unit_price = total_amount / quantity
                    
                    # Se abbiamo diviso la descrizione, dividi anche i prezzi proporzionalmente
                    if len(split_descriptions) > 1:
                        if total_amount:
                            total_amount = total_amount / len(split_descriptions)
                        if not unit_price and total_amount and quantity:
                            unit_price = total_amount / (quantity / len(split_descriptions))
                    
                    # Determina se è probabilmente un ingrediente alimentare
                    is_food_ingredient = self._is_food_ingredient(single_desc)
                    
                    item = {
                        'descrizione': single_desc,
                        'quantita': float(quantity) if quantity else 0.0,
                        'prezzo_unitario': float(unit_price) if unit_price else 0.0,
                        'importo_totale': float(total_amount) if total_amount else 0.0,
                        'is_food_ingredient': is_food_ingredient,
                        'unita_misura': self._guess_unit_of_measure(single_desc)
                    }
                    
                    items.append(item)
                    table_items_count += 1
                    
                    logger.info(f"   ✅ Articolo estratto: '{single_desc}' - €{item['prezzo_unitario']:.2f} ({'alimentare' if is_food_ingredient else 'non alimentare'})")
            
            logger.info(f"   📊 Tabella {table_idx+1} completata: {table_items_count} articoli estratti")
        
        logger.info(f"✅ Estrazione completata: {len(items)} articoli totali dalle tabelle")
        return items
    
    def _split_multiple_items(self, description: str) -> List[str]:
        """Divide una descrizione che potrebbe contenere più articoli"""
        if not description:
            return []
        
        # Separatori comuni per articoli multipli
        separators = ['\n', ';', ' - ', ' + ', '|', ' / ']
        
        # Prova a dividere usando i separatori
        items = [description]
        
        for separator in separators:
            if separator in description:
                # Split e pulisci ogni parte
                split_items = []
                for item in items:
                    parts = item.split(separator)
                    for part in parts:
                        part = part.strip()
                        if len(part) > 2:  # Solo parti significative
                            split_items.append(part)
                items = split_items
                break  # Usa solo il primo separatore che funziona
        
        # Se trovato solo un articolo, verifica se contiene pattern multipli
        if len(items) == 1:
            # Pattern per identificare liste (es: "1) Item A 2) Item B")
            if re.search(r'\d+\)\s*[^)]+\d+\)\s*', description):
                items = re.findall(r'\d+\)\s*([^)]+?)(?=\d+\)|$)', description)
                items = [item.strip() for item in items if len(item.strip()) > 2]
        
        # Limita il numero di articoli per evitare splitting eccessivo
        if len(items) > 10:
            logger.warning(f"   ⚠️ Troppe divisioni ({len(items)}), mantengo originale")
            return [description]
        
        if len(items) > 1:
            logger.info(f"   ✂️ Descrizione divisa in {len(items)} articoli: {items}")
        
        return items if items else [description]
    
    def _find_column_index(self, header: List[str], keywords: List[str]) -> Optional[int]:
        """Trova l'indice della colonna basandosi su parole chiave"""
        for i, col in enumerate(header):
            for keyword in keywords:
                if keyword in col:
                    return i
        return None
    
    def _parse_number(self, text: str) -> Optional[Decimal]:
        """Converte una stringa in numero decimale"""
        if not text:
            return None
        
        # Rimuove caratteri non numerici eccetto virgole, punti e segni
        cleaned = re.sub(r'[^\d,.-]', '', text)
        
        if not cleaned:
            return None
        
        # Gestisce formati numerici italiani (virgola come decimale)
        if ',' in cleaned and '.' in cleaned:
            # Formato 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        elif ',' in cleaned:
            # Formato 123,56
            cleaned = cleaned.replace(',', '.')
        
        try:
            return Decimal(cleaned)
        except:
            return None
    
    def _is_food_ingredient(self, description: str) -> bool:
        """Determina se un articolo è probabilmente un ingrediente alimentare"""
        desc_lower = description.lower()
        
        # Controlla se contiene parole chiave alimentari
        for keyword in self.food_keywords:
            if keyword in desc_lower:
                return True
        
        # Controlla pattern comuni (kg, lt, pz per alimenti, ecc.)
        if re.search(r'\b(kg|lt|pz|conf|confezione|scatola)\b', desc_lower):
            return True
        
        return False
    
    def _guess_unit_of_measure(self, description: str) -> str:
        """Indovina l'unità di misura dalla descrizione"""
        desc_lower = description.lower()
        
        if re.search(r'\b(kg|chilo|chilogrammo)\b', desc_lower):
            return 'kg'
        elif re.search(r'\b(lt|litro|litri)\b', desc_lower):
            return 'lt'
        elif re.search(r'\b(pz|pezzo|pezzi)\b', desc_lower):
            return 'pz'
        elif re.search(r'\b(conf|confezione|confezioni)\b', desc_lower):
            return 'conf'
        else:
            return 'kg'  # Default
    
    def find_or_create_supplier(self, supplier_json: Dict[str, any]) -> Optional[Fornitore]:
        """Trova un fornitore esistente o ne crea uno nuovo dal JSON del parser"""
        # Verifica contesto Flask
        self._ensure_flask_context()
        
        # Adatta dal nuovo formato JSON
        supplier_info = supplier_json
        if not supplier_info.get('denominazione'):
            logger.warning("Denominazione fornitore mancante nelle informazioni estratte")
            return None
        
        nome = supplier_info['denominazione'].strip()
        partita_iva = supplier_info.get('partita_iva', '').strip()
        codice_fiscale = supplier_info.get('codice_fiscale', '').strip()
        
        logger.info(f"Ricerca fornitore: {nome}")
        logger.info(f"   P.IVA: {partita_iva}")
        logger.info(f"   CF: {codice_fiscale}")
        
        existing_supplier = None
        
        try:
            # 1° Priorità: Cerca per P.IVA se presente
            if partita_iva:
                existing_supplier = Fornitore.query.filter(
                    Fornitore.partita_iva == partita_iva,
                    Fornitore.attivo == True
                ).first()
                
                if existing_supplier:
                    logger.info(f"✅ Trovato fornitore esistente tramite P.IVA: {existing_supplier.nome} (ID: {existing_supplier.id})")
                    self._update_supplier_info(existing_supplier, supplier_info)
                    return existing_supplier
            
            # 2° Priorità: Cerca per Codice Fiscale se presente
            if codice_fiscale:
                existing_supplier = Fornitore.query.filter(
                    Fornitore.codice_fiscale == codice_fiscale,
                    Fornitore.attivo == True
                ).first()
                
                if existing_supplier:
                    logger.info(f"✅ Trovato fornitore esistente tramite CF: {existing_supplier.nome} (ID: {existing_supplier.id})")
                    self._update_supplier_info(existing_supplier, supplier_info)
                    return existing_supplier
            
            # 3° Priorità: Cerca per nome esatto (case insensitive)
            existing_supplier = Fornitore.query.filter(
                db.func.lower(Fornitore.nome) == nome.lower(),
                Fornitore.attivo == True
            ).first()
                
            if existing_supplier:
                logger.info(f"✅ Trovato fornitore esistente tramite nome: {existing_supplier.nome} (ID: {existing_supplier.id})")
                self._update_supplier_info(existing_supplier, supplier_info)
                return existing_supplier
            
            # 4° Priorità: Cerca match simili usando fuzzy matching sui nomi
            all_suppliers = Fornitore.query.filter_by(attivo=True).all()
            supplier_names = [s.nome for s in all_suppliers]
            
            if supplier_names:
                # rapidfuzz.process.extractOne restituisce (match, score, index) o None
                result = process.extractOne(nome, supplier_names)
                if result is not None:
                    match, score, _ = result  # Ignoriamo l'index (terzo valore)
                    if score >= 85:  # Soglia di similarità alta
                        matching_supplier = next(s for s in all_suppliers if s.nome == match)
                        logger.info(f"🔍 Trovato fornitore simile tramite fuzzy matching: {match} (score: {score}) - ID: {matching_supplier.id}")
                        self._update_supplier_info(matching_supplier, supplier_info)
                        return matching_supplier
            
        except Exception as query_error:
            logger.error(f"❌ Errore durante la query del fornitore: {query_error}")
            raise query_error
        
        # Se non trova match, crea nuovo fornitore
        try:
            logger.info(f"🆕 Creazione nuovo fornitore: {nome}")
            
            new_supplier = Fornitore(
                nome=nome,
                email=supplier_info.get('email', '').strip(),
                telefono=supplier_info.get('telefono', '').strip(),
                indirizzo=supplier_info.get('indirizzo', '').strip(),
                partita_iva=partita_iva,
                codice_fiscale=codice_fiscale,
                attivo=True
            )
            
            db.session.add(new_supplier)
            db.session.flush()  # Per ottenere l'ID senza fare commit completo
            
            logger.info(f"✅ Creato nuovo fornitore: {nome} (ID: {new_supplier.id})")
            logger.info(f"   Email: {new_supplier.email}")
            logger.info(f"   Tel: {new_supplier.telefono}")
            logger.info(f"   P.IVA: {new_supplier.partita_iva}")
            logger.info(f"   CF: {new_supplier.codice_fiscale}")
            
            return new_supplier
        
        except Exception as e:
            logger.error(f"❌ Errore nella creazione del fornitore {nome}: {str(e)}", exc_info=True)
            db.session.rollback()
            return None
    
    def _update_supplier_info(self, supplier: Fornitore, supplier_info: Dict[str, str]) -> None:
        """Aggiorna le informazioni del fornitore se mancanti"""
        updated = False
        
        # Aggiorna nome se quello nuovo è più specifico (contiene forme societarie)
        new_name = supplier_info.get('nome', '').strip()
        if (new_name and len(new_name) > len(supplier.nome) and
            any(keyword in new_name.upper() for keyword in ['S.R.L.', 'S.P.A.', 'S.N.C.', 'S.A.S.', 'SRL', 'SPA', 'SNC', 'SAS'])):
            old_name = supplier.nome
            supplier.nome = new_name
            logger.info(f"📝 Nome fornitore aggiornato: '{old_name}' → '{new_name}'")
            updated = True
        
        # Aggiorna informazioni mancanti
        if not supplier.email and supplier_info.get('email'):
            supplier.email = supplier_info['email']
            updated = True
            logger.info(f"📝 Email fornitore aggiunta: {supplier.email}")
        
        if not supplier.telefono and supplier_info.get('telefono'):
            supplier.telefono = supplier_info['telefono']
            updated = True
            logger.info(f"📝 Telefono fornitore aggiunto: {supplier.telefono}")
        
        if not supplier.partita_iva and supplier_info.get('partita_iva'):
            supplier.partita_iva = supplier_info['partita_iva']
            updated = True
            logger.info(f"📝 P.IVA fornitore aggiunta: {supplier.partita_iva}")
        
        if not supplier.codice_fiscale and supplier_info.get('codice_fiscale'):
            supplier.codice_fiscale = supplier_info['codice_fiscale']
            updated = True
            logger.info(f"📝 CF fornitore aggiunto: {supplier.codice_fiscale}")
        
        if not supplier.indirizzo and supplier_info.get('indirizzo'):
            supplier.indirizzo = supplier_info['indirizzo']
            updated = True
            logger.info(f"📝 Indirizzo fornitore aggiunto: {supplier.indirizzo}")
        
        if updated:
            supplier.updated_at = datetime.utcnow()
            logger.info(f"📝 Informazioni fornitore aggiornate: {supplier.nome}")
    
    def _normalize_ingredient_name(self, name: str) -> str:
        """Normalizza il nome di un ingrediente per un matching più preciso"""
        if not name:
            return ""
        
        # Converti in minuscolo
        normalized = name.lower().strip()
        
        # Rimuovi articoli e preposizioni comuni
        stop_words = [
            'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'del', 'della', 'dei', 'delle',
            'al', 'allo', 'alla', 'ai', 'agli', 'alle', 'dal', 'dallo', 'dalla', 'dai', 'dagli', 'dalle',
            'nel', 'nello', 'nella', 'nei', 'negli', 'nelle', 'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle',
            'per', 'con', 'di', 'da', 'in', 'su', 'a', 'e'
        ]
        
        words = normalized.split()
        filtered_words = [word for word in words if word not in stop_words]
        normalized = ' '.join(filtered_words)
        
        # Rimuovi descrizioni comuni in parentesi o dopo caratteri separatori
        normalized = re.sub(r'\s*[\(\[\-\—\–]\s*.*$', '', normalized)
        
        # Rimuovi unità di misura e quantità alla fine
        units = [
            'kg', 'gr', 'g', 'lt', 'ml', 'pz', 'pezzi', 'pezzo', 'conf', 'confezione', 'confezioni',
            'scatola', 'scatole', 'barattolo', 'barattoli', 'sacchetto', 'sacchetti'
        ]
        for unit in units:
            normalized = re.sub(rf'\s+{unit}[\s\d]*$', '', normalized)
        
        # Rimuovi numeri isolati alla fine (spesso sono codici o quantità)
        normalized = re.sub(r'\s+\d+[\.,]?\d*\s*$', '', normalized)
        
        # Rimuovi spazi multipli
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_ingredient_similarity(self, name1: str, name2: str) -> float:
        """Calcola la similarità tra due nomi di ingredienti usando diversi algoritmi"""
        if not name1 or not name2:
            return 0.0
        
        # Normalizza entrambi i nomi
        norm1 = self._normalize_ingredient_name(name1)
        norm2 = self._normalize_ingredient_name(name2)
        
        if norm1 == norm2:
            return 100.0  # Match perfetto
        
        # Fuzzy matching su nomi normalizzati
        normalized_score = fuzz.ratio(norm1, norm2)
        
        # Fuzzy matching su nomi originali
        original_score = fuzz.ratio(name1.lower(), name2.lower())
        
        # Token sort ratio per gestire parole in ordine diverso
        token_score = fuzz.token_sort_ratio(name1.lower(), name2.lower())
        
        # Partial ratio per trovare sottostringhe significative
        partial_score = fuzz.partial_ratio(name1.lower(), name2.lower())
        
        # Verifica se uno è contenuto nell'altro (con parole intere)
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        # Calcola intersezione delle parole
        common_words = words1.intersection(words2)
        all_words = words1.union(words2)
        
        if all_words:
            word_overlap = len(common_words) / len(all_words) * 100
        else:
            word_overlap = 0
        
        # Peso finale combinando i vari score
        final_score = max(
            normalized_score * 1.2,  # Bonus per matching normalizzato
            original_score,
            token_score * 1.1,       # Bonus per token sorting
            partial_score * 0.9,     # Meno peso per partial match
            word_overlap * 1.3       # Bonus per overlap parole
        )
        
        return min(final_score, 100.0)
    
    def _find_best_ingredient_match(self, target_name: str, existing_ingredients: List[Ingrediente]) -> Tuple[Optional[Ingrediente], float]:
        """Trova il miglior match per un ingrediente tra quelli esistenti"""
        if not existing_ingredients:
            return None, 0.0
        
        best_match = None
        best_score = 0.0
        
        logger.info(f"   🔍 Ricerca match per: '{target_name}'")
        logger.info(f"   📊 Ingredienti da confrontare: {len(existing_ingredients)}")
        
        # Calcola similarity con tutti gli ingredienti esistenti
        candidates = []
        for ingredient in existing_ingredients:
            score = self._calculate_ingredient_similarity(target_name, ingredient.nome)
            candidates.append((ingredient, score))
            
            if score > 90:  # Logging per score alti
                logger.info(f"      • {ingredient.nome}: {score:.1f}%")
        
        # Ordina per score discendente
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            best_match, best_score = candidates[0]
            logger.info(f"   🎯 Miglior match: '{best_match.nome}' (score: {best_score:.1f}%)")
            
            # Mostra anche i runner-up per debugging
            if len(candidates) > 1 and candidates[1][1] > 50:
                logger.info(f"   🥈 Secondo: '{candidates[1][0].nome}' (score: {candidates[1][1]:.1f}%)")
        
        return best_match, best_score
    
    def _create_new_ingredient(self, description: str, item: Dict, supplier: Fornitore, all_ingredients: List[Ingrediente]) -> Optional[Ingrediente]:
        """Crea un nuovo ingrediente nel database dal JSON item"""
        try:
            logger.info(f"   🆕 Creazione nuovo ingrediente: {description}")
            
            # Pulisci la descrizione e limita la lunghezza
            clean_name = description[:100].strip()
            
            # Usa UOM dal nuovo parser (KG, LT, PZ, CONF)
            uom = item.get('uom', 'KG')
            if uom is None:
                uom = 'KG'  # Default
            
            new_ingredient = Ingrediente(
                nome=clean_name,
                descrizione=f'Importato automaticamente da fattura {supplier.nome} il {datetime.now().strftime("%d/%m/%Y")} (confidence: {item.get("confidence", "N/A")})',
                unita_misura=uom.lower(),  # DB usa lowercase
                categoria='Importato Automatico',
                attivo=True
            )
            
            db.session.add(new_ingredient)
            db.session.flush()  # Per ottenere l'ID
            
            # Aggiorna la lista locale
            all_ingredients.append(new_ingredient)
            
            logger.info(f"   ✅ Creato nuovo ingrediente: {new_ingredient.nome} (ID: {new_ingredient.id})")
            return new_ingredient
            
        except Exception as e:
            logger.error(f"   ❌ Errore nella creazione dell'ingrediente '{description}': {str(e)}", exc_info=True)
            return None
    
    def match_and_update_ingredients(self, items_json: List[Dict], supplier: Fornitore) -> Dict[str, any]:
        """Fa il matching degli articoli JSON con gli ingredienti e aggiorna i prezzi"""
        results = {
            'matched': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'details': []
        }
        
        logger.info(f"🔍 Inizio matching ingredienti per fornitore: {supplier.nome}")
        logger.info(f"📦 Articoli da processare: {len(items_json)} (TUTTI verranno inseriti)")
        
        # Ottieni tutti gli ingredienti esistenti
        all_ingredients = Ingrediente.query.filter_by(attivo=True).all()
        ingredient_names = [i.nome for i in all_ingredients]
        
        logger.info(f"📊 Ingredienti esistenti nel database: {len(all_ingredients)}")
        
        for idx, item in enumerate(items_json, 1):
            logger.info(f"🔄 Processing item {idx}/{len(items_json)}: {item['descrizione']}")
            
            # 🚨 RIMOSSO IL FILTRO ALIMENTARE - TUTTI GLI ARTICOLI VENGONO PROCESSATI
            # Il sistema è specifico per fatture ingredienti
            
            if item.get('prezzo_unitario', 0) <= 0:
                logger.info(f"   ⏭️ Saltato (prezzo non valido): {item['descrizione']} - €{item.get('prezzo_unitario', 0)}")
                results['skipped'] += 1
                continue
            
            description = item['descrizione'].strip()
            matched_ingredient = None
            action = 'skipped'
            
            if all_ingredients:
                # Usa il nuovo sistema di matching intelligente
                best_match, score = self._find_best_ingredient_match(description, all_ingredients)
                
                # Soglie dinamiche basate sulla qualità del match
                if score >= 95:
                    # Match quasi perfetto
                    matched_ingredient = best_match
                    action = 'matched'
                    results['matched'] += 1
                    logger.info(f"   ✅ Match eccellente: {matched_ingredient.nome} (score: {score:.1f}%)")
                    
                elif score >= 80:
                    # Match buono
                    matched_ingredient = best_match
                    action = 'matched'
                    results['matched'] += 1
                    logger.info(f"   ✅ Match buono: {matched_ingredient.nome} (score: {score:.1f}%)")
                    
                elif score >= 65:
                    # Match medio - richiede conferma ma accettiamo
                    matched_ingredient = best_match
                    action = 'matched'
                    results['matched'] += 1
                    logger.info(f"   🔍 Match medio (da verificare): {matched_ingredient.nome} (score: {score:.1f}%)")
                    
                else:
                    # Score troppo basso, crea nuovo ingrediente
                    logger.info(f"   📊 Score troppo basso ({score:.1f}%), creazione nuovo ingrediente")
                    matched_ingredient = self._create_new_ingredient(description, item, supplier, all_ingredients)
                    if matched_ingredient:
                        action = 'created'
                        results['created'] += 1
                    else:
                        results['skipped'] += 1
                        continue
            else:
                # Nessun ingrediente esistente, crea il primo
                logger.info(f"   🆕 Primo ingrediente nel database: {description}")
                matched_ingredient = self._create_new_ingredient(description, item, supplier, all_ingredients)
                if matched_ingredient:
                    action = 'created'
                    results['created'] += 1
                else:
                    results['skipped'] += 1
                    continue
            
            # Aggiorna o crea associazione ingrediente-fornitore
            if matched_ingredient:
                logger.info(f"   🔗 Aggiornamento associazione: {matched_ingredient.nome} ↔ {supplier.nome}")
                association_updated = self._update_ingredient_supplier_association(
                    matched_ingredient, supplier, item
                )
                
                if association_updated:
                    results['updated'] += 1
                    logger.info(f"   ✅ Associazione aggiornata con prezzo: €{item['prezzo_unitario']}")
                else:
                    logger.warning(f"   ⚠️ Errore nell'aggiornamento associazione")
                
                results['details'].append({
                    'ingrediente': matched_ingredient.nome,
                    'fornitore': supplier.nome,
                    'prezzo': item['prezzo_unitario'],
                    'action': action,
                    'association_updated': association_updated,
                    'confidence': item.get('confidence', 0.9)
                })
        
        logger.info(f"📊 Risultati matching completato:")
        logger.info(f"   ✅ Trovati: {results['matched']}")
        logger.info(f"   🆕 Creati: {results['created']}")
        logger.info(f"   🔄 Aggiornati: {results['updated']}")
        logger.info(f"   ⏭️ Saltati: {results['skipped']}")
        
        return results
    
    def _update_ingredient_supplier_association(
        self, ingredient: Ingrediente, supplier: Fornitore, item: Dict
    ) -> bool:
        """Aggiorna o crea l'associazione ingrediente-fornitore"""
        try:
            # Cerca associazione esistente
            existing_association = IngredienteFornitore.query.filter_by(
                ingrediente_id=ingredient.id,
                fornitore_id=supplier.id
            ).first()
            
            prezzo_unitario = Decimal(str(item['prezzo_unitario']))
            quantita = item.get('quantita', 0)
            confidence = item.get('confidence', 0.9)
            
            # Controlla se dobbiamo cambiare fornitore preferito
            old_preferred_supplier = None
            if ingredient.fornitore_preferito_id and ingredient.fornitore_preferito_id != supplier.id:
                # Trova il nome del fornitore preferito attuale per il logging
                old_preferred = Fornitore.query.get(ingredient.fornitore_preferito_id)
                if old_preferred:
                    old_preferred_supplier = old_preferred.nome

            if existing_association:
                # Aggiorna associazione esistente
                old_price = existing_association.prezzo_unitario
                existing_association.prezzo_unitario = prezzo_unitario
                existing_association.attivo = True
                existing_association.updated_at = datetime.utcnow()
                
                # Aggiungi note sull'aggiornamento con confidence
                confidence_note = f" (confidence: {confidence})"
                if existing_association.note:
                    existing_association.note += f"\n• Prezzo aggiornato il {datetime.now().strftime('%d/%m/%Y')}: €{old_price} → €{prezzo_unitario}{confidence_note}"
                else:
                    existing_association.note = f"Prezzo aggiornato automaticamente il {datetime.now().strftime('%d/%m/%Y')}: €{old_price} → €{prezzo_unitario}{confidence_note}"
                
                logger.info(f"🔄 Aggiornata associazione {ingredient.nome} ↔ {supplier.nome}: €{old_price} → €{prezzo_unitario}")
            else:
                # Crea nuova associazione
                new_association = IngredienteFornitore(
                    ingrediente_id=ingredient.id,
                    fornitore_id=supplier.id,
                    prezzo_unitario=prezzo_unitario,
                    codice_fornitore='',  # Può essere aggiunto manualmente dopo
                    tempo_consegna_giorni=0,  # Può essere aggiunto manualmente dopo
                    quantita_minima=Decimal('0.000'),
                    note=f'Associazione creata automaticamente da fattura PDF il {datetime.now().strftime("%d/%m/%Y %H:%M")} (confidence: {confidence})',
                    attivo=True
                )
                db.session.add(new_association)
                logger.info(f"🆕 Creata associazione {ingredient.nome} ↔ {supplier.nome}: €{prezzo_unitario}")
            
            # 🌟 SEMPRE aggiorna il fornitore preferito all'ultimo fornitore che ha fornito l'ingrediente
            if ingredient.fornitore_preferito_id != supplier.id:
                if old_preferred_supplier:
                    logger.info(f"🔄 Cambio fornitore preferito per {ingredient.nome}: {old_preferred_supplier} → {supplier.nome}")
                else:
                    logger.info(f"🌟 Impostato {supplier.nome} come primo fornitore preferito per {ingredient.nome}")
                
                # Aggiorna fornitore preferito
                ingredient.fornitore_preferito_id = supplier.id
                ingredient.updated_at = datetime.utcnow()
                
                # Aggiorna/crea note sull'ingrediente per tracciare il cambio
                cambio_note = f"Fornitore preferito cambiato a {supplier.nome} il {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                if old_preferred_supplier:
                    cambio_note = f"Fornitore preferito: {old_preferred_supplier} → {supplier.nome} il {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                
                if ingredient.note:
                    ingredient.note += f"\n• {cambio_note}"
                else:
                    ingredient.note = cambio_note
            else:
                logger.info(f"✅ {supplier.nome} confermato come fornitore preferito per {ingredient.nome}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore nell'aggiornamento associazione {ingredient.nome} ↔ {supplier.nome}: {str(e)}", exc_info=True)
            return False
    
    def process_invoice_pdf(self, pdf_path: str) -> Dict[str, any]:
        """Processa completamente una fattura PDF usando il nuovo parser JSON"""
        logger.info(f"🚀 Inizio elaborazione fattura (nuovo parser): {pdf_path}")
        
        # Verifica che siamo in un contesto Flask valido
        try:
            self._ensure_flask_context()
            logger.info("✅ Contesto Flask verificato correttamente")
        except RuntimeError as e:
            logger.error(f"❌ Errore contesto Flask: {e}")
            return {
                'success': False,
                'supplier': None,
                'items_processed': 0,
                'matching_results': {},
                'parsed_data': None,
                'errors': [str(e)]
            }
        
        result = {
            'success': False,
            'supplier': None,
            'items_processed': 0,
            'matching_results': {},
            'parsed_data': None,
            'errors': []
        }
        
        try:
            # Usa il nuovo parser per ottenere JSON strutturato
            logger.info("🔧 Parsing con InvoiceParserService...")
            parsed_data = self.parser.parse_invoice_pdf(pdf_path)
            
            # Verifica se ci sono errori nel parsing
            if 'error' in parsed_data:
                error_msg = f"Errore nel parsing: {parsed_data['error']}"
                logger.error(f"❌ {error_msg}")
                result['errors'].append(error_msg)
                result['parsed_data'] = parsed_data
                return result
            
            result['parsed_data'] = parsed_data
            logger.info("✅ Parsing completato con successo")
            
            # Log info parsed data
            doc_info = parsed_data.get('documento', {})
            supplier_data = doc_info.get('fornitore', {})
            items_data = parsed_data.get('righe', [])
            
            logger.info(f"📄 Documento: {doc_info.get('numero', 'N/A')} del {doc_info.get('data', 'N/A')}")
            logger.info(f"🏢 Fornitore: {supplier_data.get('denominazione', 'N/A')} (confidence: {supplier_data.get('confidence', 'N/A')})")
            logger.info(f"📦 Righe estratte: {len(items_data)}")
            
            # Verifica dati fornitore
            if not supplier_data.get('denominazione'):
                error_msg = "Impossibile identificare il fornitore - Denominazione mancante nel parsing"
                logger.error(f"❌ {error_msg}")
                result['errors'].append(error_msg)
                return result
            
            # Trova o crea fornitore usando i dati JSON
            logger.info("🔍 Ricerca/creazione fornitore dal JSON...")
            supplier = self.find_or_create_supplier(supplier_data)
            if not supplier:
                error_msg = "Errore nella gestione del fornitore"
                logger.error(f"❌ {error_msg}")
                result['errors'].append(error_msg)
                return result
            
            result['supplier'] = {
                'id': supplier.id,
                'nome': supplier.nome,
                'email': supplier.email or '',
                'confidence': supplier_data.get('confidence', 0.0)
            }
            logger.info(f"✅ Fornitore gestito: {supplier.nome} (ID: {supplier.id})")
            
            # 🚨 IMPORTANTE: Processa TUTTI gli articoli (non solo alimentari)
            # Il sistema è specifico per fatture ingredienti, quindi tutto deve essere inserito
            all_items = items_data  # Non filtrare più per is_food_ingredient
            result['items_processed'] = len(items_data)
            
            logger.info(f"📦 TUTTI gli articoli verranno processati: {len(all_items)}/{len(items_data)}")
            
            # Log quality checks dal parser
            doc_checks = parsed_data.get('doc_checks', {})
            if doc_checks.get('totale_match', False):
                logger.info(f"✅ Controllo totali: OK (diff: €{doc_checks.get('totale_diff', 0)})")
            else:
                logger.warning(f"⚠️ Controllo totali: differenza di €{doc_checks.get('totale_diff', 0)}")
            
            # Fai matching e aggiorna ingredienti per TUTTI gli articoli
            if all_items:
                logger.info("🔄 Avvio matching e aggiornamento di TUTTI gli ingredienti dal JSON...")
                matching_results = self.match_and_update_ingredients(all_items, supplier)
                result['matching_results'] = matching_results
                
                logger.info("💾 Commit modifiche al database...")
                try:
                    db.session.commit()
                    logger.info("✅ Modifiche salvate con successo")
                except Exception as commit_error:
                    logger.error(f"❌ Errore durante il commit: {commit_error}")
                    db.session.rollback()
                    raise commit_error
            else:
                logger.warning("⚠️ Nessun articolo trovato da processare")
                matching_results = {
                    'matched': 0,
                    'created': 0,
                    'updated': 0,
                    'skipped': len(items_data),
                    'details': []
                }
                result['matching_results'] = matching_results
            
            result['success'] = True
            logger.info(f"🎉 Elaborazione completata con successo (nuovo parser)!")
            logger.info(f"📊 Riepilogo finale:")
            logger.info(f"   • Fornitore: {supplier.nome} (confidence: {supplier_data.get('confidence', 'N/A')})")
            logger.info(f"   • Articoli processati: {len(items_data)}")
            logger.info(f"   • Ingredienti trovati/aggiornati: {matching_results.get('matched', 0)}")
            logger.info(f"   • Ingredienti creati: {matching_results.get('created', 0)}")
            logger.info(f"   • Associazioni aggiornate: {matching_results.get('updated', 0)}")
            logger.info(f"   • Articoli saltati: {matching_results.get('skipped', 0)}")
            logger.info(f"   • Totali documento: €{parsed_data.get('riepilogo', {}).get('totale', 0)} (match: {doc_checks.get('totale_match', False)})")
            
        except Exception as e:
            logger.error("💥 Errore durante l'elaborazione (nuovo parser)", exc_info=True)
            db.session.rollback()
            logger.info("↩️ Rollback del database completato")
            
            error_msg = f"Errore durante l'elaborazione: {str(e)}"
            logger.error(f"❌ {error_msg}")
            result['errors'].append(error_msg)
        
        return result
