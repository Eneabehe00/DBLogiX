#!/usr/bin/env python3
"""
DBLogiX - Build System Entry Point
Script semplice per avviare il sistema di build modulare
"""

import sys
import os
from pathlib import Path

def main():
    """Entry point principale"""
    print("🚀 Avviando il sistema di build modulare DBLogiX...")
    print("="*70)
    
    # Aggiungi build_system al path
    build_system_dir = Path(__file__).parent / "build_system"
    if str(build_system_dir) not in sys.path:
        sys.path.insert(0, str(build_system_dir))
    
    try:
        # Importa e avvia il build system usando l'interfaccia pulita del modulo
        from build_system import run_build
        
        success = run_build()
        
        if success:
            print("\n✅ Build completato con successo!")
            print("📦 Controlla la directory installer_output/ per i file di distribuzione")
            return 0
        else:
            print("\n❌ Build fallito!")
            print("💡 Controlla i log per dettagli sull'errore")
            return 1
            
    except ImportError as e:
        print(f"❌ Errore nell'importazione dei moduli: {e}")
        print("💡 Assicurati che la directory build_system/ sia presente con tutti i moduli")
        return 1
    except Exception as e:
        print(f"❌ Errore imprevisto: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 