"""
Debug per analizzare i problemi con Luigi Verdi (ingredienti mancanti) 
e FatturaElettronica (nessun dato estratto)
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.invoice_parser import InvoiceParserService
import pdfplumber
import logging

# Configura logging per debug dettagliato
logging.basicConfig(level=logging.INFO, format='%(message)s')

def analyze_pdf_structure(pdf_path, pdf_name):
    """Analizza struttura raw del PDF"""
    
    print(f"\n🔍 ANALISI STRUTTURA: {pdf_name}")
    print("=" * 60)
    
    if not os.path.exists(pdf_path):
        print(f"❌ File non trovato: {pdf_path}")
        return None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📄 Pagine: {len(pdf.pages)}")
            
            all_text = ""
            all_tables = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n📃 === PAGINA {page_num} ===")
                
                # Estrai testo
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n"
                    lines = page_text.split('\n')
                    print(f"📝 Righe di testo: {len(lines)}")
                    
                    # Mostra prime righe non vuote
                    non_empty_lines = [line for line in lines if line.strip()]
                    for i, line in enumerate(non_empty_lines[:15]):
                        print(f"   {i+1:2d}: {line}")
                    
                    if len(non_empty_lines) > 15:
                        print(f"   ... e altre {len(non_empty_lines) - 15} righe")
                else:
                    print("📝 Nessun testo trovato")
                
                # Estrai tabelle
                page_tables = page.extract_tables()
                if page_tables:
                    print(f"📊 Tabelle: {len(page_tables)}")
                    for table_idx, table in enumerate(page_tables, 1):
                        print(f"   📋 Tabella {table_idx}: {len(table)} righe")
                        all_tables.extend(page_tables)
                        
                        # Mostra prime righe tabella
                        for row_idx, row in enumerate(table[:5]):
                            print(f"      Riga {row_idx+1}: {row}")
                        if len(table) > 5:
                            print(f"      ... e altre {len(table) - 5} righe")
                else:
                    print("📊 Nessuna tabella trovata")
            
            return {
                'text': all_text,
                'tables': all_tables,
                'text_length': len(all_text),
                'tables_count': len(all_tables)
            }
            
    except Exception as e:
        print(f"❌ Errore nell'analisi: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_parser_on_pdf(pdf_path, pdf_name):
    """Testa il parser su un PDF specifico"""
    
    print(f"\n🔧 TEST PARSER: {pdf_name}")
    print("=" * 40)
    
    parser = InvoiceParserService()
    
    try:
        result = parser.parse_invoice_pdf(pdf_path)
        
        if 'error' in result:
            print(f"❌ Errore nel parsing: {result['error']}")
            return None
        
        doc_info = result.get('documento', {})
        fornitore = doc_info.get('fornitore', {})
        righe = result.get('righe', [])
        
        print(f"📋 RISULTATI PARSING:")
        print(f"   Documento: {doc_info.get('numero', 'N/A')} del {doc_info.get('data', 'N/A')}")
        print(f"   Fornitore: {fornitore.get('denominazione', 'N/A')}")
        print(f"   P.IVA: {fornitore.get('partita_iva', 'N/A')}")
        print(f"   Confidence fornitore: {fornitore.get('confidence', 0):.1%}")
        print(f"   Articoli estratti: {len(righe)}")
        
        # Mostra primi 5 articoli
        for i, riga in enumerate(righe[:5], 1):
            food_icon = "🍕" if riga.get('is_food_ingredient') else "📦"
            print(f"   {i:2d}. {food_icon} {riga['descrizione']}")
            print(f"       {riga.get('quantita', 0)} {riga.get('uom', 'N/A')} × €{riga.get('prezzo_unitario', 0):.2f}")
        
        if len(righe) > 5:
            print(f"   ... e altri {len(righe) - 5} articoli")
        
        return result
        
    except Exception as e:
        print(f"❌ Errore nel parsing: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def compare_luigi_versions():
    """Confronta le due versioni di Luigi per capire le differenze"""
    
    print(f"\n🔍 CONFRONTO VERSIONI LUIGI VERDI")
    print("=" * 50)
    
    luigi_v1 = "UPLOADS/fatture/fattura_test_luigi_verdi.pdf"
    luigi_v2 = "UPLOADS/fatture/fattura_test_luigi_verdi_v2.pdf"
    
    parser = InvoiceParserService()
    
    try:
        # Test v1
        print("📄 LUIGI V1 (quello con problemi):")
        result_v1 = parser.parse_invoice_pdf(luigi_v1)
        righe_v1 = result_v1.get('righe', []) if 'error' not in result_v1 else []
        print(f"   Articoli estratti: {len(righe_v1)}")
        
        # Test v2  
        print("📄 LUIGI V2 (quello funzionante):")
        result_v2 = parser.parse_invoice_pdf(luigi_v2)
        righe_v2 = result_v2.get('righe', []) if 'error' not in result_v2 else []
        print(f"   Articoli estratti: {len(righe_v2)}")
        
        print(f"\n📊 DIFFERENZA: {len(righe_v2) - len(righe_v1)} articoli mancanti in V1")
        
        # Identifica quali articoli mancano
        if righe_v1 and righe_v2:
            desc_v1 = set(r['descrizione'] for r in righe_v1)
            desc_v2 = set(r['descrizione'] for r in righe_v2)
            
            missing_in_v1 = desc_v2 - desc_v1
            if missing_in_v1:
                print(f"🚨 ARTICOLI MANCANTI IN V1:")
                for desc in missing_in_v1:
                    print(f"   - {desc}")
        
        return result_v1, result_v2
        
    except Exception as e:
        print(f"❌ Errore nel confronto: {str(e)}")
        return None, None

def main():
    """Funzione principale di debug"""
    
    print("🔬 DEBUG COMPLETO PROBLEMI PDF")
    print("=" * 50)
    
    # 1. Analizza struttura FatturaElettronica
    print("\n" + "="*70)
    fattura_elettronica = "UPLOADS/fatture/FatturaElettronica (1).pdf"
    fe_structure = analyze_pdf_structure(fattura_elettronica, "FatturaElettronica")
    fe_result = test_parser_on_pdf(fattura_elettronica, "FatturaElettronica")
    
    # 2. Analizza Luigi V1 (con problemi)
    print("\n" + "="*70)
    luigi_v1 = "UPLOADS/fatture/fattura_test_luigi_verdi.pdf"  
    luigi_structure = analyze_pdf_structure(luigi_v1, "Luigi V1")
    luigi_result = test_parser_on_pdf(luigi_v1, "Luigi V1")
    
    # 3. Confronta le versioni Luigi
    print("\n" + "="*70)
    result_v1, result_v2 = compare_luigi_versions()
    
    # 4. Riepilogo problemi
    print(f"\n📊 RIEPILOGO PROBLEMI IDENTIFICATI:")
    print("=" * 40)
    
    problems = []
    
    # Problemi FatturaElettronica
    if not fe_result or not fe_result.get('documento', {}).get('fornitore', {}).get('denominazione'):
        problems.append("❌ FatturaElettronica: Fornitore non estratto")
    
    if not fe_result or len(fe_result.get('righe', [])) == 0:
        problems.append("❌ FatturaElettronica: Nessun articolo estratto")
    
    # Problemi Luigi V1
    if luigi_result and len(luigi_result.get('righe', [])) < 15:
        problems.append(f"❌ Luigi V1: Solo {len(luigi_result.get('righe', []))} articoli invece di 15")
    
    if problems:
        print("\n🚨 PROBLEMI TROVATI:")
        for problem in problems:
            print(f"   {problem}")
        
        print(f"\n💡 PROSSIMI STEP:")
        print(f"   1. Investigare perché Luigi V1 perde articoli")
        print(f"   2. Implementare supporto per fatture elettroniche")
        print(f"   3. Migliorare robustezza parsing per PDF complessi")
    else:
        print("✅ Nessun problema identificato")

if __name__ == "__main__":
    main()
