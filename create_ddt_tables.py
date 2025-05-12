#!/usr/bin/env python
import pymysql
import os
from config import REMOTE_DB_CONFIG

def create_ddt_tables():
    """Create the DDT tables in the database if they don't already exist."""
    
    # Connect to the database
    try:
        conn = pymysql.connect(
            host=REMOTE_DB_CONFIG['host'],
            user=REMOTE_DB_CONFIG['user'],
            password=REMOTE_DB_CONFIG['password'],
            database=REMOTE_DB_CONFIG['database'],
            charset='utf8',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return False
    
    cursor = conn.cursor()
    
    # SQL statements to create the tables
    create_ddt_head = """
    CREATE TABLE IF NOT EXISTS ddt_head (
      id INT AUTO_INCREMENT PRIMARY KEY,
      id_cliente INT NOT NULL,
      id_empresa INT NOT NULL,
      data_creazione DATETIME,
      totale_senza_iva DECIMAL(10,2) DEFAULT 0,
      totale_iva DECIMAL(10,2) DEFAULT 0,
      totale_importo DECIMAL(10,2) DEFAULT 0,
      INDEX idx_cliente (id_cliente),
      INDEX idx_empresa (id_empresa)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
    """
    
    create_ddt_line = """
    CREATE TABLE IF NOT EXISTS ddt_line (
      id INT AUTO_INCREMENT PRIMARY KEY,
      id_ddt INT NOT NULL,
      id_empresa INT NOT NULL,
      id_tienda INT NOT NULL,
      id_balanza_maestra INT NOT NULL,
      id_balanza_esclava INT NOT NULL,
      tipo_venta TINYINT(1) NOT NULL,
      id_ticket BIGINT(20) NOT NULL,
      INDEX idx_ddt (id_ddt),
      INDEX idx_ticket (id_empresa, id_tienda, id_balanza_maestra, id_balanza_esclava, tipo_venta, id_ticket),
      FOREIGN KEY (id_ddt) REFERENCES ddt_head(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
    """
    
    try:
        print("Creating ddt_head table...")
        cursor.execute(create_ddt_head)
        
        print("Creating ddt_line table...")
        cursor.execute(create_ddt_line)
        
        conn.commit()
        print("DDT tables created successfully.")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error creating DDT tables: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # Override config with environment variables if present
    db_host = os.environ.get('DB_HOST')
    db_user = os.environ.get('DB_USER')
    db_pass = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')
    db_port = os.environ.get('DB_PORT')
    
    # Update config from environment variables if provided
    if db_host: REMOTE_DB_CONFIG['host'] = db_host
    if db_user: REMOTE_DB_CONFIG['user'] = db_user
    if db_pass: REMOTE_DB_CONFIG['password'] = db_pass
    if db_name: REMOTE_DB_CONFIG['database'] = db_name
    if db_port: REMOTE_DB_CONFIG['port'] = int(db_port)
    
    print(f"Creating DDT tables in database {REMOTE_DB_CONFIG['database']} on {REMOTE_DB_CONFIG['host']}...")
    create_ddt_tables() 