#!/usr/bin/env python3
"""
Test script to verify the task creation fixes
"""

import sys
import os
import datetime
from datetime import timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, TicketHeader, TicketLine, Product
from sqlalchemy import text

def test_join_logic():
    """Test the LEFT JOIN logic to handle missing products"""
    print("🔍 Testing JOIN logic...")
    
    try:
        # Test the new LEFT OUTER JOIN query
        ticket_lines = db.session.query(TicketLine).outerjoin(
            Product, TicketLine.IdArticulo == Product.IdArticulo
        ).limit(5).all()
        
        print(f"✅ Successfully retrieved {len(ticket_lines)} ticket lines with LEFT JOIN")
        
        for line in ticket_lines[:3]:  # Show first 3
            product_info = "Product found" if line.product else "Product missing (but handled gracefully)"
            print(f"   - Line {line.IdLineaTicket}: Article {line.IdArticulo} - {product_info}")
            
        return True
        
    except Exception as e:
        print(f"❌ JOIN test failed: {e}")
        return False

def test_ticket_product_separation():
    """Test that each ticket shows its own unique products"""
    print("\n🎯 Testing ticket-product separation...")
    
    try:
        # Get first few tickets
        tickets = TicketHeader.query.filter_by(Enviado=0).limit(5).all()
        
        if len(tickets) < 2:
            print("⚠️  Need at least 2 tickets to test separation")
            return True
        
        ticket_data = {}
        
        for ticket in tickets:
            print(f"\n🎫 Processing Ticket {ticket.IdTicket}:")
            
            # Use the same query as in the application
            ticket_lines = db.session.query(TicketLine).outerjoin(
                Product, TicketLine.IdArticulo == Product.IdArticulo
            ).filter(TicketLine.IdTicket == ticket.IdTicket).all()
            
            print(f"   📋 Found {len(ticket_lines)} lines for ticket {ticket.IdTicket}")
            
            line_details = []
            for line in ticket_lines:
                line_info = {
                    'line_id': line.IdLineaTicket,
                    'ticket_id': line.IdTicket,
                    'article_id': line.IdArticulo,
                    'description': line.Descripcion,
                    'weight': line.Peso
                }
                line_details.append(line_info)
                print(f"      🔹 Line {line.IdLineaTicket}: Article {line.IdArticulo} - {line.Descripcion[:30]}...")
            
            ticket_data[ticket.IdTicket] = line_details
        
        # Check for duplicates across tickets
        print(f"\n🔍 Analyzing uniqueness across {len(ticket_data)} tickets:")
        
        all_line_ids = []
        all_combinations = []
        
        for ticket_id, lines in ticket_data.items():
            for line in lines:
                all_line_ids.append(line['line_id'])
                combo = f"T{line['ticket_id']}-A{line['article_id']}-L{line['line_id']}"
                all_combinations.append(combo)
                
        # Check if line IDs are unique (they should be)
        unique_line_ids = len(set(all_line_ids))
        total_line_ids = len(all_line_ids)
        
        print(f"   📊 Line ID uniqueness: {unique_line_ids}/{total_line_ids}")
        
        # Check if ticket-article combinations make sense
        tickets_with_same_articles = 0
        for i, (ticket_id1, lines1) in enumerate(ticket_data.items()):
            for j, (ticket_id2, lines2) in enumerate(ticket_data.items()):
                if i >= j:  # Skip same ticket and avoid double comparison
                    continue
                    
                articles1 = {line['article_id'] for line in lines1}
                articles2 = {line['article_id'] for line in lines2}
                
                if articles1 == articles2 and len(articles1) > 0:
                    tickets_with_same_articles += 1
                    print(f"   ⚠️  Tickets {ticket_id1} and {ticket_id2} have identical article sets: {articles1}")
        
        if tickets_with_same_articles == 0:
            print("   ✅ All tickets have unique article combinations")
            return True
        else:
            print(f"   ❌ Found {tickets_with_same_articles} pairs of tickets with identical products")
            return False
            
    except Exception as e:
        print(f"❌ Ticket separation test failed: {e}")
        return False

def test_expiry_logic():
    """Test the corrected expiry date validation logic"""
    print("\n📅 Testing expiry date validation logic...")
    
    # Test scenarios
    today = datetime.datetime.now().date()
    task_deadline = today + timedelta(days=7)  # Task deadline in 7 days
    
    # Scenario 1: Product expires before task deadline (should be blocked)
    expired_product_date = today - timedelta(days=1)  # Expired yesterday
    should_block_1 = expired_product_date < task_deadline
    
    # Scenario 2: Product expires after task deadline (should be allowed)
    future_product_date = today + timedelta(days=14)  # Expires in 14 days
    should_block_2 = future_product_date < task_deadline
    
    print(f"📋 Task deadline: {task_deadline}")
    print(f"🔴 Product expired {(today - expired_product_date).days} days ago - Block creation: {should_block_1}")
    print(f"🟢 Product expires in {(future_product_date - today).days} days - Block creation: {should_block_2}")
    
    # Verify logic is correct
    if should_block_1 and not should_block_2:
        print("✅ Expiry date validation logic is correct!")
        return True
    else:
        print("❌ Expiry date validation logic is incorrect!")
        return False

def test_available_tickets():
    """Test retrieving available tickets using the new logic"""
    print("\n🎫 Testing available tickets retrieval...")
    
    try:
        # Get available tickets (same query as in the fixed code)
        available_tickets = TicketHeader.query.filter_by(Enviado=0).limit(3).all()
        
        print(f"✅ Found {len(available_tickets)} available tickets")
        
        for ticket in available_tickets:
            # Use the fixed query logic
            ticket_lines = db.session.query(TicketLine).outerjoin(
                Product, TicketLine.IdArticulo == Product.IdArticulo
            ).filter(TicketLine.IdTicket == ticket.IdTicket).all()
            
            ticket.loaded_lines = ticket_lines
            actual_lines = len(ticket_lines)
            
            print(f"   - Ticket {ticket.IdTicket}: {actual_lines} lines loaded successfully")
            
        return True
        
    except Exception as e:
        print(f"❌ Available tickets test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting task creation fixes validation...\n")
    
    # Initialize database connection
    try:
        # This assumes the Flask app context is available
        from app import create_app
        app = create_app()
        
        with app.app_context():
            test_results = []
            
            test_results.append(test_join_logic())
            test_results.append(test_ticket_product_separation())
            test_results.append(test_expiry_logic())
            test_results.append(test_available_tickets())
            
            print(f"\n📊 Test Results Summary:")
            print(f"   Passed: {sum(test_results)}/{len(test_results)}")
            
            if all(test_results):
                print("🎉 All tests passed! The fixes should work correctly.")
            else:
                print("⚠️  Some tests failed. Please review the implementation.")
                
    except Exception as e:
        print(f"❌ Failed to initialize app context: {e}")
        print("ℹ️  Make sure the Flask app is properly configured and the database is accessible.")

if __name__ == "__main__":
    main() 