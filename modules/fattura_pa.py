from flask import Blueprint, request, redirect, url_for, flash, send_file, current_app, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_
from app.models import db, Company, Client, AlbaranCabecera, AlbaranLinea
from datetime import datetime
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io
import logging
import uuid
from services.utils import admin_required

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
            
            # Quantità (peso/quantità dell'articolo)
            quantity = float(line.Peso or 1)
            ET.SubElement(dati_linea, 'Quantita').text = format_decimal(quantity, 2)
            ET.SubElement(dati_linea, 'UnitaMisura').text = line.Medida2 or 'PZ'
            
            # PrezzoUnitario (prezzo unitario senza IVA)
            unit_price = float(line.PrecioSinIVA or 0)
            ET.SubElement(dati_linea, 'PrezzoUnitario').text = format_decimal(unit_price, 8)
            
            # PrezzoTotale = Quantità × PrezzoUnitario (secondo specifiche PA)
            line_total = quantity * unit_price
            # Arrotonda a 2 decimali come richiesto dalle specifiche
            line_total = round(line_total, 2)
            ET.SubElement(dati_linea, 'PrezzoTotale').text = format_decimal(line_total, 2)
            
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
            
            # Add the line amount to the summary (usa il PrezzoTotale calcolato)
            vat_summary[vat_key]['ImponibileImporto'] += line_total
            # Calcola l'imposta: ImponibileImporto × (AliquotaIVA/100)
            vat_summary[vat_key]['Imposta'] = round(vat_summary[vat_key]['ImponibileImporto'] * (vat_rate / 100), 2)
        
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
        
        # Calcola l'ImportoPagamento come somma di ImponibileImporto + Imposta
        total_payment = 0.0
        for vat_data in vat_summary.values():
            total_payment += vat_data['ImponibileImporto'] + vat_data['Imposta']
        
        # Arrotonda il totale del pagamento a 2 decimali
        total_payment = round(total_payment, 2)
        ET.SubElement(dettaglio_pagamento, 'ImportoPagamento').text = format_decimal(total_payment, 2)
        
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
@admin_required
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
@admin_required
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
@admin_required
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
@admin_required
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
            'document_type': None,
            'currency': None,
            'causale': None,
            'total_amount': None,
            'ddt_reference': None,
            'ddt_date': None,
            'ddt_id': None,
            
            # Company data (CedentePrestatore)
            'company_name': None,
            'company_vat': None,
            'company_fiscal_code': None,
            'company_address': None,
            'company_cap': None,
            'company_city': None,
            'company_province': None,
            'company_country': None,
            'company_regime': None,
            
            # Client data (CessionarioCommittente)
            'client_name': None,
            'client_vat': None,
            'client_fiscal_code': None,
            'client_address': None,
            'client_cap': None,
            'client_city': None,
            'client_province': None,
            'client_country': None,
            'client_email': None,
            'client_phone': None,
            
            # Transmission data (DatiTrasmissione)
            'transmission_id': None,
            'transmission_format': None,
            'destination_code': None,
            'pec_destination': None,
            
            # Payment data
            'payment_conditions': None,
            'payment_method': None,
            'payment_due_date': None,
            'payment_amount': None,
            'iban': None,
            
            'xml_content': None,
            'invoice_lines': [],
            'vat_summary': [],
            'ddt_data': None
        }
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Read XML content for preview
            with open(file_path, 'r', encoding='utf-8') as f:
                invoice_details['xml_content'] = f.read()
            
            # Define namespaces
            namespaces = {
                'p': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2'
            }
            
            # === HEADER DATA ===
            header = root.find('.//FatturaElettronicaHeader', namespaces)
            if header is not None:
                
                # === DatiTrasmissione ===
                dati_trasmissione = header.find('DatiTrasmissione', namespaces)
                if dati_trasmissione is not None:
                    # Transmission ID
                    prog_elem = dati_trasmissione.find('ProgressivoInvio', namespaces)
                    if prog_elem is not None:
                        invoice_details['transmission_id'] = prog_elem.text
                    
                    # Format
                    format_elem = dati_trasmissione.find('FormatoTrasmissione', namespaces)
                    if format_elem is not None:
                        invoice_details['transmission_format'] = format_elem.text
                    
                    # Destination code
                    dest_elem = dati_trasmissione.find('CodiceDestinatario', namespaces)
                    if dest_elem is not None:
                        invoice_details['destination_code'] = dest_elem.text
                    
                    # PEC destination
                    pec_elem = dati_trasmissione.find('PECDestinatario', namespaces)
                    if pec_elem is not None:
                        invoice_details['pec_destination'] = pec_elem.text
                
                # === CedentePrestatore (Company data) ===
                cedente = header.find('CedentePrestatore', namespaces)
                if cedente is not None:
                    # Dati Anagrafici
                    dati_anag = cedente.find('DatiAnagrafici', namespaces)
                    if dati_anag is not None:
                        # VAT
                        id_fiscale = dati_anag.find('IdFiscaleIVA', namespaces)
                        if id_fiscale is not None:
                            paese_elem = id_fiscale.find('IdPaese', namespaces)
                            codice_elem = id_fiscale.find('IdCodice', namespaces)
                            if paese_elem is not None and codice_elem is not None:
                                invoice_details['company_vat'] = f"{paese_elem.text}{codice_elem.text}"
                        
                        # Fiscal Code
                        cf_elem = dati_anag.find('CodiceFiscale', namespaces)
                        if cf_elem is not None:
                            invoice_details['company_fiscal_code'] = cf_elem.text
                        
                        # Company name
                        anagrafica = dati_anag.find('Anagrafica', namespaces)
                        if anagrafica is not None:
                            denom_elem = anagrafica.find('Denominazione', namespaces)
                            if denom_elem is not None:
                                invoice_details['company_name'] = denom_elem.text
                        
                        # Regime fiscale
                        regime_elem = dati_anag.find('RegimeFiscale', namespaces)
                        if regime_elem is not None:
                            invoice_details['company_regime'] = regime_elem.text
                    
                    # Sede
                    sede = cedente.find('Sede', namespaces)
                    if sede is not None:
                        addr_elem = sede.find('Indirizzo', namespaces)
                        if addr_elem is not None:
                            invoice_details['company_address'] = addr_elem.text
                        
                        cap_elem = sede.find('CAP', namespaces)
                        if cap_elem is not None:
                            invoice_details['company_cap'] = cap_elem.text
                        
                        comune_elem = sede.find('Comune', namespaces)
                        if comune_elem is not None:
                            invoice_details['company_city'] = comune_elem.text
                        
                        prov_elem = sede.find('Provincia', namespaces)
                        if prov_elem is not None:
                            invoice_details['company_province'] = prov_elem.text
                        
                        nazione_elem = sede.find('Nazione', namespaces)
                        if nazione_elem is not None:
                            invoice_details['company_country'] = nazione_elem.text
                
                # === CessionarioCommittente (Client data) ===
                cessionario = header.find('CessionarioCommittente', namespaces)
                if cessionario is not None:
                    # Dati Anagrafici
                    dati_anag = cessionario.find('DatiAnagrafici', namespaces)
                    if dati_anag is not None:
                        # VAT
                        id_fiscale = dati_anag.find('IdFiscaleIVA', namespaces)
                        if id_fiscale is not None:
                            paese_elem = id_fiscale.find('IdPaese', namespaces)
                            codice_elem = id_fiscale.find('IdCodice', namespaces)
                            if paese_elem is not None and codice_elem is not None:
                                invoice_details['client_vat'] = f"{paese_elem.text}{codice_elem.text}"
                        
                        # Fiscal Code
                        cf_elem = dati_anag.find('CodiceFiscale', namespaces)
                        if cf_elem is not None:
                            invoice_details['client_fiscal_code'] = cf_elem.text
                        
                        # Client name
                        anagrafica = dati_anag.find('Anagrafica', namespaces)
                        if anagrafica is not None:
                            denom_elem = anagrafica.find('Denominazione', namespaces)
                            if denom_elem is not None:
                                invoice_details['client_name'] = denom_elem.text
                    
                    # Sede
                    sede = cessionario.find('Sede', namespaces)
                    if sede is not None:
                        addr_elem = sede.find('Indirizzo', namespaces)
                        if addr_elem is not None:
                            invoice_details['client_address'] = addr_elem.text
                        
                        cap_elem = sede.find('CAP', namespaces)
                        if cap_elem is not None:
                            invoice_details['client_cap'] = cap_elem.text
                        
                        comune_elem = sede.find('Comune', namespaces)
                        if comune_elem is not None:
                            invoice_details['client_city'] = comune_elem.text
                        
                        prov_elem = sede.find('Provincia', namespaces)
                        if prov_elem is not None:
                            invoice_details['client_province'] = prov_elem.text
                        
                        nazione_elem = sede.find('Nazione', namespaces)
                        if nazione_elem is not None:
                            invoice_details['client_country'] = nazione_elem.text
                    
                    # Contatti (email, phone)
                    contatti = cessionario.find('Contatti', namespaces)
                    if contatti is not None:
                        email_elem = contatti.find('Email', namespaces)
                        if email_elem is not None:
                            invoice_details['client_email'] = email_elem.text
                        
                        tel_elem = contatti.find('Telefono', namespaces)
                        if tel_elem is not None:
                            invoice_details['client_phone'] = tel_elem.text
            
            # === BODY DATA ===
            body = root.find('.//FatturaElettronicaBody', namespaces)
            if body is not None:
                
                # === DatiGenerali ===
                dati_generali = body.find('DatiGenerali', namespaces)
                if dati_generali is not None:
                    
                    # DatiGeneraliDocumento
                    dati_gen_doc = dati_generali.find('DatiGeneraliDocumento', namespaces)
                    if dati_gen_doc is not None:
                        # Document type
                        tipo_elem = dati_gen_doc.find('TipoDocumento', namespaces)
                        if tipo_elem is not None:
                            invoice_details['document_type'] = tipo_elem.text
                        
                        # Currency
                        divisa_elem = dati_gen_doc.find('Divisa', namespaces)
                        if divisa_elem is not None:
                            invoice_details['currency'] = divisa_elem.text
                        
                        # Invoice date
                        data_elem = dati_gen_doc.find('Data', namespaces)
                        if data_elem is not None:
                            try:
                                invoice_date = datetime.strptime(data_elem.text, '%Y-%m-%d')
                                invoice_details['invoice_date'] = invoice_date.strftime('%d/%m/%Y')
                            except:
                                invoice_details['invoice_date'] = data_elem.text
                        
                        # Invoice number
                        numero_elem = dati_gen_doc.find('Numero', namespaces)
                        if numero_elem is not None:
                            invoice_details['invoice_number'] = numero_elem.text
                        
                        # Causale
                        causale_elem = dati_gen_doc.find('Causale', namespaces)
                        if causale_elem is not None:
                            invoice_details['causale'] = causale_elem.text
                    
                    # DatiDDT
                    dati_ddt = dati_generali.find('DatiDDT', namespaces)
                    if dati_ddt is not None:
                        # DDT number
                        num_ddt_elem = dati_ddt.find('NumeroDDT', namespaces)
                        if num_ddt_elem is not None:
                            invoice_details['ddt_reference'] = num_ddt_elem.text
                        
                        # DDT date
                        data_ddt_elem = dati_ddt.find('DataDDT', namespaces)
                        if data_ddt_elem is not None:
                            try:
                                ddt_date = datetime.strptime(data_ddt_elem.text, '%Y-%m-%d')
                                invoice_details['ddt_date'] = ddt_date.strftime('%d/%m/%Y')
                            except:
                                invoice_details['ddt_date'] = data_ddt_elem.text
                
                # === DatiBeniServizi (Invoice Lines) ===
                dati_beni = body.find('DatiBeniServizi', namespaces)
                if dati_beni is not None:
                    
                    # Extract invoice lines
                    invoice_lines = []
                    for linea in dati_beni.findall('DettaglioLinee', namespaces):
                        line_data = {}
                        
                        num_elem = linea.find('NumeroLinea', namespaces)
                        desc_elem = linea.find('Descrizione', namespaces)
                        qty_elem = linea.find('Quantita', namespaces)
                        unit_elem = linea.find('UnitaMisura', namespaces)
                        price_elem = linea.find('PrezzoUnitario', namespaces)
                        total_elem = linea.find('PrezzoTotale', namespaces)
                        vat_elem = linea.find('AliquotaIVA', namespaces)
                        
                        if num_elem is not None:
                            line_data['numero'] = num_elem.text
                        if desc_elem is not None:
                            line_data['descrizione'] = desc_elem.text
                        if qty_elem is not None:
                            line_data['quantita'] = qty_elem.text
                        if unit_elem is not None:
                            line_data['unita'] = unit_elem.text
                        if price_elem is not None:
                            line_data['prezzo_unitario'] = price_elem.text
                        if total_elem is not None:
                            line_data['prezzo_totale'] = total_elem.text
                        if vat_elem is not None:
                            line_data['aliquota_iva'] = vat_elem.text
                            
                        invoice_lines.append(line_data)
                    
                    invoice_details['invoice_lines'] = invoice_lines
                    
                    # Extract VAT summary
                    vat_summary = []
                    for riepilogo in dati_beni.findall('DatiRiepilogo', namespaces):
                        vat_data = {}
                        
                        aliq_elem = riepilogo.find('AliquotaIVA', namespaces)
                        imp_elem = riepilogo.find('ImponibileImporto', namespaces)
                        imposta_elem = riepilogo.find('Imposta', namespaces)
                        esig_elem = riepilogo.find('EsigibilitaIVA', namespaces)
                        
                        if aliq_elem is not None:
                            vat_data['aliquota'] = aliq_elem.text
                        if imp_elem is not None:
                            vat_data['imponibile'] = imp_elem.text
                        if imposta_elem is not None:
                            vat_data['imposta'] = imposta_elem.text
                        if esig_elem is not None:
                            vat_data['esigibilita'] = esig_elem.text
                            
                        vat_summary.append(vat_data)
                    
                    invoice_details['vat_summary'] = vat_summary
                
                # === DatiPagamento (Payment data) ===
                dati_pagamento = body.find('DatiPagamento', namespaces)
                if dati_pagamento is not None:
                    # Payment conditions
                    cond_elem = dati_pagamento.find('CondizioniPagamento', namespaces)
                    if cond_elem is not None:
                        invoice_details['payment_conditions'] = cond_elem.text
                    
                    # Payment details
                    dettaglio_pag = dati_pagamento.find('DettaglioPagamento', namespaces)
                    if dettaglio_pag is not None:
                        # Payment method
                        modal_elem = dettaglio_pag.find('ModalitaPagamento', namespaces)
                        if modal_elem is not None:
                            invoice_details['payment_method'] = modal_elem.text
                        
                        # Due date
                        scad_elem = dettaglio_pag.find('DataScadenzaPagamento', namespaces)
                        if scad_elem is not None:
                            try:
                                due_date = datetime.strptime(scad_elem.text, '%Y-%m-%d')
                                invoice_details['payment_due_date'] = due_date.strftime('%d/%m/%Y')
                            except:
                                invoice_details['payment_due_date'] = scad_elem.text
                        
                        # Payment amount
                        imp_pag_elem = dettaglio_pag.find('ImportoPagamento', namespaces)
                        if imp_pag_elem is not None:
                            invoice_details['payment_amount'] = imp_pag_elem.text
                            invoice_details['total_amount'] = imp_pag_elem.text  # Also set total_amount
                        
                        # IBAN
                        iban_elem = dettaglio_pag.find('IBAN', namespaces)
                        if iban_elem is not None:
                            invoice_details['iban'] = iban_elem.text
                            
            # Try to get DDT data from database if we have the DDT reference
            if invoice_details['ddt_reference']:
                try:
                    # Search for DDT by number and date if available
                    ddt_search_filters = [AlbaranCabecera.NumAlbaran == int(invoice_details['ddt_reference'])]
                    
                    # If we have DDT date, add it to search filters for more precision
                    if invoice_details['ddt_date']:
                        try:
                            # Convert DDT date to search for matching date
                            ddt_date_search = datetime.strptime(invoice_details['ddt_date'], '%d/%m/%Y').date()
                            ddt_search_filters.append(db.func.date(AlbaranCabecera.Fecha) == ddt_date_search)
                        except:
                            logger.warning(f"Could not parse DDT date {invoice_details['ddt_date']} for precise search")
                    
                    # Find the DDT
                    ddt = AlbaranCabecera.query.filter(*ddt_search_filters).first()
                    
                    if ddt:
                        logger.info(f"Found DDT {ddt.NumAlbaran} (ID: {ddt.IdAlbaran}) for invoice {filename}")
                        invoice_details['ddt_id'] = ddt.IdAlbaran
                        
                        # === EXTRACT COMPLETE DDT DATA ===
                        invoice_details['ddt_data'] = {
                            # DDT Header Information
                            'header': {
                                'id_albaran': ddt.IdAlbaran,
                                'num_albaran': ddt.NumAlbaran,
                                'fecha': ddt.Fecha.strftime('%d/%m/%Y %H:%M') if ddt.Fecha else None,
                                'fecha_modificacion': ddt.FechaModificacion.strftime('%d/%m/%Y %H:%M') if ddt.FechaModificacion else None,
                                'tipo': ddt.Tipo,
                                'estado_ticket': ddt.EstadoTicket,
                                'enviado': ddt.Enviado,
                                'usuario': ddt.Usuario,
                                'referencia_documento': ddt.ReferenciaDocumento,
                                'observaciones_documento': ddt.ObservacionesDocumento,
                                'codigo_barras': ddt.CodigoBarras,
                                'num_lineas': ddt.NumLineas
                            },
                            
                            # Company Information (from DDT)
                            'company': {
                                'id_empresa': ddt.IdEmpresa,
                                'nombre_empresa': ddt.NombreEmpresa,
                                'cif_vat': ddt.CIF_VAT_Empresa,
                                'direccion': ddt.DireccionEmpresa,
                                'poblacion': ddt.PoblacionEmpresa,
                                'cp': ddt.CPEmpresa,
                                'telefono': ddt.TelefonoEmpresa,
                                'provincia': ddt.ProvinciaEmpresa,
                                'nombre_tienda': ddt.NombreTienda,
                                'nombre_balanza_maestra': ddt.NombreBalanzaMaestra,
                                'nombre_balanza_esclava': ddt.NombreBalanzaEsclava
                            },
                            
                            # Client Information (from DDT)
                            'client': {
                                'id_cliente': ddt.IdCliente,
                                'nombre_cliente': ddt.NombreCliente,
                                'dni_cliente': ddt.DNICliente,
                                'email_cliente': ddt.EmailCliente,
                                'direccion_cliente': ddt.DireccionCliente,
                                'poblacion_cliente': ddt.PoblacionCliente,
                                'provincia_cliente': ddt.ProvinciaCliente,
                                'pais_cliente': ddt.PaisCliente,
                                'cp_cliente': ddt.CPCliente,
                                'telefono_cliente': ddt.TelefonoCliente,
                                'observaciones_cliente': ddt.ObservacionesCliente,
                                'ean_cliente': ddt.EANCliente
                            },
                            
                            # Vendor Information (from DDT)
                            'vendor': {
                                'id_vendedor': ddt.IdVendedor,
                                'nombre_vendedor': ddt.NombreVendedor
                            },
                            
                            # Financial Totals (from DDT)
                            'totals': {
                                'importe_lineas': float(ddt.ImporteLineas) if ddt.ImporteLineas else 0,
                                'porc_descuento': float(ddt.PorcDescuento) if ddt.PorcDescuento else 0,
                                'importe_descuento': float(ddt.ImporteDescuento) if ddt.ImporteDescuento else 0,
                                'importe_re': float(ddt.ImporteRE) if ddt.ImporteRE else 0,
                                'importe_total_sin_re': float(ddt.ImporteTotalSinRE) if ddt.ImporteTotalSinRE else 0,
                                'importe_total_sin_iva_con_dto': float(ddt.ImporteTotalSinIVAConDtoLConDtoTotal) if ddt.ImporteTotalSinIVAConDtoLConDtoTotal else 0,
                                'importe_total_del_iva': float(ddt.ImporteTotalDelIVAConDtoLConDtoTotal) if ddt.ImporteTotalDelIVAConDtoLConDtoTotal else 0,
                                'importe_total': float(ddt.ImporteTotal) if ddt.ImporteTotal else 0,
                                'importe_sin_redondeo': float(ddt.ImporteSinRedondeo) if ddt.ImporteSinRedondeo else 0,
                                'importe_del_redondeo': float(ddt.ImporteDelRedondeo) if ddt.ImporteDelRedondeo else 0
                            },
                            
                            # DDT Lines (Products)
                            'lines': [],
                            
                            # Transport and Tariff Information
                            'transport': {
                                'id_tarifa': ddt.IdTarifa,
                                'nombre_tarifa': ddt.NombreTarifa,
                                'descuento_tarifa': float(ddt.DescuentoTarifa) if ddt.DescuentoTarifa else 0,
                                'tipo_tarifa': ddt.TipoTarifa,
                                'fecha_inicio_tarifa': ddt.FechaInicioTarifa.strftime('%d/%m/%Y') if ddt.FechaInicioTarifa else None,
                                'fecha_fin_tarifa': ddt.FechaFinTarifa.strftime('%d/%m/%Y') if ddt.FechaFinTarifa else None
                            }
                        }
                        
                        # === GET DDT LINES (PRODUCTS) ===
                        ddt_lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt.IdAlbaran).all()
                        
                        lines_data = []
                        for line in ddt_lines:
                            line_data = {
                                'id_linea_albaran': line.IdLineaAlbaran,
                                'id_ticket': line.IdTicket,
                                'id_articulo': line.IdArticulo,
                                'descripcion': line.Descripcion,
                                'descripcion1': line.Descripcion1,
                                'comportamiento': line.Comportamiento,
                                'entrada_manual': line.EntradaManual,
                                'peso': float(line.Peso) if line.Peso else 0,
                                'peso_bruto': float(line.PesoBruto) if line.PesoBruto else 0,
                                'cantidad2': float(line.Cantidad2) if line.Cantidad2 else 0,
                                'medida2': line.Medida2,
                                'precio': float(line.Precio) if line.Precio else 0,
                                'precio_sin_iva': float(line.PrecioSinIVA) if line.PrecioSinIVA else 0,
                                'porcentaje_iva': float(line.PorcentajeIVA) if line.PorcentajeIVA else 0,
                                'recargo_equivalencia': float(line.RecargoEquivalencia) if line.RecargoEquivalencia else 0,
                                'descuento': float(line.Descuento) if line.Descuento else 0,
                                'tipo_descuento': line.TipoDescuento,
                                'importe': float(line.Importe) if line.Importe else 0,
                                'importe_sin_iva_sin_dtol': float(line.ImporteSinIVASinDtoL) if line.ImporteSinIVASinDtoL else 0,
                                'importe_sin_iva_con_dtol': float(line.ImporteSinIVAConDtoL) if line.ImporteSinIVAConDtoL else 0,
                                'importe_del_iva_con_dtol': float(line.ImporteDelIVAConDtoL) if line.ImporteDelIVAConDtoL else 0,
                                'importe_del_re': float(line.ImporteDelRE) if line.ImporteDelRE else 0,
                                'importe_del_descuento': float(line.ImporteDelDescuento) if line.ImporteDelDescuento else 0,
                                'tara': float(line.Tara) if line.Tara else 0,
                                'tara_fija': float(line.TaraFija) if line.TaraFija else 0,
                                'tara_porcentual': float(line.TaraPorcentual) if line.TaraPorcentual else 0,
                                'detalle_tara': line.DetalleTara,
                                'fecha_caducidad': line.FechaCaducidad.strftime('%d/%m/%Y') if line.FechaCaducidad else None,
                                'fecha_envasado': line.FechaEnvasado.strftime('%d/%m/%Y') if line.FechaEnvasado else None,
                                'fecha_fabricacion': line.FechaFabricacion.strftime('%d/%m/%Y') if line.FechaFabricacion else None,
                                'texto_lote': line.TextoLote,
                                'ean_scanner_articulo': line.EANScannerArticulo,
                                'id_clase': line.IdClase,
                                'nombre_clase': line.NombreClase,
                                'id_familia': line.IdFamilia,
                                'nombre_familia': line.NombreFamilia,
                                'id_seccion': line.IdSeccion,
                                'nombre_seccion': line.NombreSeccion,
                                'id_sub_familia': line.IdSubFamilia,
                                'nombre_sub_familia': line.NombreSubFamilia,
                                'id_departamento': line.IdDepartamento,
                                'nombre_departamento': line.NombreDepartamento,
                                'texto1': line.Texto1,
                                'texto_libre': line.TextoLibre,
                                'peso_pieza': float(line.PesoPieza) if line.PesoPieza else 0,
                                'unidades_caja': line.UnidadesCaja,
                                'facturada': line.Facturada,
                                'cantidad_facturada': float(line.CantidadFacturada) if line.CantidadFacturada else 0,
                                'id_campania': line.IdCampania,
                                'nombre_campania': line.NombreCampania,
                                'producto_en_promocion': line.ProductoEnPromocion,
                                'nombre_plataforma': line.NombrePlataforma,
                                'hay_tara_aplicada': line.HayTaraAplicada
                            }
                            lines_data.append(line_data)
                        
                        invoice_details['ddt_data']['lines'] = lines_data
                        
                        logger.info(f"Retrieved {len(lines_data)} lines for DDT {ddt.NumAlbaran}")
                        
                        # === SUMMARY STATISTICS ===
                        invoice_details['ddt_data']['statistics'] = {
                            'total_lines': len(lines_data),
                            'total_products': len(set(line['id_articulo'] for line in lines_data if line['id_articulo'])),
                            'total_weight': sum(line['peso'] for line in lines_data),
                            'total_amount_no_vat': sum(line['importe_sin_iva_con_dtol'] for line in lines_data),
                            'total_vat': sum(line['importe_del_iva_con_dtol'] for line in lines_data),
                            'total_amount': sum(line['importe'] for line in lines_data),
                            'unique_tickets': len(set(line['id_ticket'] for line in lines_data if line['id_ticket']))
                        }
                        
                    else:
                        logger.warning(f"DDT with number {invoice_details['ddt_reference']} not found in database")
                        invoice_details['ddt_data'] = None
                        
                except Exception as e:
                    logger.error(f"Error fetching DDT data for invoice {filename}: {str(e)}")
                    invoice_details['ddt_data'] = None
            
            return render_template('fattura_pa/detail.html', invoice_details=invoice_details)
        
        except ET.ParseError as e:
            logger.error(f"Error parsing XML for {filename}: {str(e)}")
        
        return render_template('fattura_pa/detail.html', invoice_details=invoice_details)
        
    except Exception as e:
        logger.error(f"Error loading invoice detail page for {filename}: {str(e)}")
        return render_template('fattura_pa/detail.html', invoice_details=None)

