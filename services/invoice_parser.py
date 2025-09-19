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
                        for table_idx, table in enumerate(page_tables):
                            if not table:
                                continue
                            
                            # Tabelle multi-riga (almeno header + 1 riga)
                            if len(table) > 1:
                                tables.append(table)
                                logger.info(f"✅ Aggiunta tabella pagina {page_num+1}:{table_idx+1} - {len(table)} righe")
                            
                            # Tabelle a riga singola se sembrano contenere dati strutturati
                            elif len(table) == 1 and table[0]:
                                row = table[0]
                                # Verifica se la riga contiene almeno 3 colonne con dati significativi
                                valid_columns = [col for col in row if col and str(col).strip()]
                                if len(valid_columns) >= 3:
                                    # Verifica se contiene numeri (prezzi/quantità)
                                    has_numbers = any(self._contains_number(str(col)) for col in row)
                                    if has_numbers:
                                        # Crea una pseudo-tabella con header semplice per compatibilità
                                        pseudo_table = [
                                            ['Descrizione', 'Quantità', 'U.M.', 'Prezzo', 'Totale'],  # Header standard
                                            row  # Dati
                                        ]
                                        tables.append(pseudo_table)
                                        logger.info(f"✅ Aggiunta tabella a riga singola pagina {page_num+1}:{table_idx+1} - dati: {row}")
            
            logger.info(f"Trovate {len(tables)} tabelle nel PDF")
            return tables
        except Exception as e:
            logger.error(f"Errore nell'estrazione delle tabelle: {str(e)}")
            return []
    
    def _contains_number(self, text: str) -> bool:
        """Verifica se una stringa contiene numeri (per prezzi, quantità, ecc.)"""
        if not text:
            return False
        
        # Pattern per numeri con possibili simboli di valuta e formati EU
        number_patterns = [
            r'\d+[,.]?\d*',  # Numeri semplici: 123, 12.5, 12,5
            r'€\s*\d+[,.]?\d*',  # Con euro: € 12,50
            r'\d+[,.]?\d*\s*€',  # Euro dopo: 12,50 €
            r'\$\s*\d+[,.]?\d*'   # Con dollaro
        ]
        
        for pattern in number_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
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
        
        # Pattern più robusti e flessibili per P.IVA e CF
        piva_patterns = [
            r'(?:P\.?\s*IVA|PARTITA\s*IVA)[:\s]*([A-Z]{2}\s?\d{11}|\d{11})',  # Standard: P.IVA: IT12345678901 o P.IVA: 12345678901
            r'(?:P\.?\s*I\.?\s*V\.?\s*A\.?)[:\s]*([A-Z]{2}\s?\d{11}|\d{11})',  # Varianti: P.I.V.A., PIV.A, etc.
            r'\b([A-Z]{2}\d{11})\b',  # Solo codice: IT12345678901
            r'\b(\d{11})\b(?=\s*(?:Roma|Milano|Firenze|Bologna|Napoli|\w+\s*\([A-Z]{2}\)))',  # 11 cifre + città
            r'VAT[:\s]*([A-Z]{2}\d{11}|\d{11})',  # VAT Number
        ]
        
        cf_patterns = [
            r'(?:C\.?\s*F\.|CODICE\s*FISCALE)[:\s]*([A-Z0-9]{11,16})',  # Standard
            r'(?:COD\.?\s*FISC\.?)[:\s]*([A-Z0-9]{11,16})',  # Abbreviato
            r'(?:TAX\s*CODE)[:\s]*([A-Z0-9]{11,16})',  # Inglese
        ]
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Pattern telefono più flessibili
        phone_patterns = [
            r'(?:Tel\.?|Telefono|Phone)[:\s]*(\+39\s?)?(\d{2,3}[\s\-\.]?\d{3,4}[\s\-\.]?\d{3,4})',
            r'(?:\+39\s?)?(\d{3}\s?\d{3}\s?\d{4}|\d{3}\.\d{3}\.\d{4}|\d{10})',
            r'(\d{2,3}[\s\-\/]\d{6,8})',  # Formati locali: 06-12345678
        ]
        
        confidence_scores = []
        
        # Estrazione dati con pattern multipli
        for line in lines:
            line_upper = line.upper()
            
            # P.IVA - prova tutti i pattern
            if not supplier_info['partita_iva']:
                for pattern in piva_patterns:
                    piva_match = re.search(pattern, line_upper)
                    if piva_match:
                        supplier_info['partita_iva'] = self._normalize_piva(piva_match.group(1))
                        confidence_scores.append(0.95)  # Alta confidence per P.IVA
                        logger.info(f"📋 P.IVA trovata: {supplier_info['partita_iva']} usando pattern: {pattern}")
                        break
            
            # Codice Fiscale - prova tutti i pattern
            if not supplier_info['codice_fiscale']:
                for pattern in cf_patterns:
                    cf_match = re.search(pattern, line_upper)
                    if cf_match:
                        supplier_info['codice_fiscale'] = cf_match.group(1).replace(' ', '')
                        confidence_scores.append(0.9)
                        logger.info(f"📋 CF trovato: {supplier_info['codice_fiscale']}")
                        break
            
            # Email
            if not supplier_info['email']:
                email_match = re.search(email_pattern, line)
                if email_match:
                    supplier_info['email'] = email_match.group(0)
                    confidence_scores.append(0.9)
                    logger.info(f"📧 Email trovata: {supplier_info['email']}")
            
            # Telefono - prova tutti i pattern
            if not supplier_info['telefono']:
                for pattern in phone_patterns:
                    phone_match = re.search(pattern, line)
                    if phone_match:
                        # Estrai il numero completo
                        if phone_match.lastindex and phone_match.lastindex > 1:
                            # Pattern con gruppi multipli (es. Tel: +39 06-1234567)
                            phone_parts = [g for g in phone_match.groups() if g]
                            supplier_info['telefono'] = ''.join(phone_parts).replace(' ', '').replace('-', '').replace('.', '')
                        else:
                            # Pattern singolo
                            supplier_info['telefono'] = phone_match.group(0)
                        
                        confidence_scores.append(0.85)
                        logger.info(f"📞 Telefono trovato: {supplier_info['telefono']}")
                        break
            
            # Indirizzo (linee con CAP o numeri civici)
            if not supplier_info['indirizzo'] and re.search(r'\d{5}|\b\d{1,4}\s+[A-Za-z]', line):
                supplier_info['indirizzo'] = line.strip()
                confidence_scores.append(0.7)
        
        # Estrazione denominazione sociale (più conservativa e precisa)
        ignore_keywords = [
            'cedente', 'prestatore', 'fornitore', 'supplier', 'venditore', 'seller',
            'fattura', 'invoice', 'ragione sociale', 'denominazione', 'data',
            'documento', 'number', 'numero', 'doc', 'n.', 'nr'
        ]
        
        # Pattern per identificare numeri di fattura/documenti
        document_patterns = [
            r'fattura\s*n\.?\s*\d+',
            r'invoice\s*n\.?\s*\d+', 
            r'doc\s*n\.?\s*\d+',
            r'n\.?\s*\d{4}[\/\-]\d+',
            r'^\d{4}[\/\-]\d+',
            r'data\s*[:]*\s*\d+[\/\-]\d+',
            r'del\s+\d+[\/\-]\d+'
        ]
        
        for i, line in enumerate(lines[:25]):  # Cerca nelle prime 25 righe
            line_clean = line.strip()
            if len(line_clean) < 3 or len(line_clean) > 150:
                continue
            
            line_upper = line.upper()
            
            # Salta righe con keywords da ignorare
            if any(ignore_word in line_upper for ignore_word in ignore_keywords):
                continue
            
            # Salta righe che sono documenti/numeri fattura
            is_document = False
            for pattern in document_patterns:
                if re.search(pattern, line_upper):
                    is_document = True
                    break
            if is_document:
                continue
            
            # Salta righe che sono solo numeri, date o codici
            if re.match(r'^[\d\s\-\/\.:]+$', line_clean):
                continue
            
            # Salta righe con P.IVA o CF
            if re.search(r'P\.?\s*IVA|PARTITA\s*IVA|C\.?\s*F\.|CODICE\s*FISCALE', line_upper):
                continue
            
            # Salta righe che iniziano con giorni della settimana o mesi
            if re.match(r'^(LUNEDI|MARTEDI|MERCOLEDI|GIOVEDI|VENERDI|SABATO|DOMENICA|GENNAIO|FEBBRAIO|MARZO|APRILE|MAGGIO|GIUGNO|LUGLIO|AGOSTO|SETTEMBRE|OTTOBRE|NOVEMBRE|DICEMBRE)', line_upper):
                continue
                
            # Salta righe che sono chiaramente indirizzi (iniziano con via, corso, etc)
            if re.match(r'^(VIA|V\.LE|CORSO|C\.SO|PIAZZA|P\.ZA|VIALE|STRADA)\s', line_upper):
                continue
            
            # PRIORITÀ ALTA: Candidato con forma societaria
            if any(form in line_upper for form in ['S.R.L.', 'S.P.A.', 'S.N.C.', 'S.A.S.', 'SRL', 'SPA', 'SNC', 'SAS', 'S.R.L', 'S.P.A', 'S.N.C', 'S.A.S']):
                # Pulisce nome fornitore da tag HTML e parti non necessarie
                cleaned_name = self._clean_supplier_name(line_clean)
                if cleaned_name:
                    supplier_info['denominazione'] = cleaned_name
                    confidence_scores.append(0.95)
                    logger.info(f"📍 Nome fornitore trovato e pulito (forma societaria): '{cleaned_name}' alla riga {i+1}")
                    break
            
            # PRIORITÀ MEDIA: Candidato che sembra nome aziendale (non nelle primissime righe per evitare intestazioni)
            elif 3 <= i < 15 and 10 < len(line_clean) < 120:
                word_count = len(line_clean.split())
                # Deve avere almeno 2 parole e non essere solo numeri
                if 2 <= word_count <= 10 and not line_clean.isdigit():
                    # Verifica che non sia un indirizzo o info di contatto
                    if not re.search(r'@|\+39|\d{5}|www\.|http', line_clean.lower()):
                        # Verifica che contenga almeno una lettera maiuscola (tipico di nomi aziendali)
                        if any(c.isupper() for c in line_clean):
                            cleaned_name = self._clean_supplier_name(line_clean)
                            if cleaned_name:
                                supplier_info['denominazione'] = cleaned_name
                                confidence_scores.append(0.75)
                                logger.info(f"📍 Nome fornitore trovato e pulito (candidato valido): '{cleaned_name}' alla riga {i+1}")
                                break
        
        # Calcola confidence media
        supplier_info['confidence'] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.3
        
        return supplier_info
    
    def _clean_supplier_name(self, raw_name: str) -> str:
        """Pulisce il nome fornitore da tag HTML, SPETT.LE e altre parti non necessarie"""
        if not raw_name:
            return ""
        
        # Rimuovi tag HTML (es. <b>, </b>)
        cleaned = re.sub(r'<[^>]+>', '', raw_name)
        
        # Rimuovi "SPETT.LE:" e varianti
        cleaned = re.sub(r'\b(?:SPETT\.?LE?\.?:?|EGREGIO|GENTILE|GENT\.?|ALLA\s+CORTESE\s+ATTENZIONE)\b', '', cleaned, flags=re.IGNORECASE)
        
        # Gestisce fatture elettroniche con più denominazioni
        # Es: "Denominazione: MAVIC RICAMBI SRL Denominazione: DB COMPANY SRL A SOCIO UNICO"
        if 'denominazione:' in cleaned.lower():
            # Estrai tutte le denominazioni
            denominations = re.findall(r'denominazione:\s*([^d]*?)(?=\s*denominazione:|$)', cleaned, re.IGNORECASE)
            if denominations:
                # Prendi la prima (fornitore) e scarta la seconda (cliente)
                cleaned = denominations[0].strip()
                logger.info(f"   🔧 Estratta denominazione da fattura elettronica: '{cleaned}'")
        
        # Rimuovi doppi spazi e normalizza
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Rimuovi caratteri di punteggiatura all'inizio e fine
        cleaned = cleaned.strip('.,;:-')
        
        # Se rimane solo spazio o troppo corto, return vuoto
        if len(cleaned.strip()) < 3:
            return ""
        
        return cleaned.strip()
    
    def _is_total_or_tax_row(self, description: str) -> bool:
        """Verifica intelligente se una riga è un totale/IVA o contiene articoli validi"""
        if not description:
            return True
        
        desc_lower = description.lower()
        desc_words = desc_lower.split()
        
        # Pattern che indicano chiaramente righe di totale/IVA
        clear_total_patterns = [
            r'^(?:totale|total|subtotale|subtotal|imponibile|importo\s+totale)',  # Inizia con totale
            r'^(?:iva|imposta|tax)[\s\d%]+$',  # Solo IVA + percentuale
            r'^(?:sconto|discount|maggiorazione)',  # Sconti
            r'^\s*€?\s*[\d.,]+\s*$',  # Solo importo numerico
            r'^(?:esigibilità|riferimenti\s+normativi)',  # Termini fiscali
            r'^(?:bollo|contributo|conai)',  # Tasse aggiuntive
        ]
        
        # Se corrisponde a pattern chiari di totale, è sicuramente da saltare
        for pattern in clear_total_patterns:
            if re.search(pattern, desc_lower):
                return True
        
        # Pattern che indicano presenza di articoli/prodotti
        product_indicators = [
            r'\b(?:cod[._]?\s*[a-z0-9]+|art[._]?\s*[a-z0-9]+)',  # Codici articolo
            r'\b(?:mod[._]?\s*[a-z0-9]+)',  # Modelli
            r'\b(?:ricambi|ricambio|spare|part)',  # Ricambi
            r'\b(?:resistenza|interruttore|disco|smeriglio|guarnizione)',  # Nomi prodotti tecnici
            r'\b(?:kg|lt|pz|nr|conf|mt|cm)\b',  # Unità di misura
            r'\d+[,.]?\d*\s+[\d,]+\s+[a-z]+',  # Pattern prezzo quantità
        ]
        
        # Se contiene indicatori di prodotti, anche se ha "22,00" (IVA %), è probabilmente un articolo
        for pattern in product_indicators:
            if re.search(pattern, desc_lower):
                logger.info(f"   🔍 Riga riconosciuta come articolo (pattern: {pattern[:30]}...)")
                return False
        
        # Controllo lunghezza: righe molto lunghe spesso contengono articoli multipli
        if len(description) > 200:
            # Verifica se contiene più righe (fatture elettroniche compresse)
            if '\n' in description or re.search(r'[A-Z0-9]+\s+[A-Z].*?\d+[,.]?\d+.*?\d+[,.]?\d+', description):
                logger.info(f"   🔍 Riga lunga riconosciuta come articoli multipli")
                return False
        
        # Filtri tradizionali per IVA/totali semplici
        simple_tax_words = ['iva', 'imposta', 'totale', 'subtotale', 'sconto', 'trasporto']
        return any(word in desc_words for word in simple_tax_words)
    
    def _split_multiple_items(self, description: str) -> List[str]:
        """Split descrizioni più conservativo - con supporto per fatture elettroniche compresse"""
        if not description:
            return []
        
        # SUPPORTO FATTURE ELETTRONICHE COMPRESSE
        # Pattern per fatture elettroniche con articoli compressi in una cella
        if len(description) > 200 and '\n' in description:
            # Cerca pattern articoli: "NOME ARTICOLO quantità prezzo ... importo"
            electronic_items = self._extract_electronic_invoice_items(description)
            if len(electronic_items) > 1:
                logger.info(f"🔍 Estratti {len(electronic_items)} articoli da fattura elettronica compressa")
                return electronic_items[:15]  # Limite per fatture complesse
        
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
    
    def _extract_electronic_invoice_items(self, compressed_text: str) -> List[str]:
        """Estrae articoli da fatture elettroniche con contenuto compresso"""
        items = []
        
        # Pattern per riconoscere articoli in fatture elettroniche
        # Esempio: "RESISTENZA TAGLIAFILM DISPENSER SIRMAN 2,00 25,60 NR -50.00% 22,00 24,83"
        item_patterns = [
            # Pattern principale: NOME ARTICOLO + quantità + prezzo + altri dati
            r'([A-Z][A-Z\s]+?)\s+(\d+[,.]?\d*)\s+(\d+[,.]?\d*)\s+[A-Z]*\s*.*?(\d+[,.]?\d*)\s*\n',
            # Pattern alternativo per articoli con codici
            r'([A-Z][A-Z\s]+?)\s+(\d+[,.]?\d*)\s+(\d+[,.]?\d*)\s+.*?(\d+[,.]?\d*)',
            # Pattern per articoli con MOD./COD.
            r'([A-Z][A-Z\s]+?)\s*\n(?:MOD\.|COD_BUS).*?\n',
        ]
        
        # Split per linee e cerca articoli
        lines = compressed_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Salta linee vuote o troppo corte
            if not line or len(line) < 10:
                i += 1
                continue
            
            # Salta linee che sono chiaramente note o condizioni
            if any(keyword in line.lower() for keyword in ['documento emesso', 'condizioni', 'contributo', 'articolo', 'comma', 'codice civile']):
                i += 1
                continue
            
            # Pattern per articoli: cerca linee che iniziano con nome prodotto e hanno numeri
            # Es: "RESISTENZA TAGLIAFILM DISPENSER SIRMAN 2,00 25,60 NR -50.00% 22,00 24,83"
            if re.match(r'^[A-Z][A-Z\s]{10,}.*\d+[,.]?\d+.*\d+[,.]?\d+', line):
                # Estrai il nome del prodotto (prima parte prima dei numeri)
                name_match = re.match(r'^([A-Z][A-Z\s]+?)(?=\s+\d)', line)
                if name_match:
                    product_name = name_match.group(1).strip()
                    
                    # Se c'è una linea successiva con MOD./COD., includila nel nome
                    if i + 1 < len(lines) and re.match(r'MOD\.|COD_BUS', lines[i + 1]):
                        items.append(product_name)
                        i += 2  # Salta la linea MOD./COD.
                        continue
                    else:
                        items.append(product_name)
                
            # Pattern alternativo: cerca linee che iniziano con nomi prodotti tecnici
            elif re.match(r'^(?:RESISTENZA|INTERRUTTORE|DISCO|SMERIGLIO|GUARNIZIONE|MOTORE|VALVOLA|FILTRO|POMPA|CUSCINETTO)', line, re.IGNORECASE):
                # Estrai il nome completo fino ai numeri
                name_match = re.match(r'^([A-Z][^0-9]+?)(?=\s+\d|\s*$)', line, re.IGNORECASE)
                if name_match:
                    product_name = name_match.group(1).strip()
                    items.append(product_name)
            
            i += 1
        
        # Pulisci i nomi dei prodotti
        cleaned_items = []
        for item in items:
            # Rimuovi caratteri extra e normalizza
            cleaned = re.sub(r'\s+', ' ', item).strip()
            
            # Rimuovi parti che sono chiaramente dati numerici residui
            cleaned = re.sub(r'\d+[,.]?\d*\s*[€%]*\s*$', '', cleaned).strip()
            
            # Deve essere lungo almeno 5 caratteri per essere valido
            if len(cleaned) >= 5:
                cleaned_items.append(cleaned)
        
        # Rimuovi duplicati mantenendo l'ordine
        seen = set()
        unique_items = []
        for item in cleaned_items:
            if item not in seen:
                seen.add(item)
                unique_items.append(item)
        
        logger.info(f"   🔧 Parser elettronico ha trovato {len(unique_items)} articoli: {unique_items}")
        
        return unique_items
    
    def _parse_quantity_and_unit(self, qty_str: str) -> Tuple[Optional[float], Optional[str]]:
        """Parsing intelligente di quantità e unità di misura da stringhe come '25 kg', '5 lt'"""
        if not qty_str:
            return None, None
        
        # Pattern per catturare numero + unità di misura
        # Es: "25 kg", "5.5 lt", "10,5 pz", "1 conf"
        pattern = r'([\d.,]+)\s*([a-zA-Z]+)'
        match = re.search(pattern, qty_str.strip())
        
        if match:
            quantity_str = match.group(1)
            unit_str = match.group(2)
            
            # Parse quantità in formato EU
            quantity = self._parse_eu_number(quantity_str)
            
            # Normalizza unità di misura
            unit = self._normalize_unit(unit_str)
            
            return quantity, unit
        else:
            # Se non trova pattern, prova solo il numero
            quantity = self._parse_eu_number(qty_str)
            return quantity, None
    
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
            processed_rows = 0
            skipped_rows = 0
            
            for row_idx, row in enumerate(table[1:], 1):
                logger.info(f"   🔄 Processando riga {row_idx}/{len(table)-1}: {row}")
                
                if not row or len(row) == 0:
                    logger.info(f"   ⏭️ Riga {row_idx} saltata: vuota")
                    skipped_rows += 1
                    continue
                
                # Estrae descrizione
                description = ''
                if desc_idx is not None and desc_idx < len(row):
                    raw_desc = row[desc_idx]
                    description = str(raw_desc).strip() if raw_desc is not None else ''
                
                # Valida descrizione
                if not description or len(description) < 3:
                    logger.info(f"   ⏭️ Riga {row_idx} saltata: descrizione troppo corta ('{description}')")
                    skipped_rows += 1
                    continue
                
                # Verifica se è davvero una riga di totale/IVA o se contiene articoli validi
                if self._is_total_or_tax_row(description):
                    logger.info(f"   ⏭️ Riga {row_idx} saltata: sembra totale/IVA ('{description[:100]}...')")
                    skipped_rows += 1
                    continue
                
                # Split descrizioni se necessario
                split_descriptions = self._split_multiple_items(description)
                
                for single_desc in split_descriptions:
                    # Estrai dati numerici con parsing intelligente di quantità e UOM
                    quantity = None
                    unit_of_measure = None
                    
                    if qty_idx is not None and qty_idx < len(row):
                        qty_str = str(row[qty_idx]).strip() if row[qty_idx] is not None else ''
                        # Parsing intelligente di "25 kg", "5 lt", etc.
                        quantity, unit_of_measure = self._parse_quantity_and_unit(qty_str)
                    
                    # Se non ha trovato UOM nella quantità, cerca in colonna separata
                    if not unit_of_measure and uom_idx is not None and uom_idx < len(row):
                        uom_str = str(row[uom_idx]).strip() if row[uom_idx] is not None else ''
                        unit_of_measure = self._normalize_unit(uom_str)
                    
                    # Se UOM ancora non trovata, prova a indovinare dalla descrizione
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
                    processed_rows += 1
            
            logger.info(f"   📊 Tabella {table_idx+1} completata: {processed_rows} righe processate, {skipped_rows} saltate")
        
        logger.info(f"✅ Estratti {len(items)} articoli dalle {len(tables)} tabelle")
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
