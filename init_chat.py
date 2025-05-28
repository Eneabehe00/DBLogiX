#!/usr/bin/env python3
"""
Script per inizializzare le tabelle della chat nel database.
Eseguire questo script dopo aver aggiornato i modelli.
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, ChatMessage, ChatRoom, User
from datetime import datetime

def init_chat_tables():
    """Inizializza le tabelle della chat"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Creazione delle tabelle della chat...")
            
            # Create chat tables
            db.create_all()
            
            # Check if global chat room exists, if not create it
            global_room = ChatRoom.query.filter_by(is_global=True).first()
            if not global_room:
                print("Creazione della chat room globale...")
                global_room = ChatRoom(
                    name="Chat Globale",
                    description="Chat globale per tutti gli utenti",
                    is_global=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(global_room)
                db.session.commit()
                print("Chat room globale creata con successo!")
            else:
                print("Chat room globale già esistente.")
            
            print("Inizializzazione completata con successo!")
            print("\nPer testare la chat:")
            print("1. Avvia l'applicazione")
            print("2. Effettua il login")
            print("3. Clicca sull'icona della chat in basso a destra")
            
        except Exception as e:
            print(f"Errore durante l'inizializzazione: {str(e)}")
            db.session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    success = init_chat_tables()
    sys.exit(0 if success else 1) 