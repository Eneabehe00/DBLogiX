from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, Client, AlbaranCabecera, ListinoPrezziHeader
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import csv
import os
import tempfile
from werkzeug.utils import secure_filename
from sqlalchemy import text
from services.utils import admin_required, is_admin
from flask import current_app

clients_bp = Blueprint('clients', __name__, template_folder='templates')

def convert_csv_row_types(row):
    """Convert CSV row values to correct database types"""
    converted = {}
    
    # Define field types for proper conversion
    integer_fields = {
        'IdCliente', 'IdEmpresa', 'TipoEmailTicket', 'TipoEmailAlbaran', 
        'TipoEmailFactura', 'IdTarifa', 'Ofertas', 'IdFormaPago', 'IdEstado',
        'PuntosFidelidad', 'UsarRecargoEquivalencia', 'NumeroVencimientos', 
        'DiasEntreVencimientos', 'TotalPorArticulo', 'AplicarTarifaEtiqueta',
        'FormatoAlbaran', 'ModoFacturacion', 'Modificado'
    }
    
    decimal_fields = {
        'Descuento', 'CuentaPendiente', 'DtoProntoPago'
    }
    
    # Define string fields with their maximum lengths (from database schema)
    string_fields_with_limits = {
        'Nombre': 100,
        'Direccion': 200,
        'CodPostal': 10,
        'Poblacion': 100,
        'Provincia': 100,
        'Pais': 100,
        'DNI': 20,
        'Telefono1': 20,
        'Telefono2': 20,
        'Telefono3': 20,
        'Email': 100,
        'CodInterno': 50,
        'EANScanner': 50,
        'NombreBanco': 100,
        'CodigoCuenta': 50,
        'FormatoFactura': 100,
        'Usuario': 50
    }
    
    # Text fields (no length limit)
    text_fields = {'Observaciones'}
    
    for key, value in row.items():
        if key == 'TimeStamp':
            continue  # Skip timestamp, let database handle it
            
        # Handle None/empty values
        if value in ['None', 'NULL', ''] or value is None:
            converted[key] = None
            continue
            
        # Handle Operacion field specially (can be string or int)
        if key == 'Operacion':
            if value in ['A', 'M']:
                converted[key] = value
            else:
                try:
                    converted[key] = int(value)
                except (ValueError, TypeError):
                    converted[key] = 'A'  # Default to 'A' if conversion fails
            continue
            
        # Handle Foto field (binary data)
        if key == 'Foto':
            if value and value not in ['None', 'NULL', '']:
                # If it's a file path or base64, handle appropriately
                # For now, set to None if empty
                converted[key] = None
            else:
                converted[key] = None
            continue
            
        # Convert integer fields
        if key in integer_fields:
            try:
                converted[key] = int(float(value)) if value else None
            except (ValueError, TypeError):
                converted[key] = None
                
        # Convert decimal fields
        elif key in decimal_fields:
            try:
                converted[key] = float(value) if value else None
            except (ValueError, TypeError):
                converted[key] = None
                
        # String fields with length limits
        elif key in string_fields_with_limits:
            if value:
                # Clean and truncate the string to fit database limits
                clean_value = str(value).strip()
                max_length = string_fields_with_limits[key]
                if len(clean_value) > max_length:
                    # Truncate with warning in console (for debugging)
                    truncated_value = clean_value[:max_length]
                    print(f"Warning: Truncated {key} from {len(clean_value)} to {max_length} characters")
                    converted[key] = truncated_value
                else:
                    converted[key] = clean_value
            else:
                converted[key] = None
                
        # Text fields (no length limit)
        elif key in text_fields:
            converted[key] = str(value).strip() if value else None
            
        # Default for any other fields
        else:
            converted[key] = str(value).strip() if value else None
            
    return converted