@fattura_pa_bp.route('/xml/<filename>')
@login_required
@admin_required
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
@admin_required
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
@admin_required
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
@admin_required
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

@fattura_pa_bp.route('/test/<filename>')
@login_required
@admin_required
def test_invoice_parsing(filename):
    """Test route to debug XML parsing - shows all extracted data"""
    try:
        fatture_dir = os.path.join(current_app.root_path, 'Fatture')
        file_path = os.path.join(fatture_dir, filename)
        
        if not os.path.exists(file_path):
            return f"File {filename} not found", 404
        
        # Parse XML and extract all data
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Define namespaces
        namespaces = {
            'p': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2'
        }
        
        result = {
            'filename': filename,
            'xml_structure': [],
            'extracted_data': {}
        }
        
        # Show XML structure
        def analyze_element(elem, level=0):
            indent = "  " * level
            tag_name = elem.tag.replace('{http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2}', 'p:')
            text = elem.text.strip() if elem.text and elem.text.strip() else ''
            result['xml_structure'].append(f"{indent}{tag_name}: {text}")
            
            for child in elem:
                analyze_element(child, level + 1)
        
        analyze_element(root)
        
        # Extract specific data
        header = root.find('.//FatturaElettronicaHeader', namespaces)
        if header is not None:
            result['extracted_data']['header_found'] = True
            
            # DatiTrasmissione
            dati_trasmissione = header.find('DatiTrasmissione', namespaces)
            if dati_trasmissione is not None:
                result['extracted_data']['dati_trasmissione'] = {}
                for elem in dati_trasmissione:
                    tag = elem.tag.replace('{http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2}', '')
                    result['extracted_data']['dati_trasmissione'][tag] = elem.text
            
            # CedentePrestatore
            cedente = header.find('CedentePrestatore', namespaces)
            if cedente is not None:
                result['extracted_data']['cedente_prestatore'] = {}
                # Recursively extract all sub-elements
                def extract_all_children(elem, parent_dict):
                    for child in elem:
                        tag = child.tag.replace('{http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2}', '')
                        if len(child) > 0:
                            parent_dict[tag] = {}
                            extract_all_children(child, parent_dict[tag])
                        else:
                            parent_dict[tag] = child.text
                
                extract_all_children(cedente, result['extracted_data']['cedente_prestatore'])
            
            # CessionarioCommittente
            cessionario = header.find('CessionarioCommittente', namespaces)
            if cessionario is not None:
                result['extracted_data']['cessionario_committente'] = {}
                extract_all_children(cessionario, result['extracted_data']['cessionario_committente'])
        
        # Body data
        body = root.find('.//FatturaElettronicaBody', namespaces)
        if body is not None:
            result['extracted_data']['body_found'] = True
            
            # DatiGenerali
            dati_generali = body.find('DatiGenerali', namespaces)
            if dati_generali is not None:
                result['extracted_data']['dati_generali'] = {}
                extract_all_children(dati_generali, result['extracted_data']['dati_generali'])
            
            # DatiBeniServizi
            dati_beni = body.find('DatiBeniServizi', namespaces)
            if dati_beni is not None:
                result['extracted_data']['dati_beni_servizi'] = {}
                
                # Count lines
                linee = dati_beni.findall('DettaglioLinee', namespaces)
                result['extracted_data']['dati_beni_servizi']['numero_linee'] = len(linee)
                
                # Extract first line as example
                if linee:
                    result['extracted_data']['dati_beni_servizi']['prima_linea'] = {}
                    extract_all_children(linee[0], result['extracted_data']['dati_beni_servizi']['prima_linea'])
                
                # Count VAT summaries
                riepiloghi = dati_beni.findall('DatiRiepilogo', namespaces)
                result['extracted_data']['dati_beni_servizi']['numero_riepiloghi_iva'] = len(riepiloghi)
            
            # DatiPagamento
            dati_pagamento = body.find('DatiPagamento', namespaces)
            if dati_pagamento is not None:
                result['extracted_data']['dati_pagamento'] = {}
                extract_all_children(dati_pagamento, result['extracted_data']['dati_pagamento'])
        
        # Return JSON response for easy reading
        import json
        
        # Prepare data for HTML template (avoid backslashes in f-strings)
        json_data = json.dumps(result['extracted_data'], indent=2, ensure_ascii=False)
        xml_structure_text = "\n".join(result['xml_structure'][:100])
        more_lines_text = ""
        if len(result['xml_structure']) > 100:
            more_lines_text = f"<p>... and {len(result['xml_structure']) - 100} more lines</p>"
        
        return f"""
        <html>
        <head>
            <title>Test Parsing XML - {filename}</title>
            <style>
                body {{ font-family: monospace; margin: 20px; }}
                .section {{ margin: 20px 0; padding: 10px; border: 1px solid #ccc; }}
                .json {{ background: #f5f5f5; padding: 10px; white-space: pre-wrap; }}
                .xml {{ background: #e8f4f8; padding: 10px; white-space: pre; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h1>Test Parsing XML: {filename}</h1>
            
            <div class="section">
                <h2>Extracted Data (JSON)</h2>
                <div class="json">{json_data}</div>
            </div>
            
            <div class="section">
                <h2>XML Structure</h2>
                <div class="xml">{xml_structure_text}</div>
                {more_lines_text}
            </div>
            
            <a href="/fattura_pa/detail/{filename}">View Detail Page</a> |
            <a href="/fattura_pa/list">Back to List</a>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"Error parsing {filename}: {str(e)}", 500 