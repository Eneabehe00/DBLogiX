#!/usr/bin/env python3
"""
Test per debuggare problemi con fattura Mario Rossi
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app import create_app
from services.pdf_invoice_processor import PDFInvoiceProcessor
import logging

# Setup logging per vedere tutti i dettagli
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_mario_rossi():
    """Debug specifico per fattura Mario Rossi"""
    
    # Crea app Flask per contesto
    app = create_app()
    
    with app.app_context():
        logger.info("=" * 60)
        logger.info("🔍 DEBUG FATTURA MARIO ROSSI")
        logger.info("=" * 60)
        
        # Percorso della fattura Mario Rossi
        pdf_path = os.path.join("UPLOADS", "fatture", "fattura_test_mario_rossi.pdf")
        
        if not os.path.exists(pdf_path):
            logger.error(f"❌ Fattura non trovata: {pdf_path}")
            return False
        
        processor = PDFInvoiceProcessor()
        
        # Estrai solo testo per vedere cosa c'è
        text = processor.extract_text_from_pdf(pdf_path)
        print("\n" + "="*60)
        print("📄 TESTO ESTRATTO DA MARIO ROSSI:")
        print("="*60)
        print(text)
        print("="*60)
        
        # Estrai informazioni fornitore
        supplier_info = processor.extract_supplier_info(text)
        print(f"\n🏢 INFORMAZIONI FORNITORE ESTRATTE:")
        for key, value in supplier_info.items():
            print(f"   {key}: '{value}'")
        
        return True

def debug_fattura_elettronica():
    """Debug specifico per FatturaElettronica (1).pdf"""
    
    # Crea app Flask per contesto
    app = create_app()
    
    with app.app_context():
        logger.info("=" * 60)
        logger.info("🔍 DEBUG FATTURA ELETTRONICA")
        logger.info("=" * 60)
        
        # Percorso della fattura elettronica
        pdf_path = os.path.join("UPLOADS", "fatture", "FatturaElettronica (1).pdf")
        
        if not os.path.exists(pdf_path):
            logger.error(f"❌ Fattura non trovata: {pdf_path}")
            return False
        
        processor = PDFInvoiceProcessor()
        
        # Estrai solo testo per vedere cosa c'è
        text = processor.extract_text_from_pdf(pdf_path)
        print("\n" + "="*60)
        print("📄 TESTO ESTRATTO DA FATTURA ELETTRONICA:")
        print("="*60)
        print(text[:1000] + "..." if len(text) > 1000 else text)  # Primi 1000 char
        print("="*60)
        
        # Estrai informazioni fornitore
        supplier_info = processor.extract_supplier_info(text)
        print(f"\n🏢 INFORMAZIONI FORNITORE ESTRATTE:")
        for key, value in supplier_info.items():
            print(f"   {key}: '{value}'")
        
        # Test elaborazione completa
        result = processor.process_invoice_pdf(pdf_path)
        print(f"\n📊 RISULTATO ELABORAZIONE:")
        print(f"   Successo: {result.get('success', False)}")
        if result.get('supplier'):
            print(f"   Fornitore: {result['supplier']['nome']}")
        print(f"   Articoli: {result.get('items_processed', 0)}")
        if result.get('errors'):
            print(f"   Errori: {result['errors']}")
        
        return True

if __name__ == "__main__":
    print("🔍 Debug fatture problematiche")
    
    print("\n" + "="*80)
    print("1️⃣ ANALISI FATTURA MARIO ROSSI")
    print("="*80)
    debug_mario_rossi()
    
    print("\n" + "="*80)
    print("2️⃣ ANALISI FATTURA ELETTRONICA")  
    print("="*80)
    debug_fattura_elettronica()
