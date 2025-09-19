"""
DBLogiX - Invoice Parser Service
Sistema separato per il parsing di fatture PDF con output JSON strutturato
Nessuna dipendenza Flask/DB per facilità di testing
"""

import os
import re
import pdfplumber
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from datetime import datetime
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

class InvoiceParserService:
    """Servizio puro per il parsing di fatture PDF con output JSON strutturato"""
    
    def __init__(self):
        # Parole chiave per identificare ingredienti alimentari
        self.food_keywords = [
            'farina', 'olio', 'pomodoro', 'pomodori', 'sale', 'pepe', 'aglio', 'cipolla',
            'formaggio', 'mozzarella', 'parmigiano', 'ricotta', 'burro', 'latte', 'panna',
            'carne', 'pollo', 'manzo', 'maiale', 'vitello', 'pesce', 'tonno', 'salmone',
            'verdura', 'verdure', 'insalata', 'lattuga', 'carota', 'carote', 'patata', 'patate',
            'pasta', 'spaghetti', 'penne', 'fusilli', 'riso', 'risotto', 'cereali',
            'zucchero', 'sale', 'aceto', 'spezie', 'erbe', 'basilico', 'origano', 'prezzemolo',
            'pizza', 'pane', 'lievito', 'caffè', 'tè', 'vino', 'birra', 'acqua'
        ]
        
        # Unità di misura normalizzate
        self.unit_mapping = {
            'kg': 'KG', 'chilo': 'KG', 'chilogrammo': 'KG', 'chilogrammi': 'KG',
            'lt': 'LT', 'litro': 'LT', 'litri': 'LT', 'l': 'LT',
            'pz': 'PZ', 'pezzo': 'PZ', 'pezzi': 'PZ', 'nr': 'PZ', 'n.': 'PZ',
            'conf': 'CONF', 'confezione': 'CONF', 'confezioni': 'CONF',
            'scatola': 'CONF', 'scatole': 'CONF', 'barattolo': 'CONF', 'barattoli': 'CONF'
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Estrae tutto il testo dal PDF"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            logger.info(f"Estratto testo da PDF: {len(text)} caratteri")
            return text
        except Exception as e:
            logger.error(f"Errore nell'estrazione del testo: {str(e)}")
            return ""
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[List[List]]:
        """Estrae le tabelle dal PDF"""
        try:
            tables = []
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            if table and len(table) > 1:  # Almeno header + 1 riga
                                tables.append(table)
            
            logger.info(f"Trovate {len(tables)} tabelle nel PDF")
            return tables
        except Exception as e:
            logger.error(f"Errore nell'estrazione delle tabelle: {str(e)}")
            return []
    
    def _normalize_piva(self, piva: str) -> str:
        """Normalizza P.IVA al formato standard"""
        if not piva:
            return ""
        
        piva = piva.replace(" ", "").replace("-", "").upper()
        if piva.startswith("IT"):
            return piva
        elif len(piva) == 11 and piva.isdigit():
            return f"IT{piva}"
        return piva
    
    def _parse_eu_number(self, text: str) -> Optional[float]:
        """Converte numeri formato EU (1.234,56) in float"""
        if not text:
            return None
        
        # Rimuove caratteri non numerici eccetto virgole, punti e segni
        cleaned = re.sub(r'[^\d,.-]', '', str(text).strip())
        
        if not cleaned:
            return None
        
        try:
            # Gestisce formati numerici europei (virgola come decimale)
            if ',' in cleaned and '.' in cleaned:
                # Formato 1.234,56 - punto come separatore migliaia, virgola come decimale
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned and not '.' in cleaned:
                # Solo virgola - assumiamo sia decimale se ci sono max 3 cifre dopo
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 3:
                    cleaned = cleaned.replace(',', '.')
                # Altrimenti potrebbe essere separatore migliaia, lasciamo com'è
            
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def _extract_supplier_info(self, text: str) -> Dict[str, Any]:
        """Estrae informazioni del fornitore dal testo con confidence scoring"""
        supplier_info = {
            'denominazione': '',
            'partita_iva': '',
            'codice_fiscale': '',
            'indirizzo': '',
            'email': '',
            'telefono': '',
            'confidence': 0.0
        }
        
        lines = text.split('\n')
        
        # Pattern più robusti per P.IVA e CF
        piva_pattern = r'(?:P\.?\s*IVA|PARTITA\s*IVA)[:\s]*([A-Z]{2}\s?\d{11}|\d{11})'
        cf_pattern = r'(?:C\.?\s*F\.|CODICE\s*FISCALE)[:\s]*([A-Z0-9]{11,16})'
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'(?:\+39\s?)?(?:\d{3}\s?\d{3}\s?\d{4}|\d{3}\.\d{3}\.\d{4}|\d{10})'
        
        confidence_scores = []
        
        # Estrazione dati
        for line in lines:
            line_upper = line.upper()
            
            # P.IVA
            piva_match = re.search(piva_pattern, line_upper)
            if piva_match and not supplier_info['partita_iva']:
                supplier_info['partita_iva'] = self._normalize_piva(piva_match.group(1))
                confidence_scores.append(0.95)  # Alta confidence per P.IVA
            
            # Codice Fiscale
            cf_match = re.search(cf_pattern, line_upper)
            if cf_match and not supplier_info['codice_fiscale']:
                supplier_info['codice_fiscale'] = cf_match.group(1).replace(' ', '')
                confidence_scores.append(0.9)
            
            # Email
            email_match = re.search(email_pattern, line)
            if email_match and not supplier_info['email']:
                supplier_info['email'] = email_match.group(0)
                confidence_scores.append(0.9)
            
            # Telefono
            phone_match = re.search(phone_pattern, line)
            if phone_match and not supplier_info['telefono']:
                supplier_info['telefono'] = phone_match.group(0)
                confidence_scores.append(0.85)
            
            # Indirizzo (linee con CAP o numeri civici)
            if not supplier_info['indirizzo'] and re.search(r'\d{5}|\b\d{1,4}\s+[A-Za-z]', line):
                supplier_info['indirizzo'] = line.strip()
                confidence_scores.append(0.7)
        
        # Estrazione denominazione sociale (più conservativa)
        ignore_keywords = [
            'cedente', 'prestatore', 'fornitore', 'supplier', 'venditore', 'seller',
            'fattura', 'invoice', 'ragione sociale', 'denominazione', 'data'
        ]
        
        for i, line in enumerate(lines[:20]):  # Solo prime 20 righe
            line_clean = line.strip()
            if len(line_clean) < 3 or len(line_clean) > 100:
                continue
            
            line_upper = line.upper()
            
            # Salta righe con keywords da ignorare
            if any(ignore_word in line_upper for ignore_word in ignore_keywords):
                continue
            
            # Salta righe che sono solo numeri, date o codici
            if re.match(r'^[\d\s\-\/\.]+$', line_clean):
                continue
            
            # Salta righe con P.IVA o CF
            if re.search(r'P\.?\s*IVA|PARTITA\s*IVA|C\.?\s*F\.|CODICE\s*FISCALE', line_upper):
                continue
            
            # Candidato con forma societaria (alta priorità)
            if any(form in line_upper for form in ['S.R.L.', 'S.P.A.', 'S.N.C.', 'S.A.S.', 'SRL', 'SPA', 'SNC', 'SAS']):
                supplier_info['denominazione'] = line_clean
                confidence_scores.append(0.95)
                break
            
            # Candidato nelle prime righe (priorità media)
            elif i < 10 and 5 < len(line_clean) < 60:
                word_count = len(line_clean.split())
                if 2 <= word_count <= 6 and not line_clean.isdigit():
                    supplier_info['denominazione'] = line_clean
                    confidence_scores.append(0.8)
                    break
        
        # Calcola confidence media
        supplier_info['confidence'] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.3
        
        return supplier_info
    
    def _split_multiple_items(self, description: str) -> List[str]:
        """Split descrizioni più conservativo - solo per liste chiaramente identificabili"""
        if not description:
            return []
        
        # Pattern per liste numerate (1) ... 2) ...)
        if re.search(r'\d+\)\s*\S', description):
            items = re.findall(r'\d+\)\s*([^)]+?)(?=\s*\d+\)|$)', description)
            clean_items = [i.strip() for i in items if len(i.strip()) > 2]
            if len(clean_items) > 1:
                logger.info(f"Split lista numerata: {len(clean_items)} items")
                return clean_items[:10]  # Limite massimo
        
        # Solo ';' come separatore se chiaramente distinto
        if ';' in description:
            parts = [p.strip() for p in description.split(';') if len(p.strip()) > 2]
            if len(parts) > 1 and len(parts) <= 5:  # Max 5 parti per evitare over-splitting
                return parts
        
        # Solo '\n' se ogni riga è significativa
        if '\n' in description:
            parts = [p.strip() for p in description.splitlines() if len(p.strip()) > 2]
            if len(parts) > 1 and len(parts) <= 5:
                return parts
        
        # Default: non splittare
        return [description]
    
    def _normalize_unit(self, unit_text: str) -> Optional[str]:
        """Normalizza unità di misura"""
        if not unit_text:
            return None
        
        unit_lower = unit_text.lower().strip()
        return self.unit_mapping.get(unit_lower)
    
    def _guess_unit_from_description(self, description: str) -> Optional[str]:
        """Indovina l'unità di misura dalla descrizione"""
        desc_lower = description.lower()
        
        for unit, normalized in self.unit_mapping.items():
            if f' {unit}' in desc_lower or desc_lower.startswith(unit):
                return normalized
        
        return None
    
    def _is_food_ingredient(self, description: str) -> bool:
        """Determina se è un ingrediente alimentare"""
        desc_lower = description.lower()
        
        for keyword in self.food_keywords:
            if keyword in desc_lower:
                return True
        
        # Pattern alimentari comuni
        if re.search(r'\b(biologico|organic|fresh|fresco|surgelato|congelato)\b', desc_lower):
            return True
        
        return False
    
    def _validate_row_data(self, qty: Optional[float], price: Optional[float], total: Optional[float]) -> bool:
        """Valida coerenza dati di riga"""
        if not all([qty, price, total]):
            return True  # Non possiamo validare dati incompleti
        
        calculated_total = qty * price
        return abs(calculated_total - total) <= 0.02
    
    def _extract_document_info(self, text: str) -> Dict[str, Any]:
        """Estrae numero e data documento"""
        doc_info = {
            'numero': '',
            'data': ''
        }
        
        lines = text.split('\n')[:30]  # Prime 30 righe
        
        # Pattern per numero fattura
        numero_patterns = [
            r'(?:FATTURA|INVOICE)\s*(?:N\.?|NUMBER|NUM)\s*([A-Z0-9\-\/]+)',
            r'(?:N\.?\s*)?FATTURA\s*([A-Z0-9\-\/]+)',
            r'DOC\.?\s*(?:N\.?)?\s*([A-Z0-9\-\/]+)'
        ]
        
        # Pattern per data
        data_patterns = [
            r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'(\d{2,4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})'
        ]
        
        for line in lines:
            line_upper = line.upper().strip()
            
            # Cerca numero documento
            if not doc_info['numero']:
                for pattern in numero_patterns:
                    match = re.search(pattern, line_upper)
                    if match:
                        doc_info['numero'] = match.group(1).strip()
                        break
            
            # Cerca data
            if not doc_info['data']:
                for pattern in data_patterns:
                    match = re.search(pattern, line)
                    if match:
                        doc_info['data'] = match.group(1).strip()
                        break
        
        return doc_info
    
    def _extract_summary_totals(self, text: str) -> Dict[str, float]:
        """Estrae totali del riepilogo"""
        summary = {
            'subtotale': 0.0,
            'iva': 0.0,
            'totale': 0.0
        }
        
        lines = text.split('\n')
        
        # Pattern per totali
        patterns = {
            'subtotale': [r'(?:IMPONIBILE|SUBTOTAL|NETTO)\s*[€]?\s*([\d.,]+)', r'TOTALE\s*IMPONIBILE\s*[€]?\s*([\d.,]+)'],
            'iva': [r'(?:IVA|VAT)\s*[€]?\s*([\d.,]+)', r'IMPOSTA\s*[€]?\s*([\d.,]+)'],
            'totale': [r'(?:TOTALE|TOTAL)\s*(?:DOCUMENTO|DOC)?\s*[€]?\s*([\d.,]+)', r'DA\s*PAGARE\s*[€]?\s*([\d.,]+)']
        }
        
        for line in lines[-20:]:  # Ultime 20 righe
            line_upper = line.upper().strip()
            
            for key, pattern_list in patterns.items():
                if summary[key] == 0.0:  # Solo se non ancora trovato
                    for pattern in pattern_list:
                        match = re.search(pattern, line_upper)
                        if match:
                            value = self._parse_eu_number(match.group(1))
                            if value and value > 0:
                                summary[key] = value
                                break
        
        return summary
    
    def _extract_items_from_tables(self, tables: List[List[List]]) -> List[Dict[str, Any]]:
        """Estrae articoli dalle tabelle con validazione"""
        items = []
        
        logger.info(f"🔍 Analisi {len(tables)} tabelle")
        
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:
                continue
            
            header = table[0] if table[0] else []
            header_lower = [str(col).lower() if col else '' for col in header]
            
            # Trova indici colonne
            desc_idx = self._find_column_index(header_lower, ['descrizione', 'description', 'prodotto', 'articolo', 'desc', 'item'])
            qty_idx = self._find_column_index(header_lower, ['quantità', 'quantity', 'qta', 'qt', 'q.tà'])
            uom_idx = self._find_column_index(header_lower, ['um', 'u.m.', 'unità', 'unit', 'misura'])
            price_idx = self._find_column_index(header_lower, ['prezzo', 'price', 'unitario', 'costo', '€'])
            total_idx = self._find_column_index(header_lower, ['importo', 'total', 'totale', 'imponibile'])
            iva_idx = self._find_column_index(header_lower, ['iva', 'vat', '%'])
            
            # Se non trova descrizione, usa prima colonna significativa
            if desc_idx is None:
                for i, col in enumerate(header_lower):
                    if len(col) > 2 and not col.isdigit():
                        desc_idx = i
                        break
            
            logger.info(f"   Tabella {table_idx+1}: desc={desc_idx}, qty={qty_idx}, uom={uom_idx}, price={price_idx}, total={total_idx}")
            
            # Processa righe
            for row_idx, row in enumerate(table[1:], 1):
                if not row or len(row) == 0:
                    continue
                
                # Estrae descrizione
                description = ''
                if desc_idx is not None and desc_idx < len(row):
                    raw_desc = row[desc_idx]
                    description = str(raw_desc).strip() if raw_desc is not None else ''
                
                # Valida descrizione
                if not description or len(description) < 3:
                    continue
                
                # Salta totali e intestazioni
                if any(word in description.lower() for word in ['totale', 'total', 'iva', 'imposta', 'sconto', 'trasporto']):
                    continue
                
                # Split descrizioni se necessario
                split_descriptions = self._split_multiple_items(description)
                
                for single_desc in split_descriptions:
                    # Estrai dati numerici
                    quantity = None
                    if qty_idx is not None and qty_idx < len(row):
                        qty_str = str(row[qty_idx]).strip() if row[qty_idx] is not None else ''
                        quantity = self._parse_eu_number(qty_str)
                    
                    unit_of_measure = None
                    if uom_idx is not None and uom_idx < len(row):
                        uom_str = str(row[uom_idx]).strip() if row[uom_idx] is not None else ''
                        unit_of_measure = self._normalize_unit(uom_str)
                    
                    # Se UOM non trovata in colonna, prova a indovinare dalla descrizione
                    if not unit_of_measure:
                        unit_of_measure = self._guess_unit_from_description(single_desc)
                    
                    unit_price = None
                    if price_idx is not None and price_idx < len(row):
                        price_str = str(row[price_idx]).strip() if row[price_idx] is not None else ''
                        unit_price = self._parse_eu_number(price_str)
                    
                    total_amount = None
                    if total_idx is not None and total_idx < len(row):
                        total_str = str(row[total_idx]).strip() if row[total_idx] is not None else ''
                        total_amount = self._parse_eu_number(total_str)
                    
                    iva_percent = None
                    if iva_idx is not None and iva_idx < len(row):
                        iva_str = str(row[iva_idx]).strip() if row[iva_idx] is not None else ''
                        iva_percent = self._parse_eu_number(iva_str)
                    
                    # Calcoli di fallback
                    if unit_price is None and quantity and total_amount and quantity > 0:
                        unit_price = total_amount / quantity
                    
                    if total_amount is None and quantity and unit_price:
                        total_amount = round(quantity * unit_price, 2)
                    
                    # Adjust per split multipli
                    if len(split_descriptions) > 1:
                        if total_amount:
                            total_amount = round(total_amount / len(split_descriptions), 2)
                        if unit_price is None and total_amount and quantity:
                            unit_price = round(total_amount / (quantity / len(split_descriptions)), 4)
                    
                    # IVA di default se non specificata
                    if iva_percent is None:
                        iva_percent = 22.0  # Default IVA italiana
                    
                    # Valida dati
                    row_valid = self._validate_row_data(quantity, unit_price, total_amount)
                    
                    # Calcola confidence
                    confidence = 0.9
                    notes = ""
                    
                    if not row_valid:
                        confidence = 0.6
                        notes = "Possibile incongruenza nei calcoli"
                    
                    if unit_price is None or quantity is None:
                        confidence = 0.5
                        notes += " Dati incompleti"
                    
                    item = {
                        'descrizione': single_desc,
                        'quantita': float(quantity) if quantity else 0.0,
                        'uom': unit_of_measure,
                        'prezzo_unitario': float(unit_price) if unit_price else 0.0,
                        'totale_riga': float(total_amount) if total_amount else 0.0,
                        'iva_percent': float(iva_percent) if iva_percent else 22.0,
                        'confidence': confidence,
                        'notes': notes.strip(),
                        'is_food_ingredient': self._is_food_ingredient(single_desc)
                    }
                    
                    items.append(item)
        
        logger.info(f"✅ Estratti {len(items)} articoli dalle tabelle")
        return items
    
    def _find_column_index(self, header: List[str], keywords: List[str]) -> Optional[int]:
        """Trova indice colonna basandosi su keywords"""
        for i, col in enumerate(header):
            col_clean = col.strip().lower()
            for keyword in keywords:
                if keyword in col_clean:
                    return i
        return None
    
    def _calculate_document_checks(self, items: List[Dict], summary: Dict[str, float]) -> Dict[str, Any]:
        """Calcola controlli di coerenza del documento"""
        sum_righe = sum(item.get('totale_riga', 0.0) for item in items)
        totale_doc = summary.get('totale', 0.0)
        
        totale_diff = abs(sum_righe - totale_doc)
        totale_match = totale_diff <= 0.05
        
        return {
            'sum_righe': round(sum_righe, 2),
            'totale_diff': round(totale_diff, 2),
            'totale_match': totale_match
        }
    
    def parse_invoice_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Parsing completo di fattura PDF con output JSON strutturato"""
        logger.info(f"🚀 Inizio parsing: {pdf_path}")
        
        # Estrai testo e tabelle
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            logger.error("❌ Impossibile estrarre testo dal PDF")
            return self._create_error_result("Impossibile estrarre testo dal PDF")
        
        tables = self.extract_tables_from_pdf(pdf_path)
        if not tables:
            logger.error("❌ Nessuna tabella trovata nel PDF")
            return self._create_error_result("Nessuna tabella trovata nel PDF")
        
        # Parsing componenti
        doc_info = self._extract_document_info(text)
        supplier_info = self._extract_supplier_info(text)
        summary = self._extract_summary_totals(text)
        items = self._extract_items_from_tables(tables)
        
        # Controlli documento
        doc_checks = self._calculate_document_checks(items, summary)
        
        # Costruisce result JSON secondo schema
        result = {
            'documento': {
                'numero': doc_info.get('numero', ''),
                'data': doc_info.get('data', ''),
                'fornitore': supplier_info
            },
            'righe': items,
            'riepilogo': summary,
            'doc_checks': doc_checks
        }
        
        logger.info(f"✅ Parsing completato: {len(items)} righe, fornitore: {supplier_info.get('denominazione', 'N/A')}")
        return result
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Crea risultato di errore con schema JSON"""
        return {
            'documento': {
                'numero': '',
                'data': '',
                'fornitore': {
                    'denominazione': '',
                    'partita_iva': '',
                    'codice_fiscale': None,
                    'indirizzo': None,
                    'email': None,
                    'telefono': None,
                    'confidence': 0.0
                }
            },
            'righe': [],
            'riepilogo': {
                'subtotale': 0.0,
                'iva': 0.0,
                'totale': 0.0
            },
            'doc_checks': {
                'sum_righe': 0.0,
                'totale_diff': 0.0,
                'totale_match': False
            },
            'error': error_message
        }
    
    def parse_text_only(self, text: str, tables: Optional[List[List[List]]] = None) -> Dict[str, Any]:
        """Parsing da testo puro (per testing senza PDF)"""
        logger.info("🔍 Parsing da testo puro")
        
        if not text:
            return self._create_error_result("Testo vuoto fornito")
        
        # Se non ci sono tabelle, prova a estrarle dal testo
        if not tables:
            tables = self._extract_simple_tables_from_text(text)
        
        # Resto del parsing identico
        doc_info = self._extract_document_info(text)
        supplier_info = self._extract_supplier_info(text)
        summary = self._extract_summary_totals(text)
        items = self._extract_items_from_tables(tables) if tables else []
        doc_checks = self._calculate_document_checks(items, summary)
        
        return {
            'documento': {
                'numero': doc_info.get('numero', ''),
                'data': doc_info.get('data', ''),
                'fornitore': supplier_info
            },
            'righe': items,
            'riepilogo': summary,
            'doc_checks': doc_checks
        }
    
    def _extract_simple_tables_from_text(self, text: str) -> List[List[List]]:
        """Estrazione tabelle semplice da testo per testing"""
        # Implementazione base per testing - da migliorare se necessario
        return []
