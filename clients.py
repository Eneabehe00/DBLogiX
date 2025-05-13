from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Client
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import csv
import os
from werkzeug.utils import secure_filename

clients_bp = Blueprint('clients', __name__, template_folder='templates')

@clients_bp.route('/')
@login_required
def index():
    """Display list of all clients"""
    clients = Client.query.all()
    return render_template('clients/index.html', clients=clients)

@clients_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Create a new client"""
    if request.method == 'POST':
        try:
            # Get next available IdCliente
            max_id = db.session.query(db.func.max(Client.IdCliente)).scalar() or 0
            new_id = max_id + 1
            
            # Create a new client
            client = Client(
                IdCliente=new_id,
                IdEmpresa=1,  # Default company ID
                Nombre=request.form.get('Nombre', ''),
                Direccion=request.form.get('Direccion', ''),
                CodPostal=request.form.get('CodPostal', ''),
                Poblacion=request.form.get('Poblacion', ''),
                Provincia=request.form.get('Provincia', ''),
                Pais=request.form.get('Pais', 'IT'),  # Default to Italy
                DNI=request.form.get('DNI', ''),
                Telefono1=request.form.get('Telefono1', ''),
                Telefono2=request.form.get('Telefono2', ''),
                Telefono3=request.form.get('Telefono3', ''),
                Email=request.form.get('Email', ''),
                TipoEmailTicket=int(request.form.get('TipoEmailTicket', 0)),
                TipoEmailAlbaran=int(request.form.get('TipoEmailAlbaran', 0)),
                TipoEmailFactura=int(request.form.get('TipoEmailFactura', 0)),
                Foto='',  # Default empty
                IdTarifa=request.form.get('IdTarifa'),
                Ofertas=int(request.form.get('Ofertas', 0)),
                IdFormaPago=request.form.get('IdFormaPago'),
                IdEstado=request.form.get('IdEstado'),
                Observaciones=request.form.get('Observaciones', ''),
                CodInterno=request.form.get('CodInterno', ''),
                Descuento=request.form.get('Descuento'),
                PuntosFidelidad=request.form.get('PuntosFidelidad'),
                CuentaPendiente=request.form.get('CuentaPendiente'),
                EANScanner=request.form.get('EANScanner', ''),
                FormatoAlbaran=request.form.get('FormatoAlbaran', '32'),  # Default based on examples
                UsarRecargoEquivalencia=int(request.form.get('UsarRecargoEquivalencia', 0)),
                DtoProntoPago=request.form.get('DtoProntoPago'),
                NombreBanco=request.form.get('NombreBanco', ''),
                CodigoCuenta=request.form.get('CodigoCuenta', ''),
                NumeroVencimientos=request.form.get('NumeroVencimientos'),
                DiasEntreVencimientos=request.form.get('DiasEntreVencimientos'),
                TotalPorArticulo=int(request.form.get('TotalPorArticulo', 0)),
                AplicarTarifaEtiqueta=int(request.form.get('AplicarTarifaEtiqueta', 1)),  # Default based on examples
                FormatoFactura=request.form.get('FormatoFactura'),
                ModoFacturacion=request.form.get('ModoFacturacion'),
                Modificado=1,  # 1 for active
                Operacion='A',  # 'A' for Added
                Usuario=current_user.username,  # User who created it
                TimeStamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Current timestamp
            )
            
            db.session.add(client)
            db.session.commit()
            flash('Cliente creato con successo!', 'success')
            return redirect(url_for('clients.index'))
        
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Errore nella creazione del cliente: {str(e)}', 'danger')
    
    return render_template('clients/new.html')

@clients_bp.route('/<int:id>', methods=['GET'])
@login_required
def view(id):
    """View a single client"""
    client = Client.query.get_or_404(id)
    return render_template('clients/view.html', client=client)

@clients_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing client"""
    client = Client.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            client.Nombre = request.form.get('Nombre', client.Nombre)
            client.Direccion = request.form.get('Direccion', client.Direccion)
            client.CodPostal = request.form.get('CodPostal', client.CodPostal)
            client.Poblacion = request.form.get('Poblacion', client.Poblacion)
            client.Provincia = request.form.get('Provincia', client.Provincia)
            client.Pais = request.form.get('Pais', client.Pais)
            client.DNI = request.form.get('DNI', client.DNI)
            client.Telefono1 = request.form.get('Telefono1', client.Telefono1)
            client.Telefono2 = request.form.get('Telefono2', client.Telefono2)
            client.Telefono3 = request.form.get('Telefono3', client.Telefono3)
            client.Email = request.form.get('Email', client.Email)
            client.TipoEmailTicket = int(request.form.get('TipoEmailTicket', client.TipoEmailTicket))
            client.TipoEmailAlbaran = int(request.form.get('TipoEmailAlbaran', client.TipoEmailAlbaran))
            client.TipoEmailFactura = int(request.form.get('TipoEmailFactura', client.TipoEmailFactura))
            client.IdTarifa = request.form.get('IdTarifa', client.IdTarifa)
            client.Ofertas = int(request.form.get('Ofertas', client.Ofertas))
            client.IdFormaPago = request.form.get('IdFormaPago', client.IdFormaPago)
            client.IdEstado = request.form.get('IdEstado', client.IdEstado)
            client.Observaciones = request.form.get('Observaciones', client.Observaciones)
            client.CodInterno = request.form.get('CodInterno', client.CodInterno)
            client.Descuento = request.form.get('Descuento', client.Descuento)
            client.PuntosFidelidad = request.form.get('PuntosFidelidad', client.PuntosFidelidad)
            client.CuentaPendiente = request.form.get('CuentaPendiente', client.CuentaPendiente)
            client.EANScanner = request.form.get('EANScanner', client.EANScanner)
            client.FormatoAlbaran = request.form.get('FormatoAlbaran', client.FormatoAlbaran)
            client.UsarRecargoEquivalencia = int(request.form.get('UsarRecargoEquivalencia', client.UsarRecargoEquivalencia))
            client.DtoProntoPago = request.form.get('DtoProntoPago', client.DtoProntoPago)
            client.NombreBanco = request.form.get('NombreBanco', client.NombreBanco)
            client.CodigoCuenta = request.form.get('CodigoCuenta', client.CodigoCuenta)
            client.NumeroVencimientos = request.form.get('NumeroVencimientos', client.NumeroVencimientos)
            client.DiasEntreVencimientos = request.form.get('DiasEntreVencimientos', client.DiasEntreVencimientos)
            client.TotalPorArticulo = int(request.form.get('TotalPorArticulo', client.TotalPorArticulo))
            client.AplicarTarifaEtiqueta = int(request.form.get('AplicarTarifaEtiqueta', client.AplicarTarifaEtiqueta))
            client.FormatoFactura = request.form.get('FormatoFactura', client.FormatoFactura)
            client.ModoFacturacion = request.form.get('ModoFacturacion', client.ModoFacturacion)
            client.Modificado = 1  # Active
            client.Operacion = 'M'  # 'M' for Modified
            client.Usuario = current_user.username  # Current user
            client.TimeStamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Current timestamp
            
            db.session.commit()
            flash('Cliente aggiornato con successo!', 'success')
            return redirect(url_for('clients.view', id=client.IdCliente))
        
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Errore nell\'aggiornamento del cliente: {str(e)}', 'danger')
    
    return render_template('clients/edit.html', client=client)

