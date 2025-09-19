#!/usr/bin/env python3
"""
Script per eseguire la migrazione delle tabelle Fatture
Esegui questo script per creare le nuove tabelle nel database
"""

import sqlite3
import os
import sys
from datetime import datetime

def run_fatture_migration():
    """Esegue la migrazione per creare le tabelle Fatture"""
    
    # Percorso del database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database non trovato: {db_path}")
        return False
    
    # Legge il file SQL della migrazione
    migration_file = os.path.join(os.path.dirname(__file__), 'create_fatture_table.sql')
    
    if not os.path.exists(migration_file):
        print(f"❌ File migrazione non trovato: {migration_file}")
        return False
    
    try:
        # Legge il contenuto del file SQL
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        
        # Connessione al database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Esecuzione migrazione tabelle Fatture...")
        
        # Esegue i comandi SQL (split per comando)
        commands = sql_commands.split(';')
        
        for i, command in enumerate(commands):
            command = command.strip()
            if command:
                try:
                    cursor.execute(command)
                    if 'CREATE TABLE' in command.upper():
                        table_name = command.split('TABLE')[1].split('(')[0].strip()
                        print(f"   ✅ Tabella creata: {table_name}")
                    elif 'CREATE INDEX' in command.upper():
                        index_name = command.split('INDEX')[1].split('ON')[0].strip()
                        print(f"   ✅ Indice creato: {index_name}")
                    elif 'CREATE TRIGGER' in command.upper():
                        trigger_name = command.split('TRIGGER')[1].split('AFTER')[0].strip()
                        print(f"   ✅ Trigger creato: {trigger_name}")
                        
                except sqlite3.Error as e:
                    if 'already exists' in str(e).lower():
                        print(f"   ⚠️  Già esistente: {str(e)}")
                    else:
                        print(f"   ❌ Errore comando {i+1}: {str(e)}")
                        raise
        
        # Commit delle modifiche
        conn.commit()
        
        # Verifica che le tabelle siano state create
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('Fatture', 'FattureLinee')")
        created_tables = cursor.fetchall()
        
        print(f"\n✅ Migrazione completata con successo!")
        print(f"📋 Tabelle create: {[table[0] for table in created_tables]}")
        
        # Mostra la struttura delle tabelle create
        for table_name in ['Fatture', 'FattureLinee']:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"\n📊 Struttura tabella {table_name}:")
            for col in columns:
                print(f"   - {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Errore durante la migrazione: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


def verify_migration():
    """Verifica che la migrazione sia stata completata correttamente"""
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🔍 Verifica migrazione...")
        
        # Controlla l'esistenza delle tabelle
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('Fatture', 'FattureLinee')
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        if len(tables) == 2:
            print("✅ Tutte le tabelle sono presenti")
            
            # Controlla gli indici
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_fatture%'
                ORDER BY name
            """)
            indices = cursor.fetchall()
            print(f"✅ Indici creati: {len(indices)}")
            
            # Controlla i trigger
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='trigger' AND name LIKE '%fatture%'
            """)
            triggers = cursor.fetchall()
            print(f"✅ Trigger creati: {len(triggers)}")
            
            # Test inserimento/lettura
            test_data = {
                'NumeroFattura': 'TEST001',
                'DataFattura': datetime.now().date(),
                'IdCliente': 1,
                'NomeCliente': 'Test Cliente',
                'IdEmpresa': 1,
                'NomeEmpresa': 'Test Azienda',
                'PartitaIVAEmpresa': 'IT12345678901',
                'NomeFileXML': 'test.xml'
            }
            
            cursor.execute("""
                INSERT INTO Fatture (
                    NumeroFattura, DataFattura, IdCliente, NomeCliente, 
                    IdEmpresa, NomeEmpresa, PartitaIVAEmpresa, NomeFileXML
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_data['NumeroFattura'], test_data['DataFattura'],
                test_data['IdCliente'], test_data['NomeCliente'],
                test_data['IdEmpresa'], test_data['NomeEmpresa'],
                test_data['PartitaIVAEmpresa'], test_data['NomeFileXML']
            ))
            
            # Legge il record inserito
            cursor.execute("SELECT IdFattura FROM Fatture WHERE NumeroFattura = ?", (test_data['NumeroFattura'],))
            result = cursor.fetchone()
            
            if result:
                print("✅ Test inserimento/lettura riuscito")
                # Pulisce il record di test
                cursor.execute("DELETE FROM Fatture WHERE NumeroFattura = ?", (test_data['NumeroFattura'],))
                conn.commit()
            else:
                print("❌ Test inserimento/lettura fallito")
            
        else:
            print(f"❌ Tabelle mancanti. Trovate: {[t[0] for t in tables]}")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Errore durante la verifica: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 Avvio migrazione tabelle Fatture...")
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Esegue la migrazione
    if run_fatture_migration():
        print("\n" + "="*50)
        
        # Verifica la migrazione
        if verify_migration():
            print("\n🎉 Migrazione completata e verificata con successo!")
            sys.exit(0)
        else:
            print("\n❌ La verifica della migrazione è fallita!")
            sys.exit(1)
    else:
        print("\n❌ Migrazione fallita!")
        sys.exit(1) 