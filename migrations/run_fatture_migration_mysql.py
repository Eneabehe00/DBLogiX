#!/usr/bin/env python3
"""
Script per eseguire la migrazione delle tabelle Fatture su MySQL
Esegui questo script per creare le nuove tabelle nel database MySQL
"""

import pymysql
import os
import sys
from datetime import datetime

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def run_fatture_migration():
    """Esegue la migrazione per creare le tabelle Fatture su MySQL"""
    
    try:
        # Importa la configurazione del database
        from app.config import get_direct_connection_config
        
        db_config = get_direct_connection_config()
        print(f"🔌 Connessione al database MySQL: {db_config['host']}:{db_config['port']}")
        
        # Legge il file SQL della migrazione
        migration_file = os.path.join(os.path.dirname(__file__), 'create_fatture_table_mysql.sql')
        
        if not os.path.exists(migration_file):
            print(f"❌ File migrazione non trovato: {migration_file}")
            return False
        
        # Legge il contenuto del file SQL
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        
        # Connessione al database MySQL
        connection = pymysql.connect(**db_config)
        
        try:
            with connection.cursor() as cursor:
                print("🔄 Esecuzione migrazione tabelle Fatture...")
                
                # Esegue i comandi SQL (split per comando)
                commands = sql_commands.split(';')
                
                for i, command in enumerate(commands):
                    command = command.strip()
                    if command and not command.startswith('--'):
                        try:
                            cursor.execute(command)
                            
                            if 'CREATE TABLE' in command.upper():
                                table_name = command.split('TABLE')[1].split('(')[0].strip().replace('IF NOT EXISTS', '').strip()
                                print(f"   ✅ Tabella creata: {table_name}")
                                
                        except pymysql.Error as e:
                            if 'already exists' in str(e).lower() or 'table already exists' in str(e).lower():
                                print(f"   ⚠️  Tabella già esistente: {str(e)}")
                            else:
                                print(f"   ❌ Errore comando {i+1}: {str(e)}")
                                raise
                
                # Commit delle modifiche
                connection.commit()
                
                # Verifica che le tabelle siano state create
                cursor.execute("SHOW TABLES LIKE 'Fatture%'")
                created_tables = cursor.fetchall()
                
                print(f"\n✅ Migrazione completata con successo!")
                print(f"📋 Tabelle create: {[table[0] for table in created_tables]}")
                
                # Mostra la struttura delle tabelle create
                for table_name in ['Fatture', 'FattureLinee']:
                    try:
                        cursor.execute(f"DESCRIBE {table_name}")
                        columns = cursor.fetchall()
                        print(f"\n📊 Struttura tabella {table_name}:")
                        for col in columns:
                            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                            default = f" DEFAULT {col[4]}" if col[4] is not None else ""
                            print(f"   - {col[0]} ({col[1]}) {nullable}{default}")
                    except pymysql.Error as e:
                        print(f"   ⚠️  Impossibile mostrare struttura {table_name}: {str(e)}")
        
        finally:
            connection.close()
            
        return True
        
    except Exception as e:
        print(f"❌ Errore durante la migrazione: {str(e)}")
        return False


def verify_migration():
    """Verifica che la migrazione sia stata completata correttamente"""
    
    try:
        from app.config import get_direct_connection_config
        
        db_config = get_direct_connection_config()
        connection = pymysql.connect(**db_config)
        
        try:
            with connection.cursor() as cursor:
                print("\n🔍 Verifica migrazione...")
                
                # Controlla l'esistenza delle tabelle
                cursor.execute("SHOW TABLES LIKE 'Fatture%'")
                tables = cursor.fetchall()
                
                if len(tables) == 2:
                    print("✅ Tutte le tabelle sono presenti")
                    
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
                    
                    try:
                        cursor.execute("""
                            INSERT INTO Fatture (
                                NumeroFattura, DataFattura, IdCliente, NomeCliente, 
                                IdEmpresa, NomeEmpresa, PartitaIVAEmpresa, NomeFileXML
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            test_data['NumeroFattura'], test_data['DataFattura'],
                            test_data['IdCliente'], test_data['NomeCliente'],
                            test_data['IdEmpresa'], test_data['NomeEmpresa'],
                            test_data['PartitaIVAEmpresa'], test_data['NomeFileXML']
                        ))
                        
                        # Legge il record inserito
                        cursor.execute("SELECT IdFattura FROM Fatture WHERE NumeroFattura = %s", (test_data['NumeroFattura'],))
                        result = cursor.fetchone()
                        
                        if result:
                            print("✅ Test inserimento/lettura riuscito")
                            # Pulisce il record di test
                            cursor.execute("DELETE FROM Fatture WHERE NumeroFattura = %s", (test_data['NumeroFattura'],))
                            connection.commit()
                        else:
                            print("❌ Test inserimento/lettura fallito")
                            return False
                            
                    except pymysql.Error as e:
                        print(f"❌ Errore nel test di inserimento: {str(e)}")
                        return False
                    
                else:
                    print(f"❌ Tabelle mancanti. Trovate: {[t[0] for t in tables]}")
                    return False
        
        finally:
            connection.close()
            
        return True
        
    except Exception as e:
        print(f"❌ Errore durante la verifica: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 Avvio migrazione tabelle Fatture su MySQL...")
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