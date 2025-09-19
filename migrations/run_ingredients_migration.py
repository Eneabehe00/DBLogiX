#!/usr/bin/env python3
"""
DBLogiX - Migrazione Gestione Ingredienti
Automatizza l'installazione delle tabelle per la gestione ingredienti e fornitori
Versione: 1.0.0
Compatibile con MySQL 5.x
"""

import mysql.connector
import os
import sys
import json
from pathlib import Path

# Aggiungi il percorso dell'app per importare la configurazione
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def load_db_config():
    """Carica la configurazione del database dal file config.py"""
    try:
        from app.config import Config
        config = Config()
        
        return {
            'host': config.MYSQL_HOST,
            'user': config.MYSQL_USER,
            'password': config.MYSQL_PASSWORD,
            'database': config.MYSQL_DATABASE,
            'port': config.MYSQL_PORT or 3306,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
    except ImportError:
        # Fallback: try to load from environment or prompt user
        return {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'DBLogiX'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }

def test_connection(config):
    """Testa la connessione al database"""
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        print(f"✓ Connessione al database riuscita! MySQL versione: {version[0]}")
        return True
    except mysql.connector.Error as err:
        print(f"✗ Errore connessione database: {err}")
        return False

def check_existing_tables(config):
    """Controlla se le tabelle esistono già"""
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        tables_to_check = [
            'dat_fornitore',
            'dat_ingrediente', 
            'dat_fornitore_ingrediente',
            'dat_articolo_ingrediente'
        ]
        
        existing_tables = []
        for table in tables_to_check:
            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            result = cursor.fetchone()
            if result:
                existing_tables.append(table)
        
        cursor.close()
        conn.close()
        
        return existing_tables
    except mysql.connector.Error as err:
        print(f"✗ Errore controllo tabelle: {err}")
        return []

def execute_sql_file(config, sql_file_path):
    """Esegue un file SQL"""
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # Dividi le query usando il delimitatore ';'
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        success_count = 0
        for statement in statements:
            if statement.strip() and not statement.strip().startswith('--'):
                try:
                    cursor.execute(statement)
                    success_count += 1
                except mysql.connector.Error as err:
                    if "already exists" in str(err).lower():
                        print(f"⚠ Tabella già esistente: {err}")
                    else:
                        print(f"✗ Errore esecuzione query: {err}")
                        print(f"Query: {statement[:100]}...")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✓ Eseguite {success_count} query con successo")
        return True
        
    except mysql.connector.Error as err:
        print(f"✗ Errore esecuzione SQL: {err}")
        return False
    except FileNotFoundError:
        print(f"✗ File SQL non trovato: {sql_file_path}")
        return False

def update_enabled_modules():
    """Aggiorna il file enabled_modules.json per includere gli ingredienti"""
    try:
        enabled_modules_path = Path(__file__).parent.parent / 'app' / 'enabled_modules.json'
        
        if enabled_modules_path.exists():
            with open(enabled_modules_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if 'ingredients' not in config.get('enabled_modules', []):
                config['enabled_modules'].append('ingredients')
                
                with open(enabled_modules_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                print("✓ Modulo 'ingredients' aggiunto ai moduli abilitati")
            else:
                print("⚠ Modulo 'ingredients' già presente nei moduli abilitati")
        else:
            print("⚠ File enabled_modules.json non trovato")
            
    except Exception as e:
        print(f"✗ Errore aggiornamento moduli abilitati: {e}")

def verify_installation(config):
    """Verifica che l'installazione sia andata a buon fine"""
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        tables_to_verify = [
            ('dat_fornitore', 'IdFornitore'),
            ('dat_ingrediente', 'IdIngrediente'),
            ('dat_fornitore_ingrediente', 'IdFornitoreIngrediente'),
            ('dat_articolo_ingrediente', 'IdArticoloIngrediente')
        ]
        
        all_ok = True
        for table_name, primary_key in tables_to_verify:
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            
            if columns:
                print(f"✓ Tabella {table_name}: {len(columns)} colonne")
            else:
                print(f"✗ Tabella {table_name}: non trovata o vuota")
                all_ok = False
        
        # Test di inserimento di prova
        try:
            cursor.execute("""
                INSERT INTO dat_fornitore (IdEmpresa, NomeFornitore, Attivo, Usuario, TimeStamp)
                VALUES (1, 'Fornitore Test', 1, 'migration_test', NOW())
            """)
            fornitore_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO dat_ingrediente (IdEmpresa, NomeIngrediente, UnitaMisura, Attivo, Usuario, TimeStamp)
                VALUES (1, 'Ingrediente Test', 'kg', 1, 'migration_test', NOW())
            """)
            ingrediente_id = cursor.lastrowid
            
            # Rimuovi i record di test
            cursor.execute(f"DELETE FROM dat_fornitore WHERE IdFornitore = {fornitore_id}")
            cursor.execute(f"DELETE FROM dat_ingrediente WHERE IdIngrediente = {ingrediente_id}")
            
            conn.commit()
            print("✓ Test di inserimento/eliminazione completato con successo")
            
        except mysql.connector.Error as err:
            print(f"✗ Errore nel test di inserimento: {err}")
            all_ok = False
        
        cursor.close()
        conn.close()
        
        return all_ok
        
    except mysql.connector.Error as err:
        print(f"✗ Errore verifica installazione: {err}")
        return False

def main():
    """Funzione principale"""
    print("=" * 60)
    print("DBLogiX - Migrazione Gestione Ingredienti")
    print("=" * 60)
    
    # 1. Carica configurazione database
    print("\n1. Caricamento configurazione database...")
    db_config = load_db_config()
    print(f"   Host: {db_config['host']}:{db_config['port']}")
    print(f"   Database: {db_config['database']}")
    print(f"   User: {db_config['user']}")
    
    # 2. Testa connessione
    print("\n2. Test connessione al database...")
    if not test_connection(db_config):
        print("✗ Impossibile continuare senza connessione al database")
        return False
    
    # 3. Controlla tabelle esistenti
    print("\n3. Controllo tabelle esistenti...")
    existing_tables = check_existing_tables(db_config)
    if existing_tables:
        print(f"⚠ Trovate {len(existing_tables)} tabelle già esistenti:")
        for table in existing_tables:
            print(f"   - {table}")
        
        response = input("\nContinuare comunque? (y/N): ").lower()
        if response not in ['y', 'yes', 'si', 's']:
            print("Operazione annullata dall'utente")
            return False
    
    # 4. Esegui migrazione SQL
    print("\n4. Esecuzione migrazione SQL...")
    sql_file = Path(__file__).parent / 'create_ingredients_tables_mysql.sql'
    if not execute_sql_file(db_config, sql_file):
        print("✗ Migrazione SQL fallita")
        return False
    
    # 5. Aggiorna moduli abilitati
    print("\n5. Aggiornamento configurazione moduli...")
    update_enabled_modules()
    
    # 6. Verifica installazione
    print("\n6. Verifica installazione...")
    if verify_installation(db_config):
        print("\n" + "=" * 60)
        print("✓ MIGRAZIONE COMPLETATA CON SUCCESSO!")
        print("=" * 60)
        print("\nProssimi passi:")
        print("1. Riavvia l'applicazione DBLogiX")
        print("2. Vai su Prodotti > Ingredienti per iniziare")
        print("3. Configura fornitori e ingredienti")
        print("4. Associa ingredienti agli articoli per il calcolo food cost")
        return True
    else:
        print("\n✗ MIGRAZIONE COMPLETATA CON ERRORI")
        print("Controlla i log sopra per maggiori dettagli")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nOperazione interrotta dall'utente")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Errore imprevisto: {e}")
        sys.exit(1)