@clients_bp.route('/')
@login_required
def index():
    """Display list of all clients with enhanced search functionality"""
    page = request.args.get('page', 1, type=int)
    per_page = 15  # Aumentato da 20 a 15 per uniformità con DDT
    search_query = request.args.get('search', '', type=str).strip()
    
    # Reset page to 1 when performing a new search
    if search_query and page > 1:
        # If there's a search query and we're not on page 1, redirect to page 1
        return redirect(url_for('clients.index', search=search_query, page=1))
    
    # Base query
    clients_query = Client.query
    
    # Apply search filter if provided
    if search_query:
        current_app.logger.info(f"🔍 Client Search: cercando '{search_query}' in tutti i clienti")
        
        try:
            # Try to convert search to integer for ID search
            search_id = int(search_query)
            clients_query = clients_query.filter(
                db.or_(
                    Client.IdCliente == search_id,
                    Client.Nombre.ilike(f'%{search_query}%'),
                    Client.Direccion.ilike(f'%{search_query}%'),
                    Client.Email.ilike(f'%{search_query}%'),
                    Client.Telefono1.ilike(f'%{search_query}%'),
                    Client.DNI.ilike(f'%{search_query}%'),
                    Client.Poblacion.ilike(f'%{search_query}%')
                )
            )
        except ValueError:
            # Search only by text fields if not a number
            clients_query = clients_query.filter(
                db.or_(
                    Client.Nombre.ilike(f'%{search_query}%'),
                    Client.Direccion.ilike(f'%{search_query}%'),
                    Client.Email.ilike(f'%{search_query}%'),
                    Client.Telefono1.ilike(f'%{search_query}%'),
                    Client.DNI.ilike(f'%{search_query}%'),
                    Client.Poblacion.ilike(f'%{search_query}%')
                )
            )
        
        current_app.logger.info(f"🔍 Search query applied for '{search_query}'")
    
    # Order and paginate
    pagination = clients_query.order_by(Client.IdCliente.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    current_app.logger.info(f"📄 Clients page {page}: showing {len(pagination.items)} of {pagination.total} total clients")
    
    return render_template('clients/index.html', 
                         clients=pagination.items, 
                         pagination=pagination, 
                         search=search_query)

@clients_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new():
    """Create a new client"""
    if request.method == 'POST':
        try:
            # Get next available IdCliente
            max_id = db.session.query(db.func.max(Client.IdCliente)).scalar() or 0
            new_id = max_id + 1
            
            # Handle checkbox fields (they're only present in the request if checked)
            tipo_email_ticket = 1 if request.form.get('TipoEmailTicket') else 0
            tipo_email_albaran = 1 if request.form.get('TipoEmailAlbaran') else 0
            tipo_email_factura = 1 if request.form.get('TipoEmailFactura') else 0
            total_por_articulo = 1 if request.form.get('TotalPorArticulo') else 0
            aplicar_tarifa_etiqueta = 1 if request.form.get('AplicarTarifaEtiqueta') else 0
            usar_recargo_equivalencia = 0  # Default value
            
            # Convert empty strings to None for numeric fields
            descuento = request.form.get('Descuento') or None
            if descuento == '0':
                descuento = 0  # Keep zero as a valid value
                
            puntos_fidelidad = request.form.get('PuntosFidelidad') or None
            if puntos_fidelidad == '0':
                puntos_fidelidad = 0  # Keep zero as a valid value
                
            cuenta_pendiente = request.form.get('CuentaPendiente') or None
            dto_pronto_pago = request.form.get('DtoProntoPago') or None
            numero_vencimientos = request.form.get('NumeroVencimientos') or None
            dias_entre_vencimientos = request.form.get('DiasEntreVencimientos') or None
            
            # Format string values to match field lengths
            nombre = request.form.get('Nombre', '')[:50]  # varchar(50)
            direccion = request.form.get('Direccion', '')[:50]  # varchar(50)
            cod_postal = request.form.get('CodPostal', '')[:8]  # varchar(8)
            poblacion = request.form.get('Poblacion', '')[:25]  # varchar(25)
            provincia = request.form.get('Provincia', '')[:25]  # varchar(25)
            pais = request.form.get('Pais', 'IT')[:10]  # varchar(10)
            dni = request.form.get('DNI', '')[:30]  # varchar(30)
            telefono1 = request.form.get('Telefono1', '')[:20]  # varchar(20)
            telefono2 = request.form.get('Telefono2', '')[:20]  # varchar(20)
            telefono3 = request.form.get('Telefono3', '')[:20]  # varchar(20)
            email = request.form.get('Email', '')[:100]  # varchar(100)
            cod_interno = request.form.get('CodInterno', '')[:25]  # varchar(25)
            ean_scanner = request.form.get('EANScanner', '')[:50]  # varchar(50)
            nombre_banco = request.form.get('NombreBanco', '')[:100]  # varchar(100)
            codigo_cuenta = request.form.get('CodigoCuenta', '')[:100]  # varchar(100)
            
            # Set default integer value for FormatoAlbaran
            formato_albaran = 32  # Default value based on examples
            
            # Insert client directly with SQL to avoid SQLAlchemy type issues
            sql = text("""
            INSERT INTO dat_cliente (
                IdCliente, IdEmpresa, Nombre, Direccion, CodPostal, Poblacion, Provincia, Pais, 
                DNI, Telefono1, Telefono2, Telefono3, Email, TipoEmailTicket, TipoEmailAlbaran, 
                TipoEmailFactura, Foto, IdTarifa, IdListino, Ofertas, IdFormaPago, IdEstado, Observaciones, 
                CodInterno, Descuento, PuntosFidelidad, CuentaPendiente, EANScanner, FormatoAlbaran, 
                UsarRecargoEquivalencia, DtoProntoPago, NombreBanco, CodigoCuenta, NumeroVencimientos, 
                DiasEntreVencimientos, TotalPorArticulo, AplicarTarifaEtiqueta, FormatoFactura, 
                ModoFacturacion, Modificado, Operacion, Usuario, TimeStamp
            ) VALUES (
                :IdCliente, :IdEmpresa, :Nombre, :Direccion, :CodPostal, :Poblacion, :Provincia, :Pais,
                :DNI, :Telefono1, :Telefono2, :Telefono3, :Email, :TipoEmailTicket, :TipoEmailAlbaran,
                :TipoEmailFactura, :Foto, :IdTarifa, :IdListino, :Ofertas, :IdFormaPago, :IdEstado, :Observaciones,
                :CodInterno, :Descuento, :PuntosFidelidad, :CuentaPendiente, :EANScanner, :FormatoAlbaran,
                :UsarRecargoEquivalencia, :DtoProntoPago, :NombreBanco, :CodigoCuenta, :NumeroVencimientos,
                :DiasEntreVencimientos, :TotalPorArticulo, :AplicarTarifaEtiqueta, :FormatoFactura,
                :ModoFacturacion, :Modificado, :Operacion, :Usuario, NULL
            )
            """)
            
            params = {
                'IdCliente': new_id,
                'IdEmpresa': 1,
                'Nombre': nombre,
                'Direccion': direccion,
                'CodPostal': cod_postal,
                'Poblacion': poblacion,
                'Provincia': provincia,
                'Pais': pais,
                'DNI': dni,
                'Telefono1': telefono1,
                'Telefono2': telefono2,
                'Telefono3': telefono3,
                'Email': email,
                'TipoEmailTicket': tipo_email_ticket,
                'TipoEmailAlbaran': tipo_email_albaran,
                'TipoEmailFactura': tipo_email_factura,
                'Foto': '',
                'IdTarifa': request.form.get('IdTarifa') or None,
                'IdListino': request.form.get('IdListino') or None,
                'Ofertas': int(request.form.get('Ofertas', 0)),
                'IdFormaPago': request.form.get('IdFormaPago') or None,
                'IdEstado': request.form.get('IdEstado') or None,
                'Observaciones': request.form.get('Observaciones', ''),
                'CodInterno': cod_interno,
                'Descuento': descuento,
                'PuntosFidelidad': puntos_fidelidad,
                'CuentaPendiente': cuenta_pendiente,
                'EANScanner': ean_scanner,
                'FormatoAlbaran': formato_albaran,
                'UsarRecargoEquivalencia': usar_recargo_equivalencia,
                'DtoProntoPago': dto_pronto_pago,
                'NombreBanco': nombre_banco,
                'CodigoCuenta': codigo_cuenta,
                'NumeroVencimientos': numero_vencimientos,
                'DiasEntreVencimientos': dias_entre_vencimientos,
                'TotalPorArticulo': total_por_articulo,
                'AplicarTarifaEtiqueta': aplicar_tarifa_etiqueta,
                'FormatoFactura': None,
                'ModoFacturacion': None,
                'Modificado': 1,
                'Operacion': 'A',
                'Usuario': current_user.username,
            }
            
            db.session.execute(sql, params)
            
            # Inserimento automatico in dat_cliente_t
            sql_cliente_t = text("""
            INSERT INTO dat_cliente_t (
                IdCliente, IdEmpresa, IdTienda, Modificado, Operacion, Usuario, TimeStamp
            ) VALUES (
                :IdCliente, :IdEmpresa, :IdTienda, :Modificado, :Operacion, :Usuario, NOW()
            )
            """)
            
            params_t = {
                'IdCliente': new_id,
                'IdEmpresa': 1,
                'IdTienda': 1,
                'Modificado': 1,
                'Operacion': 'A',
                'Usuario': current_user.username
            }
            
            db.session.execute(sql_cliente_t, params_t)
            
            # Inserimento automatico in dat_cliente_t_b
            sql_cliente_t_b = text("""
            INSERT INTO dat_cliente_t_b (
                IdCliente, IdEmpresa, IdTienda, IdBalanza, Modificado, Operacion, Usuario, TimeStamp
            ) VALUES (
                :IdCliente, :IdEmpresa, :IdTienda, :IdBalanza, :Modificado, :Operacion, :Usuario, NOW()
            )
            """)
            
            params_t_b = {
                'IdCliente': new_id,
                'IdEmpresa': 1,
                'IdTienda': 1,
                'IdBalanza': 1,
                'Modificado': 1,
                'Operacion': 'A',
                'Usuario': current_user.username
            }
            
            db.session.execute(sql_cliente_t_b, params_t_b)
            
            db.session.commit()
            flash('Cliente creato e sincronizzato!', 'success')
            return redirect(url_for('clients.index'))
        
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Errore nella creazione del cliente: {str(e)}', 'danger')
    
    # Ottieni listini disponibili per il dropdown
    listini = ListinoPrezziHeader.query.filter_by(Attivo=True).order_by(ListinoPrezziHeader.NomeListino).all()
    
    return render_template('clients/new.html', listini=listini)

@clients_bp.route('/<int:id>', methods=['GET'])
@login_required
def view(id):
    """View a single client"""
    client = Client.query.get_or_404(id)
    
    # Obtener los DDT (AlbaranCabecera) asociados al cliente
    page = request.args.get('ddt_page', 1, type=int)
    ddts_query = AlbaranCabecera.query.filter_by(IdCliente=id)\
                .order_by(AlbaranCabecera.Fecha.desc())
    
    # Añadir información de cuántos artículos tiene cada DDT
    ddts_with_count = []
    for ddt in ddts_query.all():
        # Contar artículos en el DDT
        num_articles = ddt.lineas.count()
        
        # Crear un objeto con los datos del DDT y el conteo
        ddt_data = {
            'id': ddt.NumAlbaran,  # Usa NumAlbaran per l'identificazione visuale
            'internal_id': ddt.IdAlbaran,  # Mantieni IdAlbaran per i link interni
            'numero': ddt.NumAlbaran,
            'fecha': ddt.Fecha,
            'estado': ddt.EstadoTicket if hasattr(ddt, 'EstadoTicket') else None,
            'referente': ddt.ReferenciaDocumento,
            'total': ddt.ImporteTotal,
            'num_articles': num_articles
        }
        ddts_with_count.append(ddt_data)
    
    # Paginar los resultados
    per_page = 10
    total_items = len(ddts_with_count)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Simular paginación
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    current_page_items = ddts_with_count[start_idx:end_idx]
    
    # Crear un objeto de paginación para usar en la plantilla
    pagination = {
        'items': current_page_items,
        'page': page,
        'per_page': per_page,
        'total': total_items,
        'pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1,
        'next_num': page + 1,
        'iter_pages': lambda: range(1, total_pages + 1)
    }
    
    return render_template('clients/view.html', client=client, ddts=current_page_items, pagination=pagination if total_items > per_page else None)

@clients_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    """Edit an existing client"""
    client = Client.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Convert empty strings to None for numeric fields
            descuento = request.form.get('Descuento') or None
            puntos_fidelidad = request.form.get('PuntosFidelidad') or None
            cuenta_pendiente = request.form.get('CuentaPendiente') or None
            dto_pronto_pago = request.form.get('DtoProntoPago') or None
            numero_vencimientos = request.form.get('NumeroVencimientos') or None
            dias_entre_vencimientos = request.form.get('DiasEntreVencimientos') or None
            
            # Handle integer fields properly
            formato_albaran = request.form.get('FormatoAlbaran')
            if formato_albaran:
                formato_albaran = int(formato_albaran)
            
            formato_factura = request.form.get('FormatoFactura')
            if formato_factura:
                formato_factura = int(formato_factura)
            
            modo_facturacion = request.form.get('ModoFacturacion')
            if modo_facturacion:
                modo_facturacion = int(modo_facturacion)
            
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
            client.IdTarifa = request.form.get('IdTarifa') or None
            client.IdListino = request.form.get('IdListino') or None
            client.Ofertas = int(request.form.get('Ofertas', client.Ofertas))
            client.IdFormaPago = request.form.get('IdFormaPago') or None
            client.IdEstado = request.form.get('IdEstado') or None
            client.Observaciones = request.form.get('Observaciones', client.Observaciones)
            client.CodInterno = request.form.get('CodInterno', client.CodInterno)
            client.Descuento = descuento
            client.PuntosFidelidad = puntos_fidelidad
            client.CuentaPendiente = cuenta_pendiente
            client.EANScanner = request.form.get('EANScanner', client.EANScanner)
            client.FormatoAlbaran = formato_albaran
            client.UsarRecargoEquivalencia = int(request.form.get('UsarRecargoEquivalencia', client.UsarRecargoEquivalencia))
            client.DtoProntoPago = dto_pronto_pago
            client.NombreBanco = request.form.get('NombreBanco', client.NombreBanco)
            client.CodigoCuenta = request.form.get('CodigoCuenta', client.CodigoCuenta)
            client.NumeroVencimientos = numero_vencimientos
            client.DiasEntreVencimientos = dias_entre_vencimientos
            client.TotalPorArticulo = int(request.form.get('TotalPorArticulo', client.TotalPorArticulo))
            client.AplicarTarifaEtiqueta = int(request.form.get('AplicarTarifaEtiqueta', client.AplicarTarifaEtiqueta))
            client.FormatoFactura = formato_factura
            client.ModoFacturacion = modo_facturacion
            client.Modificado = 1  # Active
            client.Operacion = 'M'  # 'M' for Modified (as char)
            client.Usuario = current_user.username  # Current user
            # Let the database handle the timestamp
            
            db.session.commit()
            flash('Cliente aggiornato!', 'success')
            return redirect(url_for('clients.view', id=client.IdCliente))
        
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Errore nell\'aggiornamento del cliente: {str(e)}', 'danger')
    
    # Ottieni listini disponibili per il dropdown
    listini = ListinoPrezziHeader.query.filter_by(Attivo=True).order_by(ListinoPrezziHeader.NomeListino).all()
    
    return render_template('clients/edit.html', client=client, listini=listini)

