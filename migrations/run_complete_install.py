#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script per eseguire l'installazione completa del database DBLogiX
Risolve l'errore di tabelle mancanti eseguendo Install_DBLogiX_Complete.sql
"""

import os
import sys
import logging
from pathlib import Path

# Aggiungi il percorso del progetto al path Python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """Configura il logging per l'installazione"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('complete_install.log')
        ]
    )
    return logging.getLogger(__name__)

def run_complete_install():
    """Esegue l'installazione completa del database DBLogiX"""
    logger = setup_logging()
    
    try:
        logger.info("=== INIZIO INSTALLAZIONE COMPLETA DBLOGIX ===")
        
        # Import delle dipendenze DBLogiX
        from app import create_app
        from services.utils import get_db_connection
        
        # Crea l'app Flask per avere il contesto database
        app = create_app()
        
        with app.app_context():
            logger.info("Contesto applicazione creato")
            
            # Cerca il file SQL di installazione completa
            install_file = project_root / 'Install DB e Kiosk' / 'Install_DBLogiX_Complete.sql'
            
            if not install_file.exists():
                logger.error(f"File di installazione non trovato: {install_file}")
                return False
            
            logger.info(f"File SQL trovato: {install_file}")
            logger.info(f"Dimensione file: {install_file.stat().st_size / 1024:.1f} KB")
            
            # Leggi il file SQL
            logger.info("Lettura file SQL di installazione...")
            with open(install_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Ottieni connessione al database
            logger.info("Connessione al database...")
            conn = get_db_connection()
            
            if not conn:
                logger.error("Impossibile connettersi al database")
                return False
            
            logger.info("Connessione al database stabilita")
            
            try:
                # Esegui l'installazione completa
                logger.info("ATTENZIONE: Questa operazione cancellerà tutte le tabelle esistenti!")
                logger.info("Inizio installazione completa del database...")
                
                # Dividi il contenuto SQL in statement separati
                # Usa un metodo più intelligente per dividere i statement SQL
                statements = []
                current_statement = ""
                
                for line in sql_content.split('\n'):
                    line = line.strip()
                    
                    # Ignora commenti e righe vuote
                    if not line or line.startswith('--'):
                        continue
                    
                    current_statement += line + " "
                    
                    # Se la riga termina con ; è la fine di uno statement
                    if line.endswith(';'):
                        statements.append(current_statement.strip())
                        current_statement = ""
                
                # Aggiungi l'ultimo statement se non termina con ;
                if current_statement.strip():
                    statements.append(current_statement.strip())
                
                logger.info(f"Preparati {len(statements)} statement SQL per l'esecuzione")
                
                success_count = 0
                error_count = 0
                
                with conn.cursor() as cursor:
                    for i, statement in enumerate(statements, 1):
                        if statement and not statement.startswith('--'):
                            try:
                                # Log ogni 50 statement per non intasare i log
                                if i % 50 == 0 or i <= 10:
                                    logger.info(f"Esecuzione statement {i}/{len(statements)}")
                                
                                cursor.execute(statement)
                                success_count += 1
                                
                                # Se è una SELECT di status, stampa il risultato
                                if statement.upper().strip().startswith('SELECT') and 'Status' in statement:
                                    try:
                                        results = cursor.fetchall()
                                        for result in results:
                                            if isinstance(result, dict) and 'Status' in result:
                                                logger.info(f"  Status: {result['Status']}")
                                            elif hasattr(result, 'get'):
                                                logger.info(f"  Status: {result}")
                                    except:
                                        pass  # Ignora errori di fetch
                                
                            except Exception as stmt_error:
                                error_count += 1
                                # Log solo errori critici
                                if "doesn't exist" not in str(stmt_error) and "Unknown table" not in str(stmt_error):
                                    logger.warning(f"Errore statement {i}: {stmt_error}")
                                continue
                
                # Commit delle modifiche
                conn.commit()
                logger.info("Commit dell'installazione completato")
                logger.info(f"Statement eseguiti con successo: {success_count}")
                logger.info(f"Statement con errori: {error_count}")
                
                # Verifica finale
                logger.info("Verifica finale dell'installazione...")
                with conn.cursor() as cursor:
                    # Verifica che la tabella dat_articulo esista
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = DATABASE() 
                        AND table_name = 'dat_articulo'
                    """)
                    articulo_exists = cursor.fetchone()[0]
                    
                    # Conta tutte le tabelle
                    cursor.execute("SHOW TABLES")
                    all_tables = cursor.fetchall()
                    
                    # Verifica tabelle specifiche
                    required_tables = ['dat_articulo', 'dat_cliente', 'users', 'messages', 'tasks']
                    found_tables = []
                    
                    for table in required_tables:
                        cursor.execute(f"""
                            SELECT COUNT(*) 
                            FROM information_schema.tables 
                            WHERE table_schema = DATABASE() 
                            AND table_name = '{table}'
                        """)
                        if cursor.fetchone()[0] > 0:
                            found_tables.append(table)
                    
                    logger.info(f"Tabelle totali create: {len(all_tables)}")
                    logger.info(f"Tabelle principali verificate: {found_tables}")
                    
                    if articulo_exists > 0:
                        logger.info("✅ SUCCESSO: Tabella dat_articulo creata correttamente")
                        

                        
                        print("\n" + "="*70)
                        print("✅ INSTALLAZIONE COMPLETA TERMINATA CON SUCCESSO!")
                        print(f"Database: sys_datos")
                        print(f"Tabelle create: {len(all_tables)}")
                        print(f"Tabelle principali: {', '.join(found_tables)}")
                        print("Il database è ora pronto per l'uso di DBLogiX.")
                        print("="*70)
                        return True
                    else:
                        logger.error("❌ ERRORE: Tabella dat_articulo non trovata dopo l'installazione")
                        return False
                
            except Exception as db_error:
                logger.error(f"Errore durante l'installazione: {db_error}")
                conn.rollback()
                return False
            
            finally:
                conn.close()
                logger.info("Connessione al database chiusa")
    
    except Exception as e:
        logger.error(f"Errore generale durante l'installazione: {e}")
        return False

def main():
    """Funzione principale"""
    print("=" * 70)
    print("INSTALLAZIONE COMPLETA DATABASE DBLOGIX")
    print("=" * 70)
    print("Questo script installa la struttura completa del database DBLogiX")
    print("includendo tutte le tabelle necessarie:")
    print("  - dat_articulo")
    print("  - dat_cliente")
    print("  - Sistema di chat")
    print("  - Sistema di task management")
    print("")
    print("  - E molto altro...")
    print()
    print("⚠️  ATTENZIONE: Questa operazione cancellerà tutte le tabelle esistenti!")
    print("=" * 70)
    
    response = input("Vuoi procedere con l'installazione completa? (s/n): ").lower().strip()
    
    if response in ['s', 'si', 'sì', 'y', 'yes']:
        print("\nInizio installazione...")
        success = run_complete_install()
        
        if success:
            print("\n🎉 Installazione completata con successo!")
            print("Ora puoi riavviare l'applicazione DBLogiX.")
            print("Il problema della colonna mancante dovrebbe essere risolto.")
        else:
            print("\n❌ Installazione fallita. Controlla i log per maggiori dettagli.")
            return 1
    else:
        print("Installazione annullata.")
        return 0
    
    return 0

if __name__ == "__main__":
    exit(main()) 