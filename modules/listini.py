from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, ListinoPrezziHeader, ListinoPrezziRiga, Product, Client
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from services.utils import admin_required, is_admin
from flask import current_app
from sqlalchemy import text

listini_bp = Blueprint('listini', __name__, template_folder='templates')

@listini_bp.route('/')
@login_required
@admin_required
def index():
    """Visualizza la lista di tutti i listini"""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    search_query = request.args.get('search', '', type=str).strip()
    
    # Reset page to 1 when performing a new search
    if search_query and page > 1:
        return redirect(url_for('listini.index', search=search_query, page=1))
    
    # Base query
    listini_query = ListinoPrezziHeader.query
    
    # Apply search filter if provided
    if search_query:
        current_app.logger.info(f"🔍 Listini Search: cercando '{search_query}' in tutti i listini")
        
        try:
            # Try to convert search to integer for ID search
            search_id = int(search_query)
            listini_query = listini_query.filter(
                db.or_(
                    ListinoPrezziHeader.IdListino == search_id,
                    ListinoPrezziHeader.NomeListino.ilike(f'%{search_query}%'),
                    ListinoPrezziHeader.Descrizione.ilike(f'%{search_query}%')
                )
            )
        except ValueError:
            # Search only by text fields if not a number
            listini_query = listini_query.filter(
                db.or_(
                    ListinoPrezziHeader.NomeListino.ilike(f'%{search_query}%'),
                    ListinoPrezziHeader.Descrizione.ilike(f'%{search_query}%')
                )
            )
    
    # Order and paginate
    pagination = listini_query.order_by(ListinoPrezziHeader.IdListino.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    current_app.logger.info(f"📄 Listini page {page}: showing {len(pagination.items)} of {pagination.total} total listini")
    
    return render_template('listini/index.html', 
                         listini=pagination.items, 
                         pagination=pagination, 
                         search=search_query)

@listini_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new():
    """Crea un nuovo listino"""
    if request.method == 'POST':
        try:
            nome_listino = request.form.get('NomeListino', '').strip()
            descrizione = request.form.get('Descrizione', '').strip()
            
            # Validazione
            if not nome_listino:
                flash('Il nome del listino è obbligatorio', 'error')
                return render_template('listini/new.html')
            
            # Verifica che il nome non esista già
            existing = ListinoPrezziHeader.query.filter_by(NomeListino=nome_listino).first()
            if existing:
                flash('Esiste già un listino con questo nome', 'error')
                return render_template('listini/new.html')
            
            # Crea nuovo listino
            nuovo_listino = ListinoPrezziHeader(
                NomeListino=nome_listino,
                Descrizione=descrizione,
                CreatoDA=current_user.id,
                DataCreazione=datetime.utcnow()
            )
            
            db.session.add(nuovo_listino)
            db.session.commit()
            
            current_app.logger.info(f"✅ Nuovo listino creato: ID {nuovo_listino.IdListino}, Nome: {nome_listino}")
            flash(f'Listino "{nome_listino}" creato con successo', 'success')
            
            return redirect(url_for('listini.view', id=nuovo_listino.IdListino))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Errore creazione listino: {str(e)}")
            flash('Errore durante la creazione del listino', 'error')
            
    return render_template('listini/new.html')

@listini_bp.route('/<int:id>')
@login_required
def view(id):
    """Visualizza dettagli di un listino e i suoi articoli"""
    listino = ListinoPrezziHeader.query.get_or_404(id)
    
    # Paginazione per gli articoli del listino
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_query = request.args.get('search', '', type=str).strip()
    
    # Query per le righe del listino
    righe_query = ListinoPrezziRiga.query.filter_by(IdListino=id).join(Product)
    
    # Applica filtro di ricerca se fornito
    if search_query:
        try:
            # Try to convert search to integer for ID search
            search_id = int(search_query)
            righe_query = righe_query.filter(
                db.or_(
                    Product.IdArticulo == search_id,
                    Product.Descripcion.ilike(f'%{search_query}%'),
                    Product.EANScanner.ilike(f'%{search_query}%')
                )
            )
        except ValueError:
            # Search only by text fields if not a number
            righe_query = righe_query.filter(
                db.or_(
                    Product.Descripcion.ilike(f'%{search_query}%'),
                    Product.EANScanner.ilike(f'%{search_query}%')
                )
            )
    
    # Ordina e pagina
    pagination = righe_query.order_by(Product.Descripcion).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Conta clienti che usano questo listino e recupera i dati
    clienti_count = Client.query.filter_by(IdListino=id).count()
    clienti_associati = Client.query.filter_by(IdListino=id).order_by(Client.Nombre).all()
    
    return render_template('listini/view.html', 
                         listino=listino,
                         righe=pagination.items,
                         pagination=pagination,
                         search=search_query,
                         clienti_count=clienti_count,
                         clienti_associati=clienti_associati)

@listini_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    """Modifica le informazioni di un listino"""
    listino = ListinoPrezziHeader.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            nome_listino = request.form.get('NomeListino', '').strip()
            descrizione = request.form.get('Descrizione', '').strip()
            attivo = request.form.get('Attivo') is not None
            
            # Validazione
            if not nome_listino:
                flash('Il nome del listino è obbligatorio', 'error')
                return render_template('listini/edit.html', listino=listino)
            
            # Verifica che il nome non esista già (escludendo il listino corrente)
            existing = ListinoPrezziHeader.query.filter(
                ListinoPrezziHeader.NomeListino == nome_listino,
                ListinoPrezziHeader.IdListino != id
            ).first()
            if existing:
                flash('Esiste già un listino con questo nome', 'error')
                return render_template('listini/edit.html', listino=listino)
            
            # Aggiorna listino
            listino.NomeListino = nome_listino
            listino.Descrizione = descrizione
            listino.Attivo = attivo
            listino.DataModifica = datetime.utcnow()
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Listino aggiornato: ID {id}, Nome: {nome_listino}")
            flash(f'Listino "{nome_listino}" aggiornato con successo', 'success')
            
            return redirect(url_for('listini.view', id=id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Errore aggiornamento listino: {str(e)}")
            flash('Errore durante l\'aggiornamento del listino', 'error')
    
    return render_template('listini/edit.html', listino=listino)

@listini_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(id):
    """Elimina un listino e tutte le sue righe, rimuovendo automaticamente le associazioni dai clienti"""
    listino = ListinoPrezziHeader.query.get_or_404(id)
    
    try:
        nome_listino = listino.NomeListino
        
        # Trova tutti i clienti che usano questo listino
        clienti_associati = Client.query.filter_by(IdListino=id).all()
        clienti_count = len(clienti_associati)
        
        # Rimuovi l'associazione del listino da tutti i clienti
        if clienti_associati:
            for cliente in clienti_associati:
                cliente.IdListino = None
                current_app.logger.info(f"🔗 Rimossa associazione listino {id} dal cliente {cliente.IdCliente} ({cliente.Nombre})")
        
        # L'eliminazione delle righe è automatica grazie al CASCADE
        db.session.delete(listino)
        db.session.commit()
        
        current_app.logger.info(f"✅ Listino eliminato: ID {id}, Nome: {nome_listino}, {clienti_count} clienti scollegati")
        
        if clienti_count > 0:
            flash(f'Listino "{nome_listino}" eliminato con successo. {clienti_count} cliente/i ora utilizzano i prezzi standard.', 'success')
        else:
            flash(f'Listino "{nome_listino}" eliminato con successo', 'success')
        
        return redirect(url_for('listini.index'))
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore eliminazione listino: {str(e)}")
        flash('Errore durante l\'eliminazione del listino', 'error')
        return redirect(url_for('listini.view', id=id))

@listini_bp.route('/<int:id>/aggiungi_articoli', methods=['GET', 'POST'])
@login_required
@admin_required
def aggiungi_articoli(id):
    """Aggiunge articoli al listino con i prezzi specificati"""
    listino = ListinoPrezziHeader.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            articoli_selezionati = request.form.getlist('articoli_selezionati')
            
            if not articoli_selezionati:
                flash('Seleziona almeno un articolo da aggiungere', 'warning')
                return redirect(url_for('listini.aggiungi_articoli', id=id))
            
            articoli_aggiunti = 0
            articoli_esistenti = 0
            
            for id_articolo in articoli_selezionati:
                prezzo = request.form.get(f'prezzo_{id_articolo}', 0.0)
                
                try:
                    prezzo = float(prezzo) if prezzo else 0.0
                    if prezzo < 0:
                        flash(f'Il prezzo per l\'articolo {id_articolo} non può essere negativo', 'warning')
                        continue
                except ValueError:
                    flash(f'Prezzo non valido per l\'articolo {id_articolo}', 'warning')
                    continue
                
                # Verifica se l'articolo esiste già nel listino
                riga_esistente = ListinoPrezziRiga.query.filter_by(
                    IdListino=id, 
                    IdArticolo=id_articolo
                ).first()
                
                if riga_esistente:
                    articoli_esistenti += 1
                    continue
                
                # Aggiungi nuovo articolo al listino
                nuova_riga = ListinoPrezziRiga(
                    IdListino=id,
                    IdArticolo=id_articolo,
                    Prezzo=prezzo,
                    DataCreazione=datetime.utcnow()
                )
                db.session.add(nuova_riga)
                articoli_aggiunti += 1
            
            db.session.commit()
            
            # Aggiorna data modifica listino
            listino.DataModifica = datetime.utcnow()
            db.session.commit()
            
            # Messaggio di feedback
            msg = f'{articoli_aggiunti} articoli aggiunti al listino'
            if articoli_esistenti > 0:
                msg += f', {articoli_esistenti} articoli erano già presenti'
            
            flash(msg, 'success')
            current_app.logger.info(f"✅ Articoli aggiunti al listino {id}: {articoli_aggiunti} nuovi, {articoli_esistenti} esistenti")
            
            return redirect(url_for('listini.view', id=id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Errore aggiunta articoli: {str(e)}")
            flash('Errore durante l\'aggiunta degli articoli', 'error')
    
    # GET: mostra form per selezionare articoli
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_query = request.args.get('search', '', type=str).strip()
    
    # Query per articoli non ancora nel listino
    articoli_query = Product.query.filter(
        ~Product.IdArticulo.in_(
            db.session.query(ListinoPrezziRiga.IdArticolo)
            .filter_by(IdListino=id)
            .subquery()
        )
    )
    
    # Applica filtro di ricerca
    if search_query:
        try:
            search_id = int(search_query)
            articoli_query = articoli_query.filter(
                db.or_(
                    Product.IdArticulo == search_id,
                    Product.Descripcion.ilike(f'%{search_query}%'),
                    Product.EANScanner.ilike(f'%{search_query}%')
                )
            )
        except ValueError:
            articoli_query = articoli_query.filter(
                db.or_(
                    Product.Descripcion.ilike(f'%{search_query}%'),
                    Product.EANScanner.ilike(f'%{search_query}%')
                )
            )
    
    pagination = articoli_query.order_by(Product.Descripcion).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('listini/aggiungi_articoli.html',
                         listino=listino,
                         articoli=pagination.items,
                         pagination=pagination,
                         search=search_query)

@listini_bp.route('/<int:listino_id>/rimuovi_articolo/<int:articolo_id>', methods=['POST'])
@login_required
@admin_required
def rimuovi_articolo(listino_id, articolo_id):
    """Rimuove un articolo dal listino"""
    try:
        riga = ListinoPrezziRiga.query.filter_by(
            IdListino=listino_id, 
            IdArticolo=articolo_id
        ).first_or_404()
        
        articolo_desc = riga.descrizione_articolo
        
        db.session.delete(riga)
        db.session.commit()
        
        # Aggiorna data modifica listino
        listino = ListinoPrezziHeader.query.get(listino_id)
        if listino:
            listino.DataModifica = datetime.utcnow()
            db.session.commit()
        
        current_app.logger.info(f"✅ Articolo rimosso dal listino {listino_id}: {articolo_desc}")
        flash(f'Articolo "{articolo_desc}" rimosso dal listino', 'success')
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore rimozione articolo: {str(e)}")
        flash('Errore durante la rimozione dell\'articolo', 'error')
    
    return redirect(url_for('listini.view', id=listino_id))

@listini_bp.route('/<int:listino_id>/modifica_prezzo/<int:articolo_id>', methods=['POST'])
@login_required
@admin_required
def modifica_prezzo(listino_id, articolo_id):
    """Modifica il prezzo di un articolo nel listino"""
    try:
        riga = ListinoPrezziRiga.query.filter_by(
            IdListino=listino_id, 
            IdArticolo=articolo_id
        ).first_or_404()
        
        nuovo_prezzo = request.form.get('prezzo', 0.0)
        
        try:
            nuovo_prezzo = float(nuovo_prezzo) if nuovo_prezzo else 0.0
            if nuovo_prezzo < 0:
                flash('Il prezzo non può essere negativo', 'error')
                return redirect(url_for('listini.view', id=listino_id))
        except ValueError:
            flash('Prezzo non valido', 'error')
            return redirect(url_for('listini.view', id=listino_id))
        
        riga.Prezzo = nuovo_prezzo
        riga.DataModifica = datetime.utcnow()
        db.session.commit()
        
        # Aggiorna data modifica listino
        listino = ListinoPrezziHeader.query.get(listino_id)
        if listino:
            listino.DataModifica = datetime.utcnow()
            db.session.commit()
        
        current_app.logger.info(f"✅ Prezzo aggiornato nel listino {listino_id}: articolo {articolo_id}, nuovo prezzo {nuovo_prezzo}")
        flash(f'Prezzo aggiornato a €{nuovo_prezzo:.3f}', 'success')
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore modifica prezzo: {str(e)}")
        flash('Errore durante la modifica del prezzo', 'error')
    
    return redirect(url_for('listini.view', id=listino_id))

@listini_bp.route('/<int:id>/copia', methods=['POST'])
@login_required
@admin_required
def copia_listino(id):
    """Crea una copia di un listino esistente"""
    listino_originale = ListinoPrezziHeader.query.get_or_404(id)
    
    try:
        nuovo_nome = request.form.get('nuovo_nome', '').strip()
        
        if not nuovo_nome:
            flash('Il nome del nuovo listino è obbligatorio', 'error')
            return redirect(url_for('listini.view', id=id))
        
        # Verifica che il nome non esista già
        existing = ListinoPrezziHeader.query.filter_by(NomeListino=nuovo_nome).first()
        if existing:
            flash('Esiste già un listino con questo nome', 'error')
            return redirect(url_for('listini.view', id=id))
        
        # Crea nuovo listino
        nuovo_listino = ListinoPrezziHeader(
            NomeListino=nuovo_nome,
            Descrizione=f"Copia di: {listino_originale.Descrizione}" if listino_originale.Descrizione else None,
            CreatoDA=current_user.id,
            DataCreazione=datetime.utcnow()
        )
        
        db.session.add(nuovo_listino)
        db.session.flush()  # Per ottenere l'ID
        
        # Copia tutte le righe del listino originale
        righe_originali = ListinoPrezziRiga.query.filter_by(IdListino=id).all()
        
        for riga in righe_originali:
            nuova_riga = ListinoPrezziRiga(
                IdListino=nuovo_listino.IdListino,
                IdArticolo=riga.IdArticolo,
                Prezzo=riga.Prezzo,
                DataCreazione=datetime.utcnow()
            )
            db.session.add(nuova_riga)
        
        db.session.commit()
        
        current_app.logger.info(f"✅ Listino copiato: ID originale {id}, nuovo ID {nuovo_listino.IdListino}, {len(righe_originali)} articoli copiati")
        flash(f'Listino copiato con successo. Nuovo listino: "{nuovo_nome}"', 'success')
        
        return redirect(url_for('listini.view', id=nuovo_listino.IdListino))
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore copia listino: {str(e)}")
        flash('Errore durante la copia del listino', 'error')
        return redirect(url_for('listini.view', id=id))

@listini_bp.route('/<int:listino_id>/api/articoli_disponibili')
@login_required
@admin_required
def api_articoli_disponibili(listino_id):
    """API endpoint per ottenere tutti gli ID degli articoli disponibili per il listino"""
    try:
        search_query = request.args.get('search', '', type=str).strip()
        
        # Query per articoli non ancora nel listino
        articoli_query = Product.query.filter(
            ~Product.IdArticulo.in_(
                db.session.query(ListinoPrezziRiga.IdArticolo)
                .filter_by(IdListino=listino_id)
                .subquery()
            )
        )
        
        # Applica filtro di ricerca se presente
        if search_query:
            try:
                search_id = int(search_query)
                articoli_query = articoli_query.filter(
                    db.or_(
                        Product.IdArticulo == search_id,
                        Product.Descripcion.ilike(f'%{search_query}%'),
                        Product.EANScanner.ilike(f'%{search_query}%')
                    )
                )
            except ValueError:
                articoli_query = articoli_query.filter(
                    db.or_(
                        Product.Descripcion.ilike(f'%{search_query}%'),
                        Product.EANScanner.ilike(f'%{search_query}%')
                    )
                )
        
        # Ottieni tutti gli ID articoli (senza paginazione)
        articoli_ids = [articolo.IdArticulo for articolo in articoli_query.all()]
        
        return jsonify({
            'success': True,
            'articoli_ids': articoli_ids,
            'total': len(articoli_ids)
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore API articoli disponibili: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@listini_bp.route('/<int:listino_id>/api/search_clients')
@login_required
@admin_required
def api_search_clients(listino_id):
    """API per cercare clienti da associare al listino"""
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify([])
        
        # Cerca clienti per nome, email o ID
        clients_query = Client.query
        
        try:
            # Try to convert search to integer for ID search
            search_id = int(query)
            clients_query = clients_query.filter(
                db.or_(
                    Client.IdCliente == search_id,
                    Client.Nombre.ilike(f'%{query}%'),
                    Client.Email.ilike(f'%{query}%')
                )
            )
        except ValueError:
            # Search only by text fields if not a number
            clients_query = clients_query.filter(
                db.or_(
                    Client.Nombre.ilike(f'%{query}%'),
                    Client.Email.ilike(f'%{query}%')
                )
            )
        
        clients = clients_query.order_by(Client.Nombre).limit(20).all()
        
        clients_data = []
        for client in clients:
            clients_data.append({
                'IdCliente': client.IdCliente,
                'Nombre': client.Nombre,
                'Email': client.Email,
                'Telefono1': client.Telefono1,
                'Poblacion': client.Poblacion,
                'Provincia': client.Provincia,
                'IdListino': client.IdListino
            })
        
        return jsonify(clients_data)
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore ricerca clienti: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@listini_bp.route('/<int:listino_id>/assign_client/<int:client_id>', methods=['POST'])
@login_required
@admin_required
def assign_client_to_listino(listino_id, client_id):
    """API per associare un cliente al listino"""
    try:
        listino = ListinoPrezziHeader.query.get_or_404(listino_id)
        client = Client.query.get_or_404(client_id)
        
        # Aggiorna il cliente con il nuovo listino
        client.IdListino = listino_id
        db.session.commit()
        
        current_app.logger.info(f"✅ Cliente {client_id} ({client.Nombre}) associato al listino {listino_id}")
        
        return jsonify({
            'success': True,
            'message': f'Cliente "{client.Nombre}" associato con successo al listino "{listino.NomeListino}"'
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore assegnazione cliente al listino: {str(e)}")
        return jsonify({'success': False, 'error': 'Errore durante l\'assegnazione'}), 500

@listini_bp.route('/<int:listino_id>/remove_client/<int:client_id>', methods=['POST'])
@login_required
@admin_required
def remove_client_from_listino(listino_id, client_id):
    """Rimuove un cliente dal listino (reimposta a prezzi standard)"""
    try:
        client = Client.query.get_or_404(client_id)
        
        # Verifica che il cliente sia effettivamente associato a questo listino
        if client.IdListino != listino_id:
            flash('Il cliente non è associato a questo listino', 'error')
            return redirect(url_for('listini.view', id=listino_id))
        
        # Rimuovi l'associazione
        client.IdListino = None
        db.session.commit()
        
        current_app.logger.info(f"✅ Cliente {client_id} ({client.Nombre}) rimosso dal listino {listino_id}")
        flash(f'Cliente "{client.Nombre}" rimosso dal listino con successo', 'success')
        
        return redirect(url_for('listini.view', id=listino_id))
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore rimozione cliente dal listino: {str(e)}")
        flash('Errore durante la rimozione del cliente dal listino', 'error')
        return redirect(url_for('listini.view', id=listino_id))

@listini_bp.route('/api/prezzi_per_cliente/<int:cliente_id>')
@login_required
def api_prezzi_per_cliente(cliente_id):
    """API per ottenere i prezzi degli articoli per un cliente specifico"""
    try:
        cliente = Client.query.get_or_404(cliente_id)
        
        if cliente.IdListino:
            # Il cliente ha un listino personalizzato
            righe = ListinoPrezziRiga.query.filter_by(IdListino=cliente.IdListino).join(Product).all()
            prezzi = {
                riga.IdArticolo: {
                    'prezzo': float(riga.Prezzo),
                    'descrizione': riga.descrizione_articolo,
                    'fonte': 'listino'
                }
                for riga in righe
            }
        else:
            # Il cliente usa i prezzi standard
            articoli = Product.query.all()
            prezzi = {
                articolo.IdArticulo: {
                    'prezzo': float(articolo.PrecioConIVA) if articolo.PrecioConIVA else 0.0,
                    'descrizione': articolo.Descripcion,
                    'fonte': 'standard'
                }
                for articolo in articoli
            }
        
        return jsonify({
            'success': True,
            'cliente_id': cliente_id,
            'cliente_nome': cliente.Nombre,
            'listino_id': cliente.IdListino,
            'listino_nome': cliente.listino.NomeListino if cliente.listino else 'Prezzi Standard',
            'prezzi': prezzi
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore API prezzi cliente: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Errore durante il recupero dei prezzi'
        }), 500 