@clients_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(id):
    """Delete a client"""
    client = Client.query.get_or_404(id)
    
    try:
        # Prima eliminiamo i record correlati nelle tabelle di configurazione
        # Eliminazione da dat_cliente_t_b
        db.session.execute(text("""
            DELETE FROM dat_cliente_t_b 
            WHERE IdCliente = :id_cliente
        """), {"id_cliente": id})
        
        # Eliminazione da dat_cliente_t
        db.session.execute(text("""
            DELETE FROM dat_cliente_t 
            WHERE IdCliente = :id_cliente
        """), {"id_cliente": id})
        
        # Poi eliminiamo il record principale
        db.session.delete(client)
        db.session.commit()
        flash('Cliente eliminato!', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Errore nell\'eliminazione del cliente: {str(e)}', 'danger')
    
    return redirect(url_for('clients.index'))

@clients_bp.route('/import_csv', methods=['GET', 'POST'])
@login_required
@admin_required
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
            # Use system temp directory (works on Windows and Unix)
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, filename)
            file.save(temp_path)
            
            try:
                clients_imported = 0
                with open(temp_path, 'r', encoding='utf-8') as csv_file:
                    csv_reader = csv.DictReader(csv_file)
                    for row in csv_reader:
                        # Check if client already exists
                        existing_client = Client.query.filter_by(IdCliente=int(row['IdCliente'])).first()
                        
                        # Convert row values to correct types
                        converted_row = convert_csv_row_types(row)
                        
                        if existing_client:
                            # Update existing client
                            for key, value in converted_row.items():
                                if hasattr(existing_client, key) and key != 'TimeStamp':
                                    setattr(existing_client, key, value)
                            
                            existing_client.Operacion = 'M'  # Modified
                            existing_client.Usuario = current_user.username
                            # Let database handle timestamp
                        else:
                            # Create new client
                            new_client = Client()
                            for key, value in converted_row.items():
                                if hasattr(new_client, key) and key != 'TimeStamp':
                                    setattr(new_client, key, value)
                            
                            new_client.Operacion = 'A'  # Added
                            new_client.Usuario = current_user.username
                            # Let database handle timestamp
                            db.session.add(new_client)
                            db.session.flush()  # Flush to get the ID
                            
                            # Inserimento automatico in dat_cliente_t per nuovo cliente
                            sql_cliente_t = text("""
                            INSERT INTO dat_cliente_t (
                                IdCliente, IdEmpresa, IdTienda, Modificado, Operacion, Usuario, TimeStamp
                            ) VALUES (
                                :IdCliente, :IdEmpresa, :IdTienda, :Modificado, :Operacion, :Usuario, NOW()
                            )
                            """)
                            
                            params_t = {
                                'IdCliente': new_client.IdCliente,
                                'IdEmpresa': 1,
                                'IdTienda': 1,
                                'Modificado': 1,
                                'Operacion': 'A',
                                'Usuario': current_user.username
                            }
                            
                            db.session.execute(sql_cliente_t, params_t)
                            
                            # Inserimento automatico in dat_cliente_t_b per nuovo cliente
                            sql_cliente_t_b = text("""
                            INSERT INTO dat_cliente_t_b (
                                IdCliente, IdEmpresa, IdTienda, IdBalanza, Modificado, Operacion, Usuario, TimeStamp
                            ) VALUES (
                                :IdCliente, :IdEmpresa, :IdTienda, :IdBalanza, :Modificado, :Operacion, :Usuario, NOW()
                            )
                            """)
                            
                            params_t_b = {
                                'IdCliente': new_client.IdCliente,
                                'IdEmpresa': 1,
                                'IdTienda': 1,
                                'IdBalanza': 1,
                                'Modificado': 1,
                                'Operacion': 'A',
                                'Usuario': current_user.username
                            }
                            
                            db.session.execute(sql_cliente_t_b, params_t_b)
                        
                        clients_imported += 1
                
                db.session.commit()
                flash(f'{clients_imported} clienti importati!', 'success')
                
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
@admin_required
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

