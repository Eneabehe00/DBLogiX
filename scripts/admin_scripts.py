#!/usr/bin/env python3
"""
Script di amministrazione per la gestione degli stati dei ticket
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, TicketHeader, TicketLine, Task, TaskTicket
from modules.warehouse import update_expired_tickets, reset_non_expired_tickets_to_giacenza

def check_ticket_states():
    """Controlla e mostra lo stato di tutti i ticket"""
    app = create_app()
    with app.app_context():
        print("=== STATO ATTUALE DEI TICKET ===\n")
        
        # Conteggi per stato
        states = {
            0: "Giacenza",
            1: "Processato", 
            2: "DDT1",
            3: "DDT2",
            4: "Scaduto",
            10: "Task"
        }
        
        print("Conteggio ticket per stato:")
        for state_code, state_name in states.items():
            count = TicketHeader.query.filter_by(Enviado=state_code).count()
            print(f"  {state_name} ({state_code}): {count} ticket")
        
        print(f"\nTotale ticket: {TicketHeader.query.count()}")
        
        # Mostra ticket in task attivi
        print("\n=== TICKET IN TASK ATTIVI ===")
        active_tasks = Task.query.filter(Task.status.in_(['pending', 'assigned', 'in_progress'])).all()
        for task in active_tasks:
            print(f"Task {task.task_number}: {task.total_tickets} ticket")
            for task_ticket in task.task_tickets:
                ticket = task_ticket.ticket
                print(f"  - Ticket #{ticket.NumTicket} (ID: {ticket.IdTicket}) - Enviado: {ticket.Enviado} ({ticket.status_text})")

def fix_ticket_states():
    """Esegue le funzioni di correzione degli stati dei ticket"""
    app = create_app()
    with app.app_context():
        print("=== CORREZIONE STATI TICKET ===\n")
        
        print("1. Aggiornamento ticket scaduti...")
        update_expired_tickets()
        
        print("2. Reset ticket non scaduti da Task a Giacenza...")
        reset_non_expired_tickets_to_giacenza()
        
        print("\nCorrezione completata!")

def show_expired_tickets():
    """Mostra i ticket che dovrebbero essere scaduti"""
    app = create_app()
    with app.app_context():
        today = datetime.now().date()
        
        print("=== TICKET CON PRODOTTI SCADUTI ===\n")
        
        # Trova ticket con prodotti scaduti
        expired_tickets = db.session.query(TicketHeader).distinct().\
            join(TicketLine, TicketHeader.IdTicket == TicketLine.IdTicket).\
            filter(
                TicketLine.FechaCaducidad.isnot(None),
                db.func.date(TicketLine.FechaCaducidad) < today
            ).all()
        
        for ticket in expired_tickets:
            print(f"Ticket #{ticket.NumTicket} (ID: {ticket.IdTicket}) - Stato attuale: {ticket.status_text}")
            
            # Mostra prodotti scaduti in questo ticket
            expired_lines = TicketLine.query.filter(
                TicketLine.IdTicket == ticket.IdTicket,
                TicketLine.FechaCaducidad.isnot(None),
                db.func.date(TicketLine.FechaCaducidad) < today
            ).all()
            
            for line in expired_lines:
                days_expired = (today - line.FechaCaducidad.date()).days
                print(f"  - {line.Descripcion} (scaduto {days_expired} giorni fa)")
            print()

def show_task_tickets():
    """Mostra tutti i ticket associati a task"""
    app = create_app()
    with app.app_context():
        print("=== TICKET ASSOCIATI A TASK ===\n")
        
        task_tickets = TicketHeader.query.filter_by(Enviado=10).all()
        
        for ticket in task_tickets:
            print(f"Ticket #{ticket.NumTicket} (ID: {ticket.IdTicket})")
            
            # Trova il task associato
            task_ticket = TaskTicket.query.filter_by(ticket_id=ticket.IdTicket).first()
            if task_ticket:
                task = task_ticket.task
                print(f"  - Task: {task.task_number} ({task.status})")
                print(f"  - Creato: {task.created_at}")
                if task.deadline:
                    print(f"  - Scadenza: {task.deadline}")
            else:
                print("  - ERRORE: Ticket senza task associato!")
            
            # Controlla prodotti scaduti
            today = datetime.now().date()
            expired_lines = TicketLine.query.filter(
                TicketLine.IdTicket == ticket.IdTicket,
                TicketLine.FechaCaducidad.isnot(None),
                db.func.date(TicketLine.FechaCaducidad) < today
            ).count()
            
            non_expired_lines = TicketLine.query.filter(
                TicketLine.IdTicket == ticket.IdTicket,
                TicketLine.FechaCaducidad.isnot(None),
                db.func.date(TicketLine.FechaCaducidad) >= today
            ).count()
            
            print(f"  - Prodotti scaduti: {expired_lines}")
            print(f"  - Prodotti non scaduti: {non_expired_lines}")
            print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python admin_scripts.py [comando]")
        print("Comandi disponibili:")
        print("  check    - Controlla lo stato attuale dei ticket")
        print("  fix      - Corregge gli stati dei ticket")
        print("  expired  - Mostra ticket con prodotti scaduti") 
        print("  tasks    - Mostra ticket associati a task")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        check_ticket_states()
    elif command == "fix":
        fix_ticket_states()
    elif command == "expired":
        show_expired_tickets()
    elif command == "tasks":
        show_task_tickets()
    else:
        print(f"Comando sconosciuto: {command}")
        sys.exit(1) 