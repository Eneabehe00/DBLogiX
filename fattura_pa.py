from flask import Blueprint, request, redirect, url_for, flash, send_file, current_app, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_
from models import db, Company, Client, AlbaranCabecera, AlbaranLinea
from datetime import datetime
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io
import logging
import uuid

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
fattura_pa_bp = Blueprint('fattura_pa', __name__)

# Constants
NAMESPACE_MAP = {
    '': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2',
    'ds': 'http://www.w3.org/2000/09/xmldsig#',
    'p': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

# Helper functions
def get_next_invoice_number():
    """Get the next progressive invoice number"""
    # TODO: Implement proper invoice numbering logic
    # For now, using a simple timestamp-based number
    return int(datetime.now().strftime('%y%m%d%H%M'))

def format_decimal(value, decimal_places=2):
    """Format a decimal value with fixed decimal places"""
    if value is None:
        return "0.00"
    return f"{float(value):.{decimal_places}f}"

def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element"""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding='utf-8')

def create_fattura_pa_from_ddt(ddt_id):
    """Create a FatturaPA XML file from a DDT"""
    try:
        # Fetch the DDT with related data
        ddt = AlbaranCabecera.query.filter_by(IdAlbaran=ddt_id).first()
        if not ddt:
            return None, f"DDT with ID {ddt_id} not found"

        # Get company and client data
        company = Company.query.get(ddt.IdEmpresa)
        client = Client.query.get(ddt.IdCliente)
        
        if not company or not client:
            return None, "Company or client data missing"
            
        # Get DDT lines
        ddt_lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt_id).all()
        if not ddt_lines:
            return None, "No items found in the DDT"
            
        # Generate invoice number
        invoice_number = get_next_invoice_number()
        
        # Create the root element with namespaces
        root = ET.Element('p:FatturaElettronica', {
            'versione': 'FPR12',
            'xmlns:ds': NAMESPACE_MAP['ds'],
            'xmlns:p': NAMESPACE_MAP['p'],
            'xmlns:xsi': NAMESPACE_MAP['xsi'],
            'xsi:schemaLocation': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2/Schema_del_file_xml_FatturaPA_versione_1.2.xsd'
        })
        
        # 1. FatturaElettronicaHeader
        header = ET.SubElement(root, 'FatturaElettronicaHeader')
        
        # 1.1 DatiTrasmissione
        dati_trasmissione = ET.SubElement(header, 'DatiTrasmissione')
        id_trasmittente = ET.SubElement(dati_trasmissione, 'IdTrasmittente')
        ET.SubElement(id_trasmittente, 'IdPaese').text = 'IT'
        ET.SubElement(id_trasmittente, 'IdCodice').text = company.CIF_VAT.replace('IT', '') if company.CIF_VAT.startswith('IT') else company.CIF_VAT
        ET.SubElement(dati_trasmissione, 'ProgressivoInvio').text = str(uuid.uuid4())[:6]  # Random ID for transmission
        ET.SubElement(dati_trasmissione, 'FormatoTrasmissione').text = 'FPR12'  # Invoice to private
        
        # Add the receiver's SDI code (Codice Destinatario) 
        # If this is 7 zeroes, then PEC must be provided in PECDestinatario
        ET.SubElement(dati_trasmissione, 'CodiceDestinatario').text = '0000000'  # Default value
        
        # 1.2 CedentePrestatore (Seller)
        cedente = ET.SubElement(header, 'CedentePrestatore')
        
        # 1.2.1 DatiAnagrafici
        dati_anagrafici = ET.SubElement(cedente, 'DatiAnagrafici')
        id_fiscale = ET.SubElement(dati_anagrafici, 'IdFiscaleIVA')
        ET.SubElement(id_fiscale, 'IdPaese').text = 'IT'
        ET.SubElement(id_fiscale, 'IdCodice').text = company.CIF_VAT.replace('IT', '') if company.CIF_VAT.startswith('IT') else company.CIF_VAT
        
        # Codice Fiscale (if different from VAT)
        # ET.SubElement(dati_anagrafici, 'CodiceFiscale').text = company.CIF_VAT
        
        anagrafica = ET.SubElement(dati_anagrafici, 'Anagrafica')
        ET.SubElement(anagrafica, 'Denominazione').text = company.NombreEmpresa
        
        # Regime Fiscale (RF01 = regime ordinario)
        ET.SubElement(dati_anagrafici, 'RegimeFiscale').text = 'RF01'
        
        # 1.2.2 Sede
        sede = ET.SubElement(cedente, 'Sede')
        ET.SubElement(sede, 'Indirizzo').text = company.Direccion or ''
        ET.SubElement(sede, 'CAP').text = company.CodPostal or ''
        ET.SubElement(sede, 'Comune').text = company.Poblacion or ''
        ET.SubElement(sede, 'Provincia').text = company.Provincia[:2] if company.Provincia and len(company.Provincia) >= 2 else ''
        ET.SubElement(sede, 'Nazione').text = 'IT'
        
        # 1.3 CessionarioCommittente (Buyer)
        cessionario = ET.SubElement(header, 'CessionarioCommittente')
        
        # 1.3.1 DatiAnagrafici
        dati_anagrafici = ET.SubElement(cessionario, 'DatiAnagrafici')
        
        # Check if client has a VAT number or fiscal code
        if client.DNI and client.DNI.strip():
            # If it's a VAT number (Partita IVA)
            if client.DNI.startswith('IT') and len(client.DNI) >= 13:
                id_fiscale = ET.SubElement(dati_anagrafici, 'IdFiscaleIVA')
                ET.SubElement(id_fiscale, 'IdPaese').text = 'IT'
                ET.SubElement(id_fiscale, 'IdCodice').text = client.DNI.replace('IT', '')
            else:
                # Assume it's a CodiceFiscale
                ET.SubElement(dati_anagrafici, 'CodiceFiscale').text = client.DNI
        
        anagrafica = ET.SubElement(dati_anagrafici, 'Anagrafica')
        ET.SubElement(anagrafica, 'Denominazione').text = client.Nombre
        
        # 1.3.2 Sede
        sede = ET.SubElement(cessionario, 'Sede')
        ET.SubElement(sede, 'Indirizzo').text = client.Direccion or ''
        ET.SubElement(sede, 'CAP').text = client.CodPostal or ''
        ET.SubElement(sede, 'Comune').text = client.Poblacion or ''
        ET.SubElement(sede, 'Provincia').text = client.Provincia[:2] if client.Provincia and len(client.Provincia) >= 2 else ''
        ET.SubElement(sede, 'Nazione').text = 'IT'
        
        # 2. FatturaElettronicaBody
        body = ET.SubElement(root, 'FatturaElettronicaBody')
        
        # 2.1 DatiGenerali
        dati_generali = ET.SubElement(body, 'DatiGenerali')
        
        # 2.1.1 DatiGeneraliDocumento
        dati_generali_doc = ET.SubElement(dati_generali, 'DatiGeneraliDocumento')
        
        # If it's based on a DDT, set the type to TD24 (fattura differita)
        ET.SubElement(dati_generali_doc, 'TipoDocumento').text = 'TD24'  # TD24 for 'fattura differita'
        
        # Set the invoice currency to EUR
        ET.SubElement(dati_generali_doc, 'Divisa').text = 'EUR'
        
        # Invoice date in ISO format (YYYY-MM-DD)
        invoice_date = datetime.now().strftime('%Y-%m-%d')
        ET.SubElement(dati_generali_doc, 'Data').text = invoice_date
        
        # Invoice number (must be unique)
        ET.SubElement(dati_generali_doc, 'Numero').text = str(invoice_number)
        
        # Add causation (Causale) if there's a DDT reference
        ET.SubElement(dati_generali_doc, 'Causale').text = f"Fattura differita da DDT n. {ddt.NumAlbaran} del {ddt.Fecha.strftime('%d/%m/%Y') if ddt.Fecha else 'N/A'}"
        
        # 2.1.2 DatiDDT (DDT references) since this is a 'fattura differita'
        dati_ddt = ET.SubElement(dati_generali, 'DatiDDT')
        ET.SubElement(dati_ddt, 'NumeroDDT').text = str(ddt.NumAlbaran)
        ET.SubElement(dati_ddt, 'DataDDT').text = ddt.Fecha.strftime('%Y-%m-%d') if ddt.Fecha else datetime.now().strftime('%Y-%m-%d')
        
        # 2.2 DatiBeniServizi (Invoice Line Items)
        dati_beni_servizi = ET.SubElement(body, 'DatiBeniServizi')
        
        # Group VAT rates for summary
        vat_summary = {}
        
        # Add each line item from the DDT
        for i, line in enumerate(ddt_lines, 1):
            dati_linea = ET.SubElement(dati_beni_servizi, 'DettaglioLinee')
            ET.SubElement(dati_linea, 'NumeroLinea').text = str(i)
            ET.SubElement(dati_linea, 'Descrizione').text = line.Descripcion
            ET.SubElement(dati_linea, 'Quantita').text = format_decimal(line.Peso, 2)
            ET.SubElement(dati_linea, 'UnitaMisura').text = line.Medida2 or 'PZ'
            ET.SubElement(dati_linea, 'PrezzoUnitario').text = format_decimal(line.PrecioSinIVA, 6)
            
            # Calculate line amount without VAT
            price_without_vat = float(line.ImporteSinIVAConDtoL or 0)
            ET.SubElement(dati_linea, 'PrezzoTotale').text = format_decimal(price_without_vat, 2)
            
            # VAT rate for the line
            vat_rate = float(line.PorcentajeIVA or 0)
            ET.SubElement(dati_linea, 'AliquotaIVA').text = format_decimal(vat_rate, 2)
            
            # Add to VAT summary
            vat_key = format_decimal(vat_rate, 2)
            if vat_key not in vat_summary:
                vat_summary[vat_key] = {
                    'ImponibileImporto': 0.0,
                    'Imposta': 0.0,
                    'AliquotaIVA': vat_rate
                }
            
            # Add the line amount to the summary
            vat_summary[vat_key]['ImponibileImporto'] += price_without_vat
            vat_summary[vat_key]['Imposta'] += price_without_vat * (vat_rate / 100)
        
        # 2.2.2 DatiRiepilogo (VAT Summary)
        for vat_rate, data in vat_summary.items():
            dati_riepilogo = ET.SubElement(dati_beni_servizi, 'DatiRiepilogo')
            ET.SubElement(dati_riepilogo, 'AliquotaIVA').text = vat_rate
            ET.SubElement(dati_riepilogo, 'ImponibileImporto').text = format_decimal(data['ImponibileImporto'], 2)
            ET.SubElement(dati_riepilogo, 'Imposta').text = format_decimal(data['Imposta'], 2)
            ET.SubElement(dati_riepilogo, 'EsigibilitaIVA').text = 'I'  # I = immediate
        
        # 2.4 DatiPagamento (Payment details)
        dati_pagamento = ET.SubElement(body, 'DatiPagamento')
        ET.SubElement(dati_pagamento, 'CondizioniPagamento').text = 'TP02'  # TP02 = complete payment
        
        dettaglio_pagamento = ET.SubElement(dati_pagamento, 'DettaglioPagamento')
        ET.SubElement(dettaglio_pagamento, 'ModalitaPagamento').text = 'MP05'  # MP05 = bank transfer
        
        # Payment due date (30 days from invoice date by default)
        payment_date = datetime.now()
        payment_date = payment_date.replace(month=payment_date.month + 1 if payment_date.month < 12 else 1)
        if payment_date.month == 1:
            payment_date = payment_date.replace(year=payment_date.year + 1)
            
        ET.SubElement(dettaglio_pagamento, 'DataScadenzaPagamento').text = payment_date.strftime('%Y-%m-%d')
        ET.SubElement(dettaglio_pagamento, 'ImportoPagamento').text = format_decimal(ddt.ImporteTotal, 2)
        
        # Add IBAN if available
        # ET.SubElement(dettaglio_pagamento, 'IBAN').text = "IT00X0000000000000000000000"  # Example IBAN
        
        # Generate the invoice XML
        xml_data = prettify_xml(root)
        
        # Generate filename according to Italian SDI rules
        # Format: IT[VAT_NUMBER]_[DOC_TYPE]_[PROGRESSIVE_NUMBER].xml
        vat_number = company.CIF_VAT.replace('IT', '') if company.CIF_VAT.startswith('IT') else company.CIF_VAT
        filename = f"IT{vat_number}_FPR12_{invoice_number:05d}.xml"
        
        # Create the full path for saving the file
        fatture_dir = os.path.join(current_app.root_path, 'Fatture')
        os.makedirs(fatture_dir, exist_ok=True)
        
        file_path = os.path.join(fatture_dir, filename)
        
        # Save the XML to file
        with open(file_path, 'wb') as f:
            f.write(xml_data)
            
        return file_path, None  # Return the file path and no error
        
    except Exception as e:
        logger.error(f"Error generating FatturaPA XML: {str(e)}")
        return None, str(e)

# Blueprint routes
@fattura_pa_bp.route('/create/<int:ddt_id>', methods=['POST'])
@login_required
def create_invoice(ddt_id):
    """Create a FatturaPA invoice from a DDT"""
    try:
        # Generate the invoice XML
        file_path, error = create_fattura_pa_from_ddt(ddt_id)
        
        if error:
            flash(f'Errore durante la generazione della fattura: {error}', 'danger')
            return redirect(url_for('ddt.detail', ddt_id=ddt_id))
            
        # Get just the filename
        filename = os.path.basename(file_path)
        
        flash(f'Fattura elettronica generata con successo: {filename}', 'success')
        
        # Option to download the file directly
        if request.form.get('download', 'false') == 'true':
            with open(file_path, 'rb') as f:
                data = f.read()
                
            return send_file(
                io.BytesIO(data),
                mimetype='application/xml',
                as_attachment=True,
                download_name=filename
            )
            
        # Redirect back to the DDT detail page
        return redirect(url_for('ddt.detail', ddt_id=ddt_id))
        
    except Exception as e:
        flash(f'Errore imprevisto: {str(e)}', 'danger')
        return redirect(url_for('ddt.detail', ddt_id=ddt_id))

@fattura_pa_bp.route('/list')
@login_required
def list_invoices():
    """List all generated invoices"""
    fatture_dir = os.path.join(current_app.root_path, 'Fatture')
    os.makedirs(fatture_dir, exist_ok=True)
    
    invoices = []
    for filename in os.listdir(fatture_dir):
        if filename.endswith('.xml'):
            file_path = os.path.join(fatture_dir, filename)
            creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
            
            invoices.append({
                'filename': filename,
                'created_at': creation_time,
                'size': os.path.getsize(file_path)
            })
    
    # Sort by creation time (newest first)
    invoices.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('fattura_pa/list.html', invoices=invoices)

@fattura_pa_bp.route('/details/<filename>')
@login_required
def invoice_details(filename):
    """Get invoice details for AJAX requests"""
    try:
        fatture_dir = os.path.join(current_app.root_path, 'Fatture')
        file_path = os.path.join(fatture_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'File non trovato'}), 404
            
        # Get file stats
        creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
        file_size = os.path.getsize(file_path)
        
        # Parse XML to extract additional details
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract invoice details from XML (this is a simplified version)
            invoice_details = {
                'filename': filename,
                'created_at': creation_time.strftime('%d/%m/%Y %H:%M'),
                'size': f"{file_size / 1024:.1f} KB",
                'invoice_number': None,
                'client_name': None,
                'total_amount': None,
                'ddt_reference': None
            }
            
            # Try to extract more details from XML
            for elem in root.iter():
                if 'Numero' in elem.tag and elem.text:
                    invoice_details['invoice_number'] = elem.text
                elif 'Denominazione' in elem.tag and elem.text and not invoice_details['client_name']:
                    invoice_details['client_name'] = elem.text
                elif 'ImportoPagamento' in elem.tag and elem.text:
                    invoice_details['total_amount'] = elem.text
                elif 'NumeroDDT' in elem.tag and elem.text:
                    invoice_details['ddt_reference'] = elem.text
                    
            return jsonify({'success': True, 'data': invoice_details})
            
        except ET.ParseError:
            return jsonify({'success': False, 'message': 'Errore nel parsing del file XML'}), 500
            
    except Exception as e:
        logger.error(f"Error getting invoice details for {filename}: {str(e)}")
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500

@fattura_pa_bp.route('/detail/<filename>')
@login_required
def invoice_detail_page(filename):
    """Show invoice detail page"""
    try:
        fatture_dir = os.path.join(current_app.root_path, 'Fatture')
        file_path = os.path.join(fatture_dir, filename)
        
        if not os.path.exists(file_path):
            return render_template('fattura_pa/detail.html', invoice_details=None)
        
        # Get file stats
        creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
        file_size = os.path.getsize(file_path)
        
        # Initialize invoice details structure
        invoice_details = {
            'filename': filename,
            'created_at': creation_time.strftime('%d/%m/%Y %H:%M'),
            'size': f"{file_size / 1024:.1f} KB",
            'invoice_number': None,
            'invoice_date': None,
            'client_name': None,
            'client_address': None,
            'client_vat': None,
            'client_fiscal_code': None,
            'client_email': None,
            'client_phone': None,
            'company_name': None,
            'company_vat': None,
            'company_address': None,
            'total_amount': None,
            'currency': None,
            'ddt_reference': None,
            'ddt_date': None,
            'ddt_id': None,
            'transmission_id': None,
            'destination_code': None,
            'xml_content': None,
            'invoice_lines': [],
            'vat_summary': [],
            'payment_terms': None,
            'payment_method': None,
            'payment_due_date': None
        }
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Read XML content for preview
            with open(file_path, 'r', encoding='utf-8') as f:
                invoice_details['xml_content'] = f.read()
            
            # Define namespaces for proper XML navigation
            namespaces = {
                'p': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2'
            }
            
            # === 1. EXTRACT TRANSMISSION DATA (DatiTrasmissione) ===
            dati_trasmissione = root.find('.//p:DatiTrasmissione', namespaces)
            if dati_trasmissione is not None:
                progressivo_elem = dati_trasmissione.find('p:ProgressivoInvio', namespaces)
                if progressivo_elem is not None:
                    invoice_details['transmission_id'] = progressivo_elem.text
                    
                codice_dest_elem = dati_trasmissione.find('p:CodiceDestinatario', namespaces)
                if codice_dest_elem is not None:
                    invoice_details['destination_code'] = codice_dest_elem.text
            
            # === 2. EXTRACT COMPANY DATA (CedentePrestatore) ===
            cedente = root.find('.//p:CedentePrestatore', namespaces)
            if cedente is not None:
                # Company VAT and fiscal data
                id_fiscale = cedente.find('.//p:IdFiscaleIVA', namespaces)
                if id_fiscale is not None:
                    id_paese = id_fiscale.find('p:IdPaese', namespaces)
                    id_codice = id_fiscale.find('p:IdCodice', namespaces)
                    if id_paese is not None and id_codice is not None:
                        invoice_details['company_vat'] = f"{id_paese.text}{id_codice.text}"
                
                # Company name
                denominazione = cedente.find('.//p:Denominazione', namespaces)
                if denominazione is not None:
                    invoice_details['company_name'] = denominazione.text
                
                # Company address
                sede = cedente.find('.//p:Sede', namespaces)
                if sede is not None:
                    address_parts = []
                    indirizzo = sede.find('p:Indirizzo', namespaces)
                    cap = sede.find('p:CAP', namespaces)
                    comune = sede.find('p:Comune', namespaces)
                    provincia = sede.find('p:Provincia', namespaces)
                    nazione = sede.find('p:Nazione', namespaces)
                    
                    if indirizzo is not None:
                        address_parts.append(indirizzo.text)
                    if cap is not None and comune is not None:
                        address_parts.append(f"{cap.text} {comune.text}")
                    if provincia is not None:
                        address_parts.append(f"({provincia.text})")
                    if nazione is not None:
                        address_parts.append(nazione.text)
                    
                    invoice_details['company_address'] = ', '.join(address_parts) if address_parts else None
            
            # === 3. EXTRACT CLIENT DATA (CessionarioCommittente) ===
            cessionario = root.find('.//p:CessionarioCommittente', namespaces)
            if cessionario is not None:
                # Client VAT number
                id_fiscale = cessionario.find('.//p:IdFiscaleIVA', namespaces)
                if id_fiscale is not None:
                    id_paese = id_fiscale.find('p:IdPaese', namespaces)
                    id_codice = id_fiscale.find('p:IdCodice', namespaces)
                    if id_paese is not None and id_codice is not None:
                        invoice_details['client_vat'] = f"{id_paese.text}{id_codice.text}"
                
                # Client fiscal code (if different from VAT)
                codice_fiscale = cessionario.find('.//p:CodiceFiscale', namespaces)
                if codice_fiscale is not None:
                    invoice_details['client_fiscal_code'] = codice_fiscale.text
                
                # Client name
                denominazione = cessionario.find('.//p:Denominazione', namespaces)
                if denominazione is not None:
                    invoice_details['client_name'] = denominazione.text
                
                # Client address
                sede = cessionario.find('.//p:Sede', namespaces)
                if sede is not None:
                    address_parts = []
                    indirizzo = sede.find('p:Indirizzo', namespaces)
                    cap = sede.find('p:CAP', namespaces)
                    comune = sede.find('p:Comune', namespaces)
                    provincia = sede.find('p:Provincia', namespaces)
                    nazione = sede.find('p:Nazione', namespaces)
                    
                    if indirizzo is not None:
                        address_parts.append(indirizzo.text)
                    if cap is not None and comune is not None:
                        address_parts.append(f"{cap.text} {comune.text}")
                    if provincia is not None:
                        address_parts.append(f"({provincia.text})")
                    if nazione is not None:
                        address_parts.append(nazione.text)
                    
                    invoice_details['client_address'] = ', '.join(address_parts) if address_parts else None
            
            # === 4. EXTRACT GENERAL DOCUMENT DATA (DatiGenerali) ===
            dati_generali = root.find('.//p:DatiGenerali', namespaces)
            if dati_generali is not None:
                # Invoice basic data
                dati_doc = dati_generali.find('p:DatiGeneraliDocumento', namespaces)
                if dati_doc is not None:
                    # Invoice number
                    numero_elem = dati_doc.find('p:Numero', namespaces)
                    if numero_elem is not None:
                        invoice_details['invoice_number'] = numero_elem.text
                    
                    # Invoice date
                    data_elem = dati_doc.find('p:Data', namespaces)
                    if data_elem is not None:
                        try:
                            invoice_date = datetime.strptime(data_elem.text, '%Y-%m-%d')
                            invoice_details['invoice_date'] = invoice_date.strftime('%d/%m/%Y')
                        except:
                            invoice_details['invoice_date'] = data_elem.text
                    
                    # Currency
                    divisa_elem = dati_doc.find('p:Divisa', namespaces)
                    if divisa_elem is not None:
                        invoice_details['currency'] = divisa_elem.text
                
                # DDT Reference data
                dati_ddt = dati_generali.find('p:DatiDDT', namespaces)
                if dati_ddt is not None:
                    # DDT number
                    numero_ddt_elem = dati_ddt.find('p:NumeroDDT', namespaces)
                    if numero_ddt_elem is not None:
                        invoice_details['ddt_reference'] = numero_ddt_elem.text
                    
                    # DDT date
                    data_ddt_elem = dati_ddt.find('p:DataDDT', namespaces)
                    if data_ddt_elem is not None:
                        try:
                            ddt_date = datetime.strptime(data_ddt_elem.text, '%Y-%m-%d')
                            invoice_details['ddt_date'] = ddt_date.strftime('%d/%m/%Y')
                        except:
                            invoice_details['ddt_date'] = data_ddt_elem.text
            
            # === 5. EXTRACT INVOICE LINES (DettaglioLinee) ===
            invoice_lines = []
            for linea in root.findall('.//p:DettaglioLinee', namespaces):
                line_data = {}
                
                # Line number
                num_elem = linea.find('p:NumeroLinea', namespaces)
                if num_elem is not None:
                    line_data['numero'] = num_elem.text
                
                # Description
                desc_elem = linea.find('p:Descrizione', namespaces)
                if desc_elem is not None:
                    line_data['descrizione'] = desc_elem.text
                
                # Quantity
                qty_elem = linea.find('p:Quantita', namespaces)
                if qty_elem is not None:
                    line_data['quantita'] = qty_elem.text
                
                # Unit of measure
                unit_elem = linea.find('p:UnitaMisura', namespaces)
                if unit_elem is not None:
                    line_data['unita'] = unit_elem.text
                
                # Unit price
                price_elem = linea.find('p:PrezzoUnitario', namespaces)
                if price_elem is not None:
                    line_data['prezzo_unitario'] = price_elem.text
                
                # Total price
                total_elem = linea.find('p:PrezzoTotale', namespaces)
                if total_elem is not None:
                    line_data['prezzo_totale'] = total_elem.text
                
                # VAT rate
                vat_elem = linea.find('p:AliquotaIVA', namespaces)
                if vat_elem is not None:
                    line_data['aliquota_iva'] = vat_elem.text
                
                invoice_lines.append(line_data)
            
            invoice_details['invoice_lines'] = invoice_lines
            
            # === 6. EXTRACT VAT SUMMARY (DatiRiepilogo) ===
            vat_summary = []
            for riepilogo in root.findall('.//p:DatiRiepilogo', namespaces):
                vat_data = {}
                
                # VAT rate
                aliq_elem = riepilogo.find('p:AliquotaIVA', namespaces)
                if aliq_elem is not None:
                    vat_data['aliquota'] = aliq_elem.text
                
                # Taxable amount
                imp_elem = riepilogo.find('p:ImponibileImporto', namespaces)
                if imp_elem is not None:
                    vat_data['imponibile'] = imp_elem.text
                
                # VAT amount
                imposta_elem = riepilogo.find('p:Imposta', namespaces)
                if imposta_elem is not None:
                    vat_data['imposta'] = imposta_elem.text
                
                vat_summary.append(vat_data)
            
            invoice_details['vat_summary'] = vat_summary
            
            # === 7. EXTRACT PAYMENT DATA (DatiPagamento) ===
            dati_pagamento = root.find('.//p:DatiPagamento', namespaces)
            if dati_pagamento is not None:
                # Payment terms
                condizioni_elem = dati_pagamento.find('p:CondizioniPagamento', namespaces)
                if condizioni_elem is not None:
                    payment_terms_map = {
                        'TP01': 'Pagamento a rate',
                        'TP02': 'Pagamento completo',
                        'TP03': 'Anticipo'
                    }
                    invoice_details['payment_terms'] = payment_terms_map.get(condizioni_elem.text, condizioni_elem.text)
                
                # Payment details
                dettaglio = dati_pagamento.find('p:DettaglioPagamento', namespaces)
                if dettaglio is not None:
                    # Payment method
                    modalita_elem = dettaglio.find('p:ModalitaPagamento', namespaces)
                    if modalita_elem is not None:
                        payment_method_map = {
                            'MP01': 'Contanti',
                            'MP02': 'Assegno',
                            'MP03': 'Assegno circolare',
                            'MP04': 'Contanti presso tesoreria',
                            'MP05': 'Bonifico',
                            'MP06': 'Vaglia cambiario',
                            'MP07': 'Bollettino bancario',
                            'MP08': 'Carta di pagamento',
                            'MP09': 'RID',
                            'MP10': 'RID utenze',
                            'MP11': 'RID veloce',
                            'MP12': 'RIBA',
                            'MP13': 'MAV',
                            'MP14': 'Quietanza erario',
                            'MP15': 'Giroconto su conti di contabilità speciale',
                            'MP16': 'Domiciliazione bancaria',
                            'MP17': 'Domiciliazione postale',
                            'MP18': 'Bollettino di c/c postale',
                            'MP19': 'SEPA Direct Debit',
                            'MP20': 'SEPA Direct Debit CORE',
                            'MP21': 'SEPA Direct Debit B2B',
                            'MP22': 'Trattenuta su somme già riscosse'
                        }
                        invoice_details['payment_method'] = payment_method_map.get(modalita_elem.text, modalita_elem.text)
                    
                    # Payment due date
                    scadenza_elem = dettaglio.find('p:DataScadenzaPagamento', namespaces)
                    if scadenza_elem is not None:
                        try:
                            due_date = datetime.strptime(scadenza_elem.text, '%Y-%m-%d')
                            invoice_details['payment_due_date'] = due_date.strftime('%d/%m/%Y')
                        except:
                            invoice_details['payment_due_date'] = scadenza_elem.text
                    
                    # Total payment amount
                    importo_elem = dettaglio.find('p:ImportoPagamento', namespaces)
                    if importo_elem is not None:
                        invoice_details['total_amount'] = importo_elem.text
                    
        except ET.ParseError as e:
            logger.error(f"Error parsing XML for {filename}: {str(e)}")
        
        # === 8. CROSS-REFERENCE WITH DDT DATABASE ===
        if invoice_details['ddt_reference']:
            try:
                ddt = AlbaranCabecera.query.filter_by(NumAlbaran=int(invoice_details['ddt_reference'])).first()
                if ddt:
                    invoice_details['ddt_id'] = ddt.IdAlbaran
                    
                    # Cross-reference client data (use XML as primary, DDT as backup/verification)
                    if not invoice_details['client_email'] and ddt.EmailCliente:
                        invoice_details['client_email'] = ddt.EmailCliente
                    if not invoice_details['client_phone'] and ddt.TelefonoCliente:
                        invoice_details['client_phone'] = ddt.TelefonoCliente
                    
                    # Log any discrepancies for verification
                    if invoice_details['client_name'] and ddt.NombreCliente:
                        if invoice_details['client_name'].strip().lower() != ddt.NombreCliente.strip().lower():
                            logger.warning(f"Client name mismatch for invoice {filename}: XML='{invoice_details['client_name']}' vs DDT='{ddt.NombreCliente}'")
                    
                    # If XML doesn't have client data, use DDT as fallback
                    if not invoice_details['client_name'] and ddt.NombreCliente:
                        invoice_details['client_name'] = ddt.NombreCliente
                        logger.info(f"Using DDT client name as fallback for invoice {filename}")
                        
            except Exception as e:
                logger.error(f"Error cross-referencing DDT data for invoice {filename}: {str(e)}")
        
        return render_template('fattura_pa/detail.html', invoice_details=invoice_details)
        
    except Exception as e:
        logger.error(f"Error loading invoice detail page for {filename}: {str(e)}")
        return render_template('fattura_pa/detail.html', invoice_details=None)

@fattura_pa_bp.route('/xml/<filename>')
@login_required
def get_xml_content(filename):
    """Get XML content for preview"""
    try:
        fatture_dir = os.path.join(current_app.root_path, 'Fatture')
        file_path = os.path.join(fatture_dir, filename)
        
        if not os.path.exists(file_path):
            return "File non trovato", 404
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"Error reading XML content for {filename}: {str(e)}")
        return f"Errore nella lettura del file: {str(e)}", 500

@fattura_pa_bp.route('/download/<filename>')
@login_required
def download_invoice(filename):
    """Download a specific invoice"""
    fatture_dir = os.path.join(current_app.root_path, 'Fatture')
    file_path = os.path.join(fatture_dir, filename)
    
    if not os.path.exists(file_path):
        flash('File non trovato', 'danger')
        return redirect(url_for('fattura_pa.list_invoices'))
        
    with open(file_path, 'rb') as f:
        data = f.read()
        
    return send_file(
        io.BytesIO(data),
        mimetype='application/xml',
        as_attachment=True,
        download_name=filename
    ) 

@fattura_pa_bp.route('/delete/<filename>', methods=['POST'])
@login_required
def delete_invoice(filename):
    """Delete a specific invoice"""
    fatture_dir = os.path.join(current_app.root_path, 'Fatture')
    file_path = os.path.join(fatture_dir, filename)
    
    if not os.path.exists(file_path):
        flash('File non trovato', 'danger')
        return redirect(url_for('fattura_pa.list_invoices'))
        
    try:
        os.remove(file_path)
        flash('Fattura eliminata con successo', 'success')
        return redirect(url_for('fattura_pa.list_invoices'))
    except Exception as e:
        flash(f'Errore durante la cancellazione della fattura: {str(e)}', 'danger')
        return redirect(url_for('fattura_pa.list_invoices'))

@fattura_pa_bp.route('/delete/<filename>', methods=['DELETE'])
@login_required
def delete_invoice_ajax(filename):
    """Delete a specific invoice via AJAX"""
    try:
        fatture_dir = os.path.join(current_app.root_path, 'Fatture')
        file_path = os.path.join(fatture_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'File non trovato'}), 404
            
        # Check if user is admin (additional security)
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Accesso negato'}), 403
            
        os.remove(file_path)
        logger.info(f"Invoice {filename} deleted by user {current_user.username}")
        
        return jsonify({'success': True, 'message': 'Fattura eliminata con successo'})
        
    except Exception as e:
        logger.error(f"Error deleting invoice {filename}: {str(e)}")
        return jsonify({'success': False, 'message': f'Errore durante la cancellazione: {str(e)}'}), 500 