@clients_bp.route('/api/search_listini')
@login_required
@admin_required
def api_search_listini():
    """API per cercare listini da associare al cliente"""
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify([])
        
        # Cerca listini per nome o ID
        listini_query = ListinoPrezziHeader.query.filter_by(Attivo=True)
        
        try:
            # Try to convert search to integer for ID search
            search_id = int(query)
            listini_query = listini_query.filter(
                db.or_(
                    ListinoPrezziHeader.IdListino == search_id,
                    ListinoPrezziHeader.NomeListino.ilike(f'%{query}%')
                )
            )
        except ValueError:
            # Search only by text fields if not a number
            listini_query = listini_query.filter(
                ListinoPrezziHeader.NomeListino.ilike(f'%{query}%')
            )
        
        listini = listini_query.order_by(ListinoPrezziHeader.NomeListino).limit(20).all()
        
        listini_data = []
        for listino in listini:
            listini_data.append({
                'IdListino': listino.IdListino,
                'NomeListino': listino.NomeListino,
                'Descrizione': listino.Descrizione,
                'numero_articoli': listino.numero_articoli,
                'Attivo': listino.Attivo
            })
        
        return jsonify(listini_data)
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore ricerca listini: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@clients_bp.route('/<int:client_id>/assign_listino/<int:listino_id>', methods=['POST'])
@login_required
@admin_required
def assign_listino_to_client(client_id, listino_id):
    """API per associare un listino al cliente"""
    try:
        client = Client.query.get_or_404(client_id)
        listino = ListinoPrezziHeader.query.get_or_404(listino_id)
        
        # Aggiorna il cliente con il nuovo listino
        client.IdListino = listino_id
        db.session.commit()
        
        current_app.logger.info(f"✅ Listino {listino_id} ({listino.NomeListino}) associato al cliente {client_id}")
        
        return jsonify({
            'success': True,
            'message': f'Listino "{listino.NomeListino}" associato con successo al cliente "{client.Nombre}"'
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore assegnazione listino al cliente: {str(e)}")
        return jsonify({'success': False, 'error': 'Errore durante l\'assegnazione'}), 500

@clients_bp.route('/<int:client_id>/remove_listino', methods=['POST'])
@login_required
@admin_required
def remove_listino_from_client(client_id):
    """Rimuove un listino dal cliente (reimposta a prezzi standard)"""
    try:
        client = Client.query.get_or_404(client_id)
        
        listino_name = client.listino.NomeListino if client.listino else 'N/A'
        
        # Rimuovi l'associazione
        client.IdListino = None
        db.session.commit()
        
        current_app.logger.info(f"✅ Listino rimosso dal cliente {client_id} ({client.Nombre})")
        flash(f'Listino "{listino_name}" rimosso dal cliente con successo', 'success')
        
        return redirect(url_for('clients.view', id=client_id))
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore rimozione listino dal cliente: {str(e)}")
        flash('Errore durante la rimozione del listino dal cliente', 'error')
        return redirect(url_for('clients.view', id=client_id))