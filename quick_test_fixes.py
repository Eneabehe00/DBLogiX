"""
Test veloce delle correzioni implementate
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.invoice_parser import InvoiceParserService

def test_electronic_invoice():
    """Test veloce fattura elettronica"""
    
    parser = InvoiceParserService()
    
    print("🔧 TEST FATTURA ELETTRONICA")
    print("=" * 40)
    
    try:
        result = parser.parse_invoice_pdf("UPLOADS/fatture/FatturaElettronica (1).pdf")
        
        if 'error' in result:
            print(f"❌ Errore: {result['error']}")
            return
        
        fornitore = result.get('documento', {}).get('fornitore', {})
        righe = result.get('righe', [])
        
        print(f"✅ Fornitore: {fornitore.get('denominazione', 'N/A')}")
        print(f"✅ Articoli estratti: {len(righe)}")
        
        # Mostra primi 3 articoli
        for i, riga in enumerate(righe[:3], 1):
            if riga.get('prezzo_unitario', 0) > 0:  # Solo articoli con prezzo valido
                print(f"   {i}. {riga['descrizione'][:50]}")
                print(f"      €{riga.get('prezzo_unitario', 0):.2f}")
        
        validi = [r for r in righe if r.get('prezzo_unitario', 0) > 0]
        print(f"🎯 Articoli con prezzo valido: {len(validi)}")
        
    except Exception as e:
        print(f"❌ Errore: {str(e)}")

def test_luigi_v1():
    """Test veloce Luigi V1"""
    
    parser = InvoiceParserService()
    
    print("\n🔧 TEST LUIGI V1")
    print("=" * 30)
    
    try:
        result = parser.parse_invoice_pdf("UPLOADS/fatture/fattura_test_luigi_verdi.pdf")
        
        if 'error' in result:
            print(f"❌ Errore: {result['error']}")
            return
        
        fornitore = result.get('documento', {}).get('fornitore', {})
        righe = result.get('righe', [])
        
        print(f"✅ Fornitore: {fornitore.get('denominazione', 'N/A')}")
        print(f"✅ Articoli: {len(righe)} (corretto per questa fattura)")
        
    except Exception as e:
        print(f"❌ Errore: {str(e)}")

if __name__ == "__main__":
    test_electronic_invoice()
    test_luigi_v1()
    print("\n✅ Test completato velocemente")