@clients_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete a client"""
    client = Client.query.get_or_404(id)
    
    try:
        db.session.delete(client)
        db.session.commit()
        flash('Cliente eliminato con successo!', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Errore nell\'eliminazione del cliente: {str(e)}', 'danger')
    
    return redirect(url_for('clients.index'))

@clients_bp.route('/import_csv', methods=['GET', 'POST'])
@login_required
def import_csv():
    """Import clients from CSV file"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nessun file selezionato', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Nessun file selezionato', 'danger')
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            temp_path = os.path.join('/tmp', filename)
            file.save(temp_path)
            
            try:
                clients_imported = 0
                with open(temp_path, 'r', encoding='utf-8') as csv_file:
                    csv_reader = csv.DictReader(csv_file)
                    for row in csv_reader:
                        # Check if client already exists
                        existing_client = Client.query.filter_by(IdCliente=int(row['IdCliente'])).first()
                        
                        if existing_client:
                            # Update existing client
                            for key, value in row.items():
                                if hasattr(existing_client, key):
                                    setattr(existing_client, key, value)
                            existing_client.Operacion = 'M'  # Modified
                            existing_client.Usuario = current_user.username
                            existing_client.TimeStamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            # Create new client
                            new_client = Client()
                            for key, value in row.items():
                                if hasattr(new_client, key):
                                    setattr(new_client, key, value)
                            new_client.Operacion = 'A'  # Added
                            new_client.Usuario = current_user.username
                            new_client.TimeStamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            db.session.add(new_client)
                        
                        clients_imported += 1
                
                db.session.commit()
                flash(f'{clients_imported} clienti importati con successo!', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Errore durante l\'importazione: {str(e)}', 'danger')
            
            finally:
                # Remove temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
    return render_template('clients/import.html')

@clients_bp.route('/export_csv')
@login_required
def export_csv():
    """Export clients to CSV file"""
    try:
        clients = Client.query.all()
        
        # Prepare CSV data
        csv_data = []
        headers = [column.name for column in Client.__table__.columns]
        csv_data.append(headers)
        
        for client in clients:
            row = []
            for header in headers:
                row.append(getattr(client, header))
            csv_data.append(row)
        
        # Create CSV response
        from io import StringIO
        import csv
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerows(csv_data)
        
        # Create response
        from flask import Response
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=clienti.csv'
            }
        )
        
        return response
    
    except Exception as e:
        flash(f'Errore durante l\'esportazione: {str(e)}', 'danger')
        return redirect(url_for('clients.index')) 