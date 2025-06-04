#!/usr/bin/env python3
"""
Debug script to examine database content
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, TicketHeader, TicketLine, Product
from sqlalchemy import text

def main():
    app = create_app()
    with app.app_context():
        print("🔍 Examining database content...\n")
        
        # Check table structure
        print("🏗️  Table structure for dat_ticket_linea:")
        result = db.session.execute(text("DESCRIBE dat_ticket_linea"))
        for row in result:
            print(f"  {row.Field}: {row.Type} (Key: {row.Key}, Null: {row.Null}, Default: {row.Default})")
        
        print("\n" + "="*80 + "\n")
        
        # Check raw ticket line data
        print("📋 Raw ticket line data (first 15 rows):")
        result = db.session.execute(text('SELECT IdLineaTicket, IdTicket, IdArticulo, Descripcion FROM dat_ticket_linea ORDER BY IdTicket, IdLineaTicket LIMIT 15'))
        for row in result:
            print(f"  Line {row.IdLineaTicket}: Ticket {row.IdTicket} -> Article {row.IdArticulo} ({row.Descripcion[:40]}...)")
        
        print("\n" + "="*80 + "\n")
        
        # Check for duplicate IdLineaTicket
        print("🔍 Checking for duplicate IdLineaTicket values:")
        result = db.session.execute(text('SELECT IdLineaTicket, COUNT(*) as count FROM dat_ticket_linea GROUP BY IdLineaTicket HAVING COUNT(*) > 1'))
        duplicates = list(result)
        if duplicates:
            print("  ⚠️  Found duplicate IdLineaTicket values:")
            for row in duplicates:
                print(f"    IdLineaTicket {row.IdLineaTicket} appears {row.count} times")
        else:
            print("  ✅ No duplicate IdLineaTicket values found")
        
        print("\n" + "="*80 + "\n")
        
        # Check available tickets
        print("🎫 Available tickets (Enviado=0):")
        tickets = TicketHeader.query.filter_by(Enviado=0).limit(10).all()
        for ticket in tickets:
            print(f"  Ticket {ticket.IdTicket}: NumTicket {ticket.NumTicket}, NumLineas {ticket.NumLineas}")
        
        print("\n" + "="*80 + "\n")
        
        # Test different ORM queries
        print("🔧 Testing different ORM query approaches:")
        for ticket in tickets[:3]:
            print(f"\n🎫 Ticket {ticket.IdTicket}:")
            
            # Method 1: Simple filter
            method1 = db.session.query(TicketLine).filter(TicketLine.IdTicket == ticket.IdTicket).all()
            print(f"  Method 1 (simple filter): {len(method1)} lines")
            for line in method1:
                print(f"    Line {line.IdLineaTicket}: Article {line.IdArticulo}")
            
            # Method 2: Using relationship
            try:
                if hasattr(ticket, 'lines'):
                    method2 = ticket.lines.all()
                    print(f"  Method 2 (relationship): {len(method2)} lines")
                    for line in method2:
                        print(f"    Line {line.IdLineaTicket}: Article {line.IdArticulo}")
                else:
                    print("  Method 2: No relationship defined")
            except Exception as e:
                print(f"  Method 2 error: {e}")
            
            # Method 3: Fresh session query
            fresh_lines = db.session.query(TicketLine).filter_by(IdTicket=ticket.IdTicket).all()
            print(f"  Method 3 (filter_by): {len(fresh_lines)} lines")
            for line in fresh_lines:
                print(f"    Line {line.IdLineaTicket}: Article {line.IdArticulo}")

if __name__ == "__main__":
    main() 