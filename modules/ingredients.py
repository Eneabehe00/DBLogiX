from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_, desc, asc, func
from app.models import db, Ingrediente, Fornitore, IngredienteFornitore, ArticoloIngrediente, Article, ViewFoodCost
from datetime import datetime
from decimal import Decimal
from services.utils import admin_required, is_admin
from services.pdf_invoice_processor import PDFInvoiceProcessor
from werkzeug.utils import secure_filename
import os
import logging

ingredients_bp = Blueprint('ingredients', __name__)

def parse_decimal(value):
    """Parse a decimal value from form input"""
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value).replace(',', '.'))
    except:
        return None

def format_price(price):
    """Format a price value for display"""
    if price is None:
        return 'N/A'
    try:
        return f"€ {float(price):.2f}".replace('.', ',')
    except (ValueError, TypeError):
        return 'N/A'

# ===========================================
# DASHBOARD INGREDIENTI
# ===========================================

@ingredients_bp.route('/')
@login_required
def index():
    """Lista degli ingredienti con ricerca e filtri"""
    try:
        # Parametri di ricerca
        search = request.args.get('search', '')
        categoria = request.args.get('categoria', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Query di base
        query = Ingrediente.query
        
        # Applicare filtri
        if search:
            query = query.filter(or_(
                Ingrediente.nome.contains(search),
                Ingrediente.descrizione.contains(search)
            ))
        
        if categoria:
            query = query.filter(Ingrediente.categoria == categoria)
        
        # Ordinamento
        sort_by = request.args.get('sort', 'nome')
        if sort_by == 'nome':
            query = query.order_by(Ingrediente.nome)
        elif sort_by == 'categoria':
            query = query.order_by(Ingrediente.categoria, Ingrediente.nome)
        elif sort_by == 'recent':
            query = query.order_by(desc(Ingrediente.created_at))
        
        # Paginazione
        ingredienti = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Liste per filtri
        categorie = db.session.query(Ingrediente.categoria)\
            .filter(Ingrediente.attivo == True, Ingrediente.categoria.isnot(None))\
            .distinct().order_by(Ingrediente.categoria).all()
        categorie = [c[0] for c in categorie if c[0]]
        
        return render_template('ingredients/index.html',
                             ingredienti=ingredienti,
                             categorie=categorie,
                             search=search,
                             categoria=categoria,
                             sort_by=sort_by)
    
    except Exception as e:
        flash(f'Errore nel caricamento degli ingredienti: {str(e)}', 'error')
        return redirect(url_for('ingredients.index'))

@ingredients_bp.route('/nuovo', methods=['GET', 'POST'])
@login_required
def new():
    """Crea nuovo ingrediente"""
    if request.method == 'POST':
        try:
            # Verifica duplicati
            nome = request.form.get('nome', '').strip()
            if Ingrediente.query.filter_by(nome=nome).first():
                flash(f'Ingrediente "{nome}" già esistente!', 'error')
                return render_template('ingredients/ingredienti/new.html')
            
            # Crea nuovo ingrediente
            ingrediente = Ingrediente(
                nome=nome,
                descrizione=request.form.get('descrizione', ''),
                unita_misura=request.form.get('unita_misura', 'kg'),
                categoria=request.form.get('categoria', ''),
                calorie=parse_decimal(request.form.get('calorie')),
                proteine=parse_decimal(request.form.get('proteine')),
                carboidrati=parse_decimal(request.form.get('carboidrati')),
                grassi=parse_decimal(request.form.get('grassi')),
                allergeni=request.form.get('allergeni', ''),
                conservazione=request.form.get('conservazione', ''),
                attivo=True
            )
            
            db.session.add(ingrediente)
            db.session.commit()
            
            flash(f'Ingrediente "{nome}" creato con successo!', 'success')
            return redirect(url_for('ingredients.view', id=ingrediente.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nella creazione dell\'ingrediente: {str(e)}', 'error')
    
    return render_template('ingredients/ingredienti/new.html')

@ingredients_bp.route('/<int:id>')
@login_required
def view(id):
    """Visualizza dettagli ingrediente"""
    try:
        ingrediente = Ingrediente.query.get_or_404(id)
        
        # Fornitori associati
        associazioni_fornitori = IngredienteFornitore.query.filter_by(
            ingrediente_id=id, attivo=True
        ).join(Fornitore).filter(Fornitore.attivo == True).all()
        
        # Articoli che utilizzano questo ingrediente
        articoli_ingredienti = ArticoloIngrediente.query.filter_by(
            ingrediente_id=id, attivo=True
        ).limit(10).all()
        
        return render_template('ingredients/ingredienti/view.html',
                             ingrediente=ingrediente,
                             associazioni_fornitori=associazioni_fornitori,
                             articoli_ingredienti=articoli_ingredienti)
    
    except Exception as e:
        flash(f'Errore nel caricamento dell\'ingrediente: {str(e)}', 'error')
        return redirect(url_for('ingredients.index'))

@ingredients_bp.route('/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Modifica ingrediente"""
    try:
        ingrediente = Ingrediente.query.get_or_404(id)
        
        if request.method == 'POST':
            # Verifica duplicati (escludendo questo ingrediente)
            nome = request.form.get('nome', '').strip()
            duplicato = Ingrediente.query.filter(
                Ingrediente.nome == nome,
                Ingrediente.id != id
            ).first()
            
            if duplicato:
                flash(f'Ingrediente "{nome}" già esistente!', 'error')
                return render_template('ingredients/ingredienti/edit.html', ingrediente=ingrediente)
            
            # Aggiorna ingrediente
            ingrediente.nome = nome
            ingrediente.descrizione = request.form.get('descrizione', '')
            ingrediente.unita_misura = request.form.get('unita_misura', 'kg')
            ingrediente.categoria = request.form.get('categoria', '')
            ingrediente.calorie = parse_decimal(request.form.get('calorie'))
            ingrediente.proteine = parse_decimal(request.form.get('proteine'))
            ingrediente.carboidrati = parse_decimal(request.form.get('carboidrati'))
            ingrediente.grassi = parse_decimal(request.form.get('grassi'))
            ingrediente.allergeni = request.form.get('allergeni', '')
            ingrediente.conservazione = request.form.get('conservazione', '')
            ingrediente.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Ingrediente "{nome}" aggiornato con successo!', 'success')
            return redirect(url_for('ingredients.view', id=id))
        
        return render_template('ingredients/ingredienti/edit.html', ingrediente=ingrediente)
    
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nella modifica dell\'ingrediente: {str(e)}', 'error')
        return redirect(url_for('ingredients.index'))

@ingredients_bp.route('/<int:id>/elimina', methods=['POST'])
@login_required
@admin_required
def delete(id):
    """Elimina ingrediente (hard delete con cascade)"""
    try:
        ingrediente = Ingrediente.query.get_or_404(id)
        nome_ingrediente = ingrediente.nome
        
        # Conta le associazioni che verranno eliminate
        articoli_count = ArticoloIngrediente.query.filter_by(ingrediente_id=id).count()
        fornitori_count = IngredienteFornitore.query.filter_by(ingrediente_id=id).count()
        
        # HARD DELETE: Le associazioni vengono eliminate automaticamente grazie alle cascade
        # definite nel modello (cascade='all, delete-orphan')
        db.session.delete(ingrediente)
        db.session.commit()
        
        # Messaggio di conferma con dettagli delle eliminazioni
        message = f'Ingrediente "{nome_ingrediente}" eliminato con successo!'
        if articoli_count > 0:
            message += f' Rimosse {articoli_count} associazioni con articoli.'
        if fornitori_count > 0:
            message += f' Rimosse {fornitori_count} associazioni con fornitori.'
        
        flash(message, 'success')
        return redirect(url_for('ingredients.index'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nell\'eliminazione dell\'ingrediente: {str(e)}', 'error')
        return redirect(url_for('ingredients.view', id=id))

# ===========================================
# GESTIONE FORNITORI - CRUD
# ===========================================

@ingredients_bp.route('/fornitori')
@login_required  
def fornitori_list():
    """Lista dei fornitori con ricerca"""
    try:
        # Parametri di ricerca
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Query di base
        query = Fornitore.query
        
        # Applicare filtri
        if search:
            query = query.filter(or_(
                Fornitore.nome.contains(search),
                Fornitore.email.contains(search),
                Fornitore.telefono.contains(search),
                Fornitore.citta.contains(search)
            ))
        
        # Ordinamento
        sort_by = request.args.get('sort', 'nome')
        if sort_by == 'nome':
            query = query.order_by(Fornitore.nome)
        elif sort_by == 'citta':
            query = query.order_by(Fornitore.citta, Fornitore.nome)
        elif sort_by == 'recent':
            query = query.order_by(desc(Fornitore.created_at))
        
        # Paginazione
        fornitori = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('ingredients/fornitori/index.html',
                             fornitori=fornitori,
                             search=search,
                             sort_by=sort_by)
    
    except Exception as e:
        flash(f'Errore nel caricamento dei fornitori: {str(e)}', 'error')
        return redirect(url_for('ingredients.index'))

@ingredients_bp.route('/fornitori/nuovo', methods=['GET', 'POST'])
@login_required
def fornitori_new():
    """Crea nuovo fornitore"""
    if request.method == 'POST':
        try:
            # Verifica duplicati
            nome = request.form.get('nome', '').strip()
            if Fornitore.query.filter_by(nome=nome).first():
                flash(f'Fornitore "{nome}" già esistente!', 'error')
                return render_template('ingredients/fornitori/new.html')
            
            # Crea nuovo fornitore
            fornitore = Fornitore(
                nome=nome,
                email=request.form.get('email', ''),
                telefono=request.form.get('telefono', ''),
                indirizzo=request.form.get('indirizzo', ''),
                citta=request.form.get('citta', ''),
                provincia=request.form.get('provincia', ''),
                cap=request.form.get('cap', ''),
                paese=request.form.get('paese', 'Italia'),
                partita_iva=request.form.get('partita_iva', ''),
                codice_fiscale=request.form.get('codice_fiscale', ''),
                iban=request.form.get('iban', ''),
                note=request.form.get('note', ''),
                attivo=True
            )
            
            db.session.add(fornitore)
            db.session.commit()
            
            flash(f'Fornitore "{nome}" creato con successo!', 'success')
            return redirect(url_for('ingredients.fornitori_view', id=fornitore.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nella creazione del fornitore: {str(e)}', 'error')
    
    return render_template('ingredients/fornitori/new.html')

@ingredients_bp.route('/fornitori/<int:id>')
@login_required
def fornitori_view(id):
    """Visualizza dettagli fornitore"""
    try:
        fornitore = Fornitore.query.get_or_404(id)
        
        # Ingredienti forniti
        associazioni_ingredienti = IngredienteFornitore.query.filter_by(
            fornitore_id=id, attivo=True
        ).join(Ingrediente).filter(Ingrediente.attivo == True).all()
        
        return render_template('ingredients/fornitori/view.html',
                             fornitore=fornitore,
                             associazioni_ingredienti=associazioni_ingredienti)
    
    except Exception as e:
        flash(f'Errore nel caricamento del fornitore: {str(e)}', 'error')
        return redirect(url_for('ingredients.fornitori_list'))

@ingredients_bp.route('/fornitori/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
def fornitori_edit(id):
    """Modifica fornitore"""
    try:
        fornitore = Fornitore.query.get_or_404(id)
        
        if request.method == 'POST':
            # Verifica duplicati (escludendo questo fornitore)
            nome = request.form.get('nome', '').strip()
            duplicato = Fornitore.query.filter(
                Fornitore.nome == nome,
                Fornitore.attivo == True,
                Fornitore.id != id
            ).first()
            
            if duplicato:
                flash(f'Fornitore "{nome}" già esistente!', 'error')
                return render_template('ingredients/fornitori/edit.html', fornitore=fornitore)
            
            # Aggiorna fornitore
            fornitore.nome = nome
            fornitore.email = request.form.get('email', '')
            fornitore.telefono = request.form.get('telefono', '')
            fornitore.indirizzo = request.form.get('indirizzo', '')
            fornitore.citta = request.form.get('citta', '')
            fornitore.provincia = request.form.get('provincia', '')
            fornitore.cap = request.form.get('cap', '')
            fornitore.paese = request.form.get('paese', 'Italia')
            fornitore.partita_iva = request.form.get('partita_iva', '')
            fornitore.codice_fiscale = request.form.get('codice_fiscale', '')
            fornitore.iban = request.form.get('iban', '')
            fornitore.note = request.form.get('note', '')
            fornitore.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Fornitore "{nome}" aggiornato con successo!', 'success')
            return redirect(url_for('ingredients.fornitori_view', id=id))
        
        return render_template('ingredients/fornitori/edit.html', fornitore=fornitore)
    
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nella modifica del fornitore: {str(e)}', 'error')
        return redirect(url_for('ingredients.fornitori_list'))

@ingredients_bp.route('/fornitori/<int:id>/elimina', methods=['POST'])
@login_required
@admin_required
def fornitori_delete(id):
    """Elimina fornitore (hard delete con cascade)"""
    try:
        fornitore = Fornitore.query.get_or_404(id)
        nome_fornitore = fornitore.nome
        
        # Conta le associazioni che verranno eliminate
        ingredienti_count = IngredienteFornitore.query.filter_by(fornitore_id=id).count()
        
        # Verifica se è fornitore preferito per alcuni ingredienti e aggiorna
        ingredienti_con_preferito = Ingrediente.query.filter_by(fornitore_preferito_id=id).all()
        for ingrediente in ingredienti_con_preferito:
            ingrediente.fornitore_preferito_id = None
        
        # Verifica se è fornitore preferito per alcune associazioni articolo-ingrediente
        associazioni_con_preferito = ArticoloIngrediente.query.filter_by(fornitore_preferito_id=id).all()
        for associazione in associazioni_con_preferito:
            associazione.fornitore_preferito_id = None
        
        # HARD DELETE: Le associazioni IngredienteFornitore vengono eliminate automaticamente 
        # grazie alle foreign keys con CASCADE
        db.session.delete(fornitore)
        db.session.commit()
        
        # Messaggio di conferma con dettagli delle eliminazioni
        message = f'Fornitore "{nome_fornitore}" eliminato con successo!'
        if ingredienti_count > 0:
            message += f' Rimosse {ingredienti_count} associazioni con ingredienti.'
        if ingredienti_con_preferito:
            message += f' Aggiornati {len(ingredienti_con_preferito)} ingredienti che lo avevano come preferito.'
        
        flash(message, 'success')
        return redirect(url_for('ingredients.fornitori_list'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nell\'eliminazione del fornitore: {str(e)}', 'error')
        return redirect(url_for('ingredients.fornitori_view', id=id))

# ===========================================
# GESTIONE ASSOCIAZIONI INGREDIENTI-FORNITORI
# ===========================================

@ingredients_bp.route('/<int:ingrediente_id>/aggiungi-fornitore', methods=['GET', 'POST'])
@login_required
def add_fornitore(ingrediente_id):
    """Associa un fornitore a un ingrediente"""
    try:
        ingrediente = Ingrediente.query.get_or_404(ingrediente_id)
        
        if request.method == 'POST':
            fornitore_id = request.form.get('fornitore_id', type=int)
            prezzo_unitario = parse_decimal(request.form.get('prezzo_unitario'))
            
            if not fornitore_id or not prezzo_unitario:
                flash('Fornitore e prezzo sono obbligatori!', 'error')
                return render_template('ingredients/ingredienti/add_fornitore.html', 
                                     ingrediente=ingrediente,
                                     fornitori=Fornitore.query.filter_by(attivo=True).all())
            
            # LOGICA N:N - Controlla se l'associazione con questo fornitore esiste già
            esistente = IngredienteFornitore.query.filter_by(
                ingrediente_id=ingrediente_id,
                fornitore_id=fornitore_id
            ).first()
            
            if esistente:
                # Aggiorna l'associazione esistente (riattivandola se era disattivata)
                esistente.attivo = True
                esistente.prezzo_unitario = prezzo_unitario
                esistente.codice_fornitore = request.form.get('codice_fornitore', '')
                esistente.tempo_consegna_giorni = request.form.get('tempo_consegna_giorni', 0, type=int)
                esistente.quantita_minima = parse_decimal(request.form.get('quantita_minima', '0')) or 0
                esistente.note = request.form.get('note', '')
                esistente.updated_at = datetime.utcnow()
                
                db.session.commit()
                flash('Fornitore aggiornato con successo!', 'success')
                return redirect(url_for('ingredients.view', id=ingrediente_id))
            
            else:
                # Crea nuova associazione
                associazione = IngredienteFornitore(
                    ingrediente_id=ingrediente_id,
                    fornitore_id=fornitore_id,
                    prezzo_unitario=prezzo_unitario,
                    codice_fornitore=request.form.get('codice_fornitore', ''),
                    tempo_consegna_giorni=request.form.get('tempo_consegna_giorni', 0, type=int),
                    quantita_minima=parse_decimal(request.form.get('quantita_minima', '0')) or 0,
                    note=request.form.get('note', ''),
                    attivo=True
                )
                
                db.session.add(associazione)
                db.session.commit()
            
            flash('Fornitore associato con successo!', 'success')
            return redirect(url_for('ingredients.view', id=ingrediente_id))
        
        # Mostra solo i fornitori che non sono già associati a questo ingrediente
        fornitori_gia_associati = db.session.query(IngredienteFornitore.fornitore_id).filter_by(
            ingrediente_id=ingrediente_id, 
            attivo=True
        ).subquery()
        
        fornitori_disponibili = Fornitore.query.filter(
            Fornitore.attivo == True,
            ~Fornitore.id.in_(fornitori_gia_associati)
        ).order_by(Fornitore.nome).all()
        
        return render_template('ingredients/ingredienti/add_fornitore.html',
                             ingrediente=ingrediente,
                             fornitori=fornitori_disponibili)
    
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nell\'associazione del fornitore: {str(e)}', 'error')
        return redirect(url_for('ingredients.view', id=ingrediente_id))

@ingredients_bp.route('/<int:ingrediente_id>/imposta-fornitore-preferito/<int:fornitore_id>', methods=['POST'])
@login_required
def set_fornitore_preferito(ingrediente_id, fornitore_id):
    """Imposta il fornitore preferito per un ingrediente"""
    try:
        ingrediente = Ingrediente.query.get_or_404(ingrediente_id)
        
        # Verifica che l'associazione esista e sia attiva
        associazione = IngredienteFornitore.query.filter_by(
            ingrediente_id=ingrediente_id,
            fornitore_id=fornitore_id,
            attivo=True
        ).first()
        
        if not associazione:
            flash('Il fornitore non è associato a questo ingrediente!', 'error')
            return redirect(url_for('ingredients.view', id=ingrediente_id))
        
        # Imposta il fornitore preferito
        ingrediente.fornitore_preferito_id = fornitore_id
        ingrediente.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Fornitore {associazione.fornitore.nome} impostato come preferito!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nell\'impostazione del fornitore preferito: {str(e)}', 'error')
    
    return redirect(url_for('ingredients.view', id=ingrediente_id))

@ingredients_bp.route('/associazioni/<int:associazione_id>/modifica', methods=['GET', 'POST'])
@login_required
def associazione_edit(associazione_id):
    """Modifica associazione ingrediente-fornitore"""
    try:
        associazione = IngredienteFornitore.query.get_or_404(associazione_id)
        
        if request.method == 'POST':
            prezzo_unitario = parse_decimal(request.form.get('prezzo_unitario'))
            
            if not prezzo_unitario:
                flash('Il prezzo è obbligatorio!', 'error')
                return render_template('ingredients/associazioni/edit.html', associazione=associazione)
            
            # Aggiorna associazione
            associazione.prezzo_unitario = prezzo_unitario
            associazione.codice_fornitore = request.form.get('codice_fornitore', '')
            associazione.tempo_consegna_giorni = request.form.get('tempo_consegna_giorni', 0, type=int)
            associazione.quantita_minima = parse_decimal(request.form.get('quantita_minima', '0')) or 0
            associazione.note = request.form.get('note', '')
            associazione.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Associazione aggiornata con successo!', 'success')
            return redirect(url_for('ingredients.view', id=associazione.ingrediente_id))
        
        return render_template('ingredients/associazioni/edit.html', associazione=associazione)
    
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nella modifica dell\'associazione: {str(e)}', 'error')
        return redirect(url_for('ingredients.index'))

@ingredients_bp.route('/associazioni/<int:associazione_id>/elimina', methods=['POST'])
@login_required
def associazione_delete(associazione_id):
    """Elimina associazione ingrediente-fornitore"""
    try:
        associazione = IngredienteFornitore.query.get_or_404(associazione_id)
        ingrediente_id = associazione.ingrediente_id
        
        # Soft delete
        associazione.attivo = False
        associazione.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Associazione eliminata con successo!', 'success')
        return redirect(url_for('ingredients.view', id=ingrediente_id))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nell\'eliminazione dell\'associazione: {str(e)}', 'error')
        return redirect(url_for('ingredients.index'))

# ===========================================
# FOOD COST E ASSOCIAZIONI ARTICOLI
# ===========================================

@ingredients_bp.route('/food-cost')
@login_required
def food_cost():
    """Vista food cost articoli"""
    try:
        # Parametri di ricerca
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Query vista food cost
        query = ViewFoodCost.query.filter(ViewFoodCost.attivo == True)
        
        if search:
            query = query.filter(ViewFoodCost.nome_articolo.contains(search))
        
        # Ordinamento
        sort_by = request.args.get('sort', 'percentuale')
        if sort_by == 'nome':
            query = query.order_by(ViewFoodCost.nome_articolo)
        elif sort_by == 'percentuale':
            query = query.order_by(desc(ViewFoodCost.percentuale_food_cost))
        elif sort_by == 'costo':
            query = query.order_by(desc(ViewFoodCost.costo_ingredienti))
        
        # Paginazione
        articoli = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Statistiche
        stats = db.session.query(
            func.avg(ViewFoodCost.percentuale_food_cost).label('media'),
            func.min(ViewFoodCost.percentuale_food_cost).label('minima'),
            func.max(ViewFoodCost.percentuale_food_cost).label('massima'),
            func.count().label('totale')
        ).filter(
            ViewFoodCost.attivo == True,
            ViewFoodCost.percentuale_food_cost.isnot(None)
        ).first()
        
        return render_template('ingredients/food_cost.html',
                             articoli=articoli,
                             stats=stats,
                             search=search,
                             sort_by=sort_by)
    
    except Exception as e:
        flash(f'Errore nel caricamento del food cost: {str(e)}', 'error')
        return redirect(url_for('ingredients.index'))

@ingredients_bp.route('/articoli/<int:articolo_id>/ingredienti')
@login_required
def articoli_ingredienti(articolo_id):
    """Gestione ingredienti di un articolo"""
    try:
        # Verifica che l'articolo esista
        articolo = Article.query.get_or_404(articolo_id)
        
        # Ingredienti associati
        ingredienti_articolo = ArticoloIngrediente.query.filter_by(
            articolo_id=articolo_id, attivo=True
        ).all()
        
        # Calcolo food cost totale
        costo_totale = sum(ai.costo_totale for ai in ingredienti_articolo)
        percentuale_food_cost = 0
        if articolo.PrecioConIVA and costo_totale > 0:
            percentuale_food_cost = (costo_totale / float(articolo.PrecioConIVA)) * 100
        
        return render_template('ingredients/articoli/ingredienti.html',
                             articolo=articolo,
                             ingredienti_articolo=ingredienti_articolo,
                             costo_totale=costo_totale,
                             percentuale_food_cost=percentuale_food_cost)
    
    except Exception as e:
        flash(f'Errore nel caricamento degli ingredienti dell\'articolo: {str(e)}', 'error')
        return redirect(url_for('ingredients.food_cost'))

# ===========================================
# API ENDPOINTS
# ===========================================

@ingredients_bp.route('/api/ingredienti/search')
@login_required
def api_ingredienti_search():
    """API per ricerca ingredienti (autocomplete)"""
    try:
        q = request.args.get('q', '')
        if len(q) < 2:
            return jsonify([])
        
        ingredienti = Ingrediente.query.filter(
            Ingrediente.attivo == True,
            Ingrediente.nome.contains(q)
        ).limit(10).all()
        
        return jsonify([{
            'id': i.id,
            'nome': i.nome,
            'unita_misura': i.unita_misura,
            'categoria': i.categoria
        } for i in ingredienti])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ingredients_bp.route('/api/fornitori/search')
@login_required
def api_fornitori_search():
    """API per ricerca fornitori (autocomplete)"""
    try:
        q = request.args.get('q', '')
        if len(q) < 2:
            return jsonify([])
        
        fornitori = Fornitore.query.filter(
            Fornitore.attivo == True,
            Fornitore.nome.contains(q)
        ).limit(10).all()
        
        return jsonify([{
            'id': f.id,
            'nome': f.nome,
            'citta': f.citta,
            'telefono': f.telefono
        } for f in fornitori])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ingredients_bp.route('/api/ingredienti/<int:ingrediente_id>/fornitori')
@login_required
def api_ingrediente_fornitori(ingrediente_id):
    """API per ottenere i fornitori di un ingrediente"""
    try:
        associazioni = IngredienteFornitore.query.filter_by(
            ingrediente_id=ingrediente_id, attivo=True
        ).join(Fornitore).filter(Fornitore.attivo == True).all()
        
        return jsonify([{
            'id': a.id,
            'fornitore_id': a.fornitore_id,
            'nome_fornitore': a.fornitore.nome,
            'prezzo_unitario': float(a.prezzo_unitario),
            'prezzo_formatted': a.prezzo_formatted,
            'tempo_consegna': a.tempo_consegna_text,
            'quantita_minima': float(a.quantita_minima) if a.quantita_minima else 0
        } for a in associazioni])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ingredients_bp.route('/api/available-ingredients')
@login_required
def api_available_ingredients():
    """API per ottenere tutti gli ingredienti disponibili"""
    try:
        ingredienti = Ingrediente.query.order_by(Ingrediente.nome).all()
        
        return jsonify({
            'success': True,
            'ingredients': [{
                'id': i.id,
                'name': i.nome,
                'category': i.categoria or 'Generale',
                'unit': i.unita_misura,
                'description': i.descrizione
            } for i in ingredienti]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ingredients_bp.route('/api/suppliers-for-ingredient/<int:ingrediente_id>')
@login_required
def api_suppliers_for_ingredient(ingrediente_id):
    """API per ottenere i fornitori per un ingrediente specifico"""
    try:
        ingrediente = Ingrediente.query.get_or_404(ingrediente_id)
        associazioni = IngredienteFornitore.query.filter_by(
            ingrediente_id=ingrediente_id, attivo=True
        ).join(Fornitore).filter(Fornitore.attivo == True).all()
        
        return jsonify({
            'success': True,
            'suppliers': [{
                'id': a.id,
                'name': a.fornitore.nome,
                'price': float(a.prezzo_unitario),
                'unit': ingrediente.unita_misura,
                'tempo_consegna': a.tempo_consegna_giorni,
                'quantita_minima': float(a.quantita_minima) if a.quantita_minima else 0
            } for a in associazioni]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ingredients_bp.route('/api/add-ingredient-to-article', methods=['POST'])
@login_required
def api_add_ingredient_to_article():
    """API per aggiungere un ingrediente a un articolo"""
    try:
        data = request.get_json()
        
        # Validazione dati
        required_fields = ['IdArticolo', 'IdIngrediente', 'Quantita']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Campo {field} obbligatorio'}), 400
        
        # Verifica che l'articolo esista
        articolo = Article.query.get(data['IdArticolo'])
        if not articolo:
            return jsonify({'success': False, 'error': 'Articolo non trovato'}), 404
        
        # Verifica che l'ingrediente esista
        ingrediente = Ingrediente.query.get(data['IdIngrediente'])
        if not ingrediente:
            return jsonify({'success': False, 'error': 'Ingrediente non trovato'}), 404
        
        # Verifica se l'associazione attiva esiste già
        esistente_attiva = ArticoloIngrediente.query.filter_by(
            articolo_id=data['IdArticolo'],
            ingrediente_id=data['IdIngrediente'],
            attivo=True
        ).first()
        
        if esistente_attiva:
            return jsonify({'success': False, 'error': 'Ingrediente già associato a questo articolo'}), 400
        
        # Verifica se esiste un'associazione disattivata da riattivare
        esistente_disattivata = ArticoloIngrediente.query.filter_by(
            articolo_id=data['IdArticolo'],
            ingrediente_id=data['IdIngrediente'],
            attivo=False
        ).first()
        
        if esistente_disattivata:
            # Riattiva l'associazione esistente aggiornando i dati
            esistente_disattivata.attivo = True
            esistente_disattivata.quantita = parse_decimal(str(data['Quantita']))
            esistente_disattivata.fornitore_preferito_id = data.get('IdFornitoreIngrediente')
            esistente_disattivata.note = data.get('Note', '')
            esistente_disattivata.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Ingrediente riassociato con successo',
                'id': esistente_disattivata.id
            })
        
        # Se non esiste nessuna associazione, crea una nuova
        associazione = ArticoloIngrediente(
            articolo_id=data['IdArticolo'],
            ingrediente_id=data['IdIngrediente'],
            quantita=parse_decimal(str(data['Quantita'])),
            fornitore_preferito_id=data.get('IdFornitoreIngrediente'),
            note=data.get('Note', ''),
            attivo=True
        )
        
        db.session.add(associazione)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ingrediente aggiunto con successo',
            'id': associazione.id
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@ingredients_bp.route('/api/remove-ingredient-from-article/<int:associazione_id>', methods=['DELETE'])
@login_required
def api_remove_ingredient_from_article(associazione_id):
    """API per rimuovere un ingrediente da un articolo"""
    try:
        associazione = ArticoloIngrediente.query.get_or_404(associazione_id)
        
        # Soft delete
        associazione.attivo = False
        associazione.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ingrediente rimosso con successo'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@ingredients_bp.route('/api/update-article-ingredient/<int:associazione_id>', methods=['PUT'])
@login_required
def api_update_article_ingredient(associazione_id):
    """API per aggiornare un ingrediente di un articolo"""
    try:
        associazione = ArticoloIngrediente.query.get_or_404(associazione_id)
        data = request.get_json()
        
        # Aggiorna i campi consentiti
        if 'Quantita' in data:
            associazione.quantita = parse_decimal(str(data['Quantita']))
        
        if 'IdFornitoreIngrediente' in data:
            associazione.fornitore_preferito_id = data['IdFornitoreIngrediente'] if data['IdFornitoreIngrediente'] else None
        
        if 'Note' in data:
            associazione.note = data.get('Note', '')
        
        associazione.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ingrediente aggiornato con successo'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@ingredients_bp.route('/api/update-article-price/<int:article_id>', methods=['PUT'])
@login_required
@admin_required
def api_update_article_price(article_id):
    """API per aggiornare il prezzo di un articolo"""
    try:
        article = Article.query.get_or_404(article_id)
        data = request.get_json()
        
        if not data or 'prezzo_con_iva' not in data:
            return jsonify({
                'success': False, 
                'error': 'Prezzo con IVA non fornito'
            }), 400
            
        prezzo_con_iva = parse_decimal(str(data['prezzo_con_iva']))
        if not prezzo_con_iva or prezzo_con_iva <= 0:
            return jsonify({
                'success': False, 
                'error': 'Prezzo non valido'
            }), 400
        
        # Calcola il prezzo senza IVA basato sulla percentuale IVA dell'articolo
        iva_percentage = 22  # Default 22%
        if hasattr(article, 'IdIva') and article.IdIva:
            if article.IdIva == 1:
                iva_percentage = 4
            elif article.IdIva == 2:
                iva_percentage = 10
            elif article.IdIva == 3:
                iva_percentage = 22
        
        # Calcola prezzo senza IVA: prezzo_con_iva / (1 + iva_rate)
        # Converti tutto in Decimal per evitare errori di tipo
        from decimal import Decimal
        iva_rate = Decimal(str(iva_percentage)) / Decimal('100')
        prezzo_sin_iva = prezzo_con_iva / (Decimal('1') + iva_rate)
        prezzo_sin_iva = prezzo_sin_iva.quantize(Decimal('0.01'))
        
        # Aggiorna i prezzi
        old_prezzo_con_iva = article.PrecioConIVA
        old_prezzo_sin_iva = article.PrecioSinIVA
        
        article.PrecioConIVA = prezzo_con_iva
        article.PrecioSinIVA = prezzo_sin_iva
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Prezzo aggiornato con successo',
            'data': {
                'old_prezzo_con_iva': float(old_prezzo_con_iva) if old_prezzo_con_iva else 0,
                'new_prezzo_con_iva': float(prezzo_con_iva),
                'old_prezzo_sin_iva': float(old_prezzo_sin_iva) if old_prezzo_sin_iva else 0,
                'new_prezzo_sin_iva': float(prezzo_sin_iva),
                'iva_percentage': iva_percentage
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'error': f'Errore durante l\'aggiornamento: {str(e)}'
        }), 500

# ===========================================
# GESTIONE FATTURE PDF
# ===========================================

logger = logging.getLogger(__name__)

def allowed_file(filename):
    """Controlla se il file è un PDF"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

@ingredients_bp.route('/fatture')
@login_required
def fatture_list():
    """Lista delle fatture caricate"""
    try:
        fatture_dir = os.path.join(current_app.root_path, '..', 'UPLOADS', 'fatture')
        fatture = []
        
        if os.path.exists(fatture_dir):
            for filename in os.listdir(fatture_dir):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(fatture_dir, filename)
                    stat = os.stat(file_path)
                    
                    fatture.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime),
                        'modified': datetime.fromtimestamp(stat.st_mtime)
                    })
        
        # Ordina per data di modifica decrescente
        fatture.sort(key=lambda x: x['modified'], reverse=True)
        
        return render_template('ingredients/fatture/index.html', fatture=fatture)
    
    except Exception as e:
        flash(f'Errore nel caricamento delle fatture: {str(e)}', 'error')
        return redirect(url_for('ingredients.index'))

@ingredients_bp.route('/fatture/upload', methods=['GET', 'POST'])
@login_required
def fatture_upload():
    """Upload di nuove fatture PDF"""
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                flash('Nessun file selezionato', 'error')
                return render_template('ingredients/fatture/upload.html')
            
            file = request.files['file']
            
            if file.filename == '':
                flash('Nessun file selezionato', 'error')
                return render_template('ingredients/fatture/upload.html')
            
            if not allowed_file(file.filename):
                flash('Solo file PDF sono consentiti', 'error')
                return render_template('ingredients/fatture/upload.html')
            
            # Salva il file
            filename = secure_filename(file.filename)
            
            # Aggiungi timestamp se il file esiste già
            fatture_dir = os.path.join(current_app.root_path, '..', 'UPLOADS', 'fatture')
            os.makedirs(fatture_dir, exist_ok=True)
            
            file_path = os.path.join(fatture_dir, filename)
            if os.path.exists(file_path):
                base, ext = os.path.splitext(filename)
                filename = f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                file_path = os.path.join(fatture_dir, filename)
            
            file.save(file_path)
            
            # Processa automaticamente se richiesto
            auto_process = request.form.get('auto_process') == 'true'
            
            if auto_process:
                processor = PDFInvoiceProcessor()
                result = processor.process_invoice_pdf(file_path)
                
                if result['success']:
                    flash(f'Fattura caricata e processata con successo! '
                          f'Fornitore: {result["supplier"]["nome"]}, '
                          f'Articoli processati: {result["items_processed"]}', 'success')
                else:
                    flash(f'Fattura caricata ma errori durante l\'elaborazione: {", ".join(result["errors"])}', 'warning')
            else:
                flash(f'Fattura "{filename}" caricata con successo!', 'success')
            
            return redirect(url_for('ingredients.fatture_list'))
        
        except Exception as e:
            flash(f'Errore durante l\'upload: {str(e)}', 'error')
            logger.error(f"Errore upload fattura: {str(e)}")
    
    return render_template('ingredients/fatture/upload.html')

@ingredients_bp.route('/fatture/process/<filename>')
@login_required
def fatture_process(filename):
    """Processa una fattura specifica"""
    try:
        fatture_dir = os.path.join(current_app.root_path, '..', 'UPLOADS', 'fatture')
        file_path = os.path.join(fatture_dir, secure_filename(filename))
        
        if not os.path.exists(file_path):
            flash('File fattura non trovato', 'error')
            return redirect(url_for('ingredients.fatture_list'))
        
        processor = PDFInvoiceProcessor()
        result = processor.process_invoice_pdf(file_path)
        
        if result['success']:
            matching = result['matching_results']
            flash(f'Fattura processata con successo! '
                  f'Fornitore: {result["supplier"]["nome"]}, '
                  f'Ingredienti trovati: {matching["matched"]}, '
                  f'Ingredienti creati: {matching["created"]}, '
                  f'Associazioni aggiornate: {matching["updated"]}', 'success')
        else:
            flash(f'Errori durante l\'elaborazione: {", ".join(result["errors"])}', 'error')
        
        return redirect(url_for('ingredients.fatture_detail', filename=filename))
    
    except Exception as e:
        flash(f'Errore durante l\'elaborazione: {str(e)}', 'error')
        logger.error(f"Errore elaborazione fattura {filename}: {str(e)}")
        return redirect(url_for('ingredients.fatture_list'))

@ingredients_bp.route('/fatture/detail/<filename>')
@login_required
def fatture_detail(filename):
    """Mostra dettagli di una fattura e anteprima dei dati estratti"""
    try:
        fatture_dir = os.path.join(current_app.root_path, '..', 'UPLOADS', 'fatture')
        file_path = os.path.join(fatture_dir, secure_filename(filename))
        
        if not os.path.exists(file_path):
            flash('File fattura non trovato', 'error')
            return redirect(url_for('ingredients.fatture_list'))
        
        # Info file
        stat = os.stat(file_path)
        file_info = {
            'filename': filename,
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime)
        }
        
        # Estrai dati per anteprima (senza salvare)
        processor = PDFInvoiceProcessor()
        
        # Estrai testo e informazioni fornitore
        text = processor.extract_text_from_pdf(file_path)
        supplier_info = processor.extract_supplier_info(text) if text else {}
        
        # Estrai tabelle e articoli
        tables = processor.extract_tables_from_pdf(file_path)
        items = processor.extract_items_from_tables(tables) if tables else []
        
        # Filtra solo gli ingredienti alimentari per l'anteprima
        food_items = [item for item in items if item.get('is_food_ingredient', False)]
        
        return render_template('ingredients/fatture/detail.html',
                             file_info=file_info,
                             supplier_info=supplier_info,
                             items=food_items,
                             total_items=len(items))
    
    except Exception as e:
        flash(f'Errore nel caricamento dei dettagli: {str(e)}', 'error')
        logger.error(f"Errore dettagli fattura {filename}: {str(e)}")
        return redirect(url_for('ingredients.fatture_list'))

@ingredients_bp.route('/fatture/delete/<filename>', methods=['POST'])
@login_required
@admin_required
def fatture_delete(filename):
    """Elimina una fattura"""
    try:
        fatture_dir = os.path.join(current_app.root_path, '..', 'UPLOADS', 'fatture')
        file_path = os.path.join(fatture_dir, secure_filename(filename))
        
        if os.path.exists(file_path):
            os.remove(file_path)
            flash(f'Fattura "{filename}" eliminata con successo!', 'success')
        else:
            flash('File fattura non trovato', 'error')
        
    except Exception as e:
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'error')
        logger.error(f"Errore eliminazione fattura {filename}: {str(e)}")
    
    return redirect(url_for('ingredients.fatture_list'))

# ===========================================
# API ENDPOINTS PER FATTURE
# ===========================================

@ingredients_bp.route('/api/fatture/process', methods=['POST'])
@login_required
def api_fatture_process():
    """API per processare una fattura via AJAX"""
    try:
        # Debug: log della richiesta
        logger.info(f"API fatture/process chiamata - Content-Type: {request.content_type}")
        
        # Gestisci sia JSON che form data
        if request.is_json:
            data = request.get_json()
        else:
            # Fallback per form data
            data = request.form.to_dict()
        
        logger.info(f"Dati ricevuti: {data}")
        
        filename = data.get('filename')
        
        if not filename:
            logger.error("Nome file non fornito nella richiesta")
            return jsonify({'success': False, 'error': 'Nome file non fornito'}), 400
        
        # Costruisci il percorso del file
        fatture_dir = os.path.join(current_app.root_path, '..', 'UPLOADS', 'fatture')
        file_path = os.path.join(fatture_dir, secure_filename(filename))
        
        logger.info(f"Percorso file: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File non trovato: {file_path}")
            return jsonify({'success': False, 'error': 'File non trovato'}), 404
        
        # Inizializza il processore
        try:
            processor = PDFInvoiceProcessor()
            logger.info("PDFInvoiceProcessor inizializzato correttamente")
        except Exception as proc_error:
            logger.error(f"Errore nell'inizializzazione del processore: {str(proc_error)}")
            return jsonify({'success': False, 'error': f'Errore processore: {str(proc_error)}'}), 500
        
        # Elabora la fattura
        logger.info(f"Inizio elaborazione fattura: {filename}")
        result = processor.process_invoice_pdf(file_path)
        
        logger.info(f"Risultato elaborazione: success={result.get('success', False)}")
        if not result.get('success', False):
            logger.error(f"Errori nell'elaborazione: {result.get('errors', [])}")
        
        return jsonify(result)
    
    except Exception as e:
        error_msg = f"Errore API elaborazione fattura: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({'success': False, 'error': error_msg}), 500

@ingredients_bp.route('/api/fatture/preview', methods=['POST'])
@login_required
def api_fatture_preview():
    """API per ottenere anteprima dei dati di una fattura"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'success': False, 'error': 'Nome file non fornito'}), 400
        
        fatture_dir = os.path.join(current_app.root_path, '..', 'UPLOADS', 'fatture')
        file_path = os.path.join(fatture_dir, secure_filename(filename))
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File non trovato'}), 404
        
        processor = PDFInvoiceProcessor()
        
        # Estrai dati senza salvare
        text = processor.extract_text_from_pdf(file_path)
        supplier_info = processor.extract_supplier_info(text) if text else {}
        
        tables = processor.extract_tables_from_pdf(file_path)
        items = processor.extract_items_from_tables(tables) if tables else []
        
        # Filtra ingredienti alimentari
        food_items = [item for item in items if item.get('is_food_ingredient', False)]
        
        return jsonify({
            'success': True,
            'supplier_info': supplier_info,
            'items': food_items,
            'total_items': len(items),
            'food_items_count': len(food_items)
        })
    
    except Exception as e:
        logger.error(f"Errore API anteprima fattura: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500