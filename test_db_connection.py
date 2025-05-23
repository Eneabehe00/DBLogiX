#!/usr/bin/env python
"""
MySQL Database Connection Tester
This script tests connections to a MySQL database server.
"""
import sys
import socket
import argparse
import pymysql
import time

def check_port_open(host, port, timeout=2):
    """Check if a TCP port is open on the specified host"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.close()
        return True
    except (socket.timeout, socket.error):
        return False

def test_mysql_connection(host, user, password, database, port=3306, charset='utf8'):
    """Test connection to MySQL database"""
    print(f"\nTesting MySQL connection to {host}:{port}...")
    
    # First check if port is open
    if not check_port_open(host, port):
        print(f"ERROR: Port {port} is closed on {host}. Cannot establish connection.")
        print("Please check:")
        print("  1. The database server is running")
        print("  2. Firewall settings allow connections")
        print("  3. The IP address is correct")
        return False
    
    print(f"✓ Port {port} is open on {host}")
    
    # Now try to connect
    try:
        print(f"Attempting to connect with user '{user}' to database '{database}'...")
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            connect_timeout=5,
            charset=charset
        )
        
        # Test the connection
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        print(f"✓ Connection successful! MySQL version: {version[0]}")
        return True
    
    except pymysql.err.OperationalError as e:
        error_code = e.args[0]
        if error_code == 1045:
            print("ERROR: Access denied. Invalid username or password.")
        elif error_code == 1049:
            print(f"ERROR: Database '{database}' does not exist.")
        elif error_code == 2003:
            print(f"ERROR: Cannot connect to MySQL server on '{host}'.")
            print("Please check:")
            print("  1. MySQL server is running")
            print("  2. The IP address is correct")
            print("  3. Firewall settings")
        else:
            print(f"ERROR: {str(e)}")
        return False
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test MySQL database connection')
    parser.add_argument('--host', required=True, help='Database host address')
    parser.add_argument('--user', default='user', help='Database username')
    parser.add_argument('--password', default='dibal', help='Database password')
    parser.add_argument('--database', default='sys_datos', help='Database name')
    parser.add_argument('--port', type=int, default=3306, help='Database port')
    parser.add_argument('--charset', default='utf8', help='Character set')
    
    args = parser.parse_args()
    
    print("\n=== MySQL Connection Tester ===")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"User: {args.user}")
    print(f"Database: {args.database}")
    print(f"Charset: {args.charset}")
    
    success = test_mysql_connection(
        args.host, 
        args.user, 
        args.password, 
        args.database, 
        args.port, 
        args.charset
    )
    
    if success:
        print("\nSUCCESS: Connection test passed!")
    else:
        print("\nFAILED: Connection test failed!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 