from flask import Blueprint, request, redirect, url_for, flash, send_file, current_app, render_template
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