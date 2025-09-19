from flask import Blueprint, request, redirect, url_for, flash, send_file, current_app, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_
from app.models import db, Company, Client, AlbaranCabecera, AlbaranLinea, FatturaCabecera, FatturaLinea, Article
from datetime import datetime, timedelta
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
fattura_pa_bp = Blueprint('fattura_pa', __name__, url_prefix='/fattura_pa')

# Constants
NAMESPACE_MAP = {
    '': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2',
    'ds': 'http://www.w3.org/2000/09/xmldsig#',
    'p': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

# Helper functions
def get_next_invoice_number():
    """Ottiene il prossimo numero di fattura come intero progressivo"""
    try:
        last_fattura = FatturaCabecera.query.order_by(FatturaCabecera.NumFactura.desc()).first()
        if last_fattura and last_fattura.NumFactura:
            try:
                last_num = int(last_fattura.NumFactura)
                return last_num + 1
            except (ValueError, TypeError):
                pass
        return 1
    except Exception as e:
        logger.error(f"Errore nel calcolo del prossimo numero fattura: {str(e)}")
        return 1

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

def save_fattura_to_db(invoice_data, xml_filename, xml_path, ddt_reference=None):
    """Salva la fattura nel database utilizzando le tabelle esistenti dat_factura_cabecera e dat_factura_linea"""
    try:
        company = invoice_data['company']
        client = invoice_data['client']
        lines = invoice_data['lines']
        note = invoice_data.get('note', '')
        date = invoice_data.get('date', datetime.now())
        
        # Calcola i totali
        importo_linee = 0.0
        importo_iva = 0.0
        
        for line in lines:
            line_total = float(line.get('prezzo_totale', 0))
            vat_rate = float(line.get('aliquota_iva', 0))
            line_vat = line_total * (vat_rate / 100)
            
            importo_linee += line_total
            importo_iva += line_vat
        
        importo_totale = importo_linee + importo_iva
        
        # Ottiene il prossimo numero fattura
        next_num = get_next_invoice_number()
        
        # Crea il record fattura usando la struttura corretta (completando tutti i campi come nel CSV)
        fattura = FatturaCabecera(
            NumFactura=str(next_num)[:20],  # varchar(20) constraint
            IdEmpresa=company.IdEmpresa,
            NombreEmpresa=(company.NombreEmpresa or '')[:100],  # varchar(100) constraint
            CIF_VAT_Empresa=(company.CIF_VAT or '')[:14],  # varchar(14) constraint
            DireccionEmpresa=(company.Direccion or '')[:50],  # varchar(50) constraint
            PoblacionEmpresa=(company.Poblacion or '')[:25],  # varchar(25) constraint
            CPEmpresa=(company.CodPostal or '')[:8],  # varchar(8) constraint
            TelefonoEmpresa=(company.Telefono1 or '')[:20],  # varchar(20) constraint
            ProvinciaEmpresa=(company.Provincia or '')[:25],  # varchar(25) constraint
            AuditFileVersion="",  # Vuoto come nel CSV
            
            # Dati tienda (dal CSV di esempio)
            IdTienda=1,
            NombreTienda="LAB",  # Come nel CSV di esempio
            IdTiendaCreacion=1,
            NombreTiendaCreacion="LAB",  # Come nel CSV di esempio
            IdBalanzaMaestra=1,
            NombreBalanzaMaestra="1",  # Come nel CSV di esempio
            IdBalanzaEsclava=-1,
            NombreBalanzaEsclava="",  # Vuoto come nel CSV
            
            # Venditore (dal CSV di esempio)
            IdVendedor=1,
            NombreVendedor="DDT 1",  # Come nel CSV di esempio
            
            # Dati cliente
            IdCliente=client.IdCliente,
            NombreCliente=(client.Nombre or '')[:50],  # varchar(50) constraint
            DNICliente=(client.DNI or '')[:30],  # varchar(30) constraint
            EmailCliente=(client.Email or '')[:100],  # varchar(100) constraint
            DireccionCliente=(client.Direccion or '')[:50],  # varchar(50) constraint
            PoblacionCliente=(client.Poblacion or '')[:25],  # varchar(25) constraint
            ProvinciaCliente=(client.Provincia or '')[:25],  # varchar(25) constraint
            PaisCliente=(client.Pais or 'AL')[:10],  # Default 'AL' come nel CSV
            CPCliente=(client.CodPostal or '')[:8],  # varchar(8) constraint
            TelefonoCliente=(client.Telefono1 or '')[:20],  # varchar(20) constraint
            ObservacionesCliente=client.Observaciones,  # TEXT field, no truncation needed
            EANCliente=(getattr(client, 'EANScanner', None) or "TEST")[:50],  # Campo dal cliente, default "TEST"
            
            # Riferimenti documento
            ReferenciaDocumento=xml_filename[:50],  # varchar(50) constraint
            ObservacionesDocumento=note,
            
            # Pagamento (dal CSV di esempio)
            DtoProntoPago=None,  # Vuoto nel CSV
            NumeroVencimientos=1,  # Default 1
            DiasEntreVencimientos=0,  # Default 0
            TotalPorArticulo=0,  # Default 0 come nel CSV
            
            # Importi (popolando tutti i campi come nel CSV)
            ImporteLineas=round(importo_linee, 2),
            PorcDescuento=0.000,  # Default 0
            ImporteDescuento=round(0.000, 3),  # Default 0
            ImporteDescuentoPP=round(0.000, 3),  # Default 0
            ImporteTotalConDtoTotal=round(importo_linee, 2),
            ImporteTotalConDtoTotalConDtoPP=round(importo_linee, 2),
            ImporteRE=round(0.000, 3),  # Default 0
            ImporteTotalSinRE=round(importo_totale, 2),
            ImporteTotalSinIVAConDtoL=round(importo_linee, 2),
            ImporteTotalSinIVAConDtoLConDtoTotalConDtoPPConRE=round(importo_linee, 2),
            ImporteTotalSinIVAConDtoLConDtoTotalConDtoPP=round(importo_linee, 2),
            ImporteTotalSinIVAConDtoLConDtoTotal=round(importo_linee, 2),
            ImporteDtoTotalSinIVA=round(0.000, 3),  # Default 0
            ImporteTotalDelIVAConDtoLConDtoTotal=round(importo_iva, 2),
            ImporteTotalDelIVAConDtoLConDtoTotalConDtoPP=round(importo_iva, 2),
            ImporteSinRedondeo=round(importo_totale, 2),
            ImporteDelRedondeo=round(0.000, 3),  # Default 0
            
            # Date
            Fecha=datetime.now(),
            FechaOperacion=datetime.now().date(),
            FechaAnulacion=None,
            
            # Riferimenti originali
            IdFactura_Original=None,
            NumFactura_Original=None,
            MotivoAnulacion=None,
            
            # Tipo fattura (dal CSV di esempio)
            Tipo='F' if not ddt_reference else '24',  # 'F' normale, '24' differita
            
            FechaModificacion=datetime.now(),
            NumLineas=len(lines),
            CodigoBarras="",  # Vuoto come nel CSV
            
            # Tariffe (dal CSV di esempio, tutto vuoto/default)
            IdTarifa=None,
            NombreTarifa="",
            DescuentoTarifa=None,
            TipoTarifa="",
            FechaInicioTarifa=None,
            FechaFinTarifa=None,
            
            # Controlli e hash
            CodigoHash="",  # Vuoto come nel CSV
            EstadoFactura='C',  # 'C' = Completata come nel CSV
            ImporteSolicitado=None,
            ImporteEntregado=None,
            ImporteDevuelto=None,
            PuntosFidelidad=None,
            PuntosFidelidadTotales=None,
            REAplicado=0,  # Default 0
            IdBotonVendedor=None,
            UsuarioAnulacion="",
            
            # Audit (dal CSV di esempio)
            Version="4.7.0",  # Come nel CSV
            Modificado=1,  # 1 = modificato
            Operacion='M',  # 'M' = modified come nel CSV
            Usuario=(current_user.username if current_user and hasattr(current_user, 'username') else 'BELL')[:20],  # 'BELL' come CSV
            TimeStamp=datetime.now(),
            
            # Campi TicketBai (dal CSV di esempio)
            TB_TBAI=2,  # Come nel CSV
            TB_NumSerieBalanza=f"{next_num:08d}",  # Numero seriale dinamico
            TB_SerieFactura=f"{next_num:08d}FA",  # Formato simile al CSV
            TB_TipoFactura="FA",  # Come nel CSV
            TB_FacturaRectificada=0,
            TB_FacturaAnulada=0,
            TB_ContenidoQR="",
            TB_IdentificativoTB="",
            TB_IdfacturaAnt=None,
            TB_TipoFacturaAnt="",
            TB_IdfacturaRec=None,
            TB_TipoFacturaRec="",
            TB_TipoRectificacion="",
            TB_CodigoRectificacion="",
            TB_FacturaSustitutiva=0,
            IdNegativaAuxiliar=0
        )
        
        # Assegna manualmente un ID prima dell'inserimento
        max_id = db.session.query(db.func.max(FatturaCabecera.IdFactura)).scalar() or 0
        fattura.IdFactura = max_id + 1
        
        db.session.add(fattura)
        db.session.flush()  # Per ottenere l'ID
        
        print(f"DEBUG: fattura.IdFactura dopo flush = {fattura.IdFactura}")
        
        # Salva le linee della fattura
        for i, line in enumerate(lines, 1):
            quantita = float(line.get('quantita', 1))
            prezzo_unitario = float(line.get('prezzo_unitario', 0))
            prezzo_totale = float(line.get('prezzo_totale', 0))
            aliquota_iva = float(line.get('aliquota_iva', 0))
            importo_iva_linea = prezzo_totale * (aliquota_iva / 100)
            
            # Determina se è un articolo pesabile o numerabile
            is_weight = line.get('unita_misura', 'PZ') in ['Kg', 'g', 'KG', 'G']
            
            # Ottiene i dati dell'articolo se disponibile
            articolo = None
            id_articolo = line.get('id_articolo')
            if id_articolo:
                articolo = Article.query.get(id_articolo)
            
            # Assegna manualmente IdLineaFactura - calcola per ogni linea per evitare conflitti
            max_linea_id = db.session.query(db.func.max(FatturaLinea.IdLineaFactura)).scalar() or 0
            current_linea_id = max_linea_id + i
            
            fattura_linea = FatturaLinea(
                IdLineaFactura=current_linea_id,  # ID univoco per ogni linea
                IdFactura=fattura.IdFactura,
                IdEmpresa=company.IdEmpresa,
                IdTienda=1,
                IdTiendaCreacion=1,
                IdBalanzaMaestra=1,
                IdBalanzaEsclava=-1,
                
                # Tipo vendita (dal CSV di esempio)
                TipoVenta=2,  # Standard come nel CSV
                
                # Dati articolo
                IdArticulo=id_articolo,
                Descripcion=(line.get('descrizione') or (articolo.Descripcion if articolo else ''))[:100],
                Descripcion1=(line.get('descrizione') or (articolo.Descripcion if articolo else ''))[:100],
                
                # Comportamento e flags (dal CSV di esempio)
                Comportamiento=0,  # 0 = comportamento normale
                EntradaManual=0,   # 0 = non inserimento manuale
                
                # Tara (dal CSV di esempio)
                Tara=0.000,
                TaraPreprogramada=0,
                TaraFija=0.000,
                TaraPorcentual=0.000,
                
                # Peso o quantità
                Peso=quantita if is_weight else 1.000,  # Sempre un valore, default 1.000 se non peso
                PesoBruto=None,
                PesoEmbalaje=None,
                PesoRegalado=None,
                PesoNetoNoEscurrido=None,
                ValorTaraPorcentual=None,
                TaraNoEscurrida=None,
                DetalleTara=None,
                
                Cantidad2=quantita if not is_weight else None,
                Cantidad2Regalada=None,
                Medida2=(line.get('unita_misura', 'PZ') or 'PZ')[:10],  # varchar(10) constraint
                
                # Prezzi (dal CSV di esempio)
                PrecioPorCienGramos=0,  # 0 = non prezzo per 100g
                Precio=prezzo_unitario,
                PrecioSinOferta=None,
                PrecioSinIVA=prezzo_unitario,
                PrecioConIVASinDtoL=None,
                
                # IVA
                IdIVA=1,  # Default IVA ID
                PorcentajeIVA=aliquota_iva,
                RecargoEquivalencia=0.000,  # Default 0
                
                # Sconti
                Descuento=0.000,  # Default 0 se non specificato
                
                # Importi (popolando tutti i campi come nel CSV)
                Importe=prezzo_totale,
                ImporteSinOferta=None,
                ImporteSinIVASinDtoL=prezzo_totale,
                ImporteConIVASinDtoL=None,
                ImporteSinIVAConDtoL=prezzo_totale,
                ImporteDelIVAConDtoL=importo_iva_linea,
                ImporteSinIVAConDtoLConDtoTotal=prezzo_totale,
                ImporteDelIVAConDtoLConDtoTotal=importo_iva_linea,
                ImporteSinIVAConDtoLConDtoTotalConDtoPP=prezzo_totale,
                ImporteDelIVAConDtoLConDtoTotalConDtoPP=importo_iva_linea,
                ImporteDelRE=0.000,
                ImporteDelDescuento=0.000,
                ImporteConDtoTotalConDtoPP=prezzo_totale + importo_iva_linea,
                
                # Date (tutte None per default, come nel CSV)
                DiasCaducidad=None,
                HorasCaducidad=None,
                FechaCaducidad=None,
                DiasExtra=None,
                HorasExtra=None,
                FechaExtra=None,
                DiasEnvasado=None,
                HorasEnvasado=None,
                FechaEnvasado=None,
                DiasCongelacion=None,
                HorasCongelacion=None,
                FechaCongelacion=None,
                DiasConsumo=None,
                HorasConsumo=None,
                FechaConsumo=None,
                DiasFabricacion=None,
                HorasFabricacion=None,
                FechaFabricacion=None,
                
                # Codici e identificatori
                LogoEtiqueta=None,
                CodInterno=(articolo.IdArticulo if articolo else 0),  # Usa ID articolo
                EANScannerArticulo=(articolo.EANScanner if articolo and articolo.EANScanner else None),
                TextoLote=None,
                
                # Classificazioni (dal CSV di esempio, con dati articolo se disponibile)
                IdClase=1,  # Default
                NombreClase="GASTRO",  # Default come nel CSV
                IdElemAsociado=0,
                NombreElemAsociado="",
                IdFamilia=(articolo.IdFamilia if articolo and articolo.IdFamilia else 0),
                NombreFamilia="",  # Potrebbe essere popolato da join
                IdSeccion=(articolo.IdSeccion if articolo and articolo.IdSeccion else 0),
                NombreSeccion="",  # Potrebbe essere popolato da join
                IdSubFamilia=(articolo.IdSubFamilia if articolo and articolo.IdSubFamilia else 0),
                NombreSubFamilia="",  # Potrebbe essere popolato da join
                IdDepartamento=(articolo.IdDepartamento if articolo and articolo.IdDepartamento else 0),
                NombreDepartamento="",  # Potrebbe essere popolato da join
                
                # Campi testo (tutti vuoti per default)
                Texto1="",
                Texto2="",
                Texto3="", 
                Texto4="",
                Texto5="",
                Texto6="",
                Texto7="",
                Texto8="",
                Texto9="",
                Texto10="",
                Texto11="",
                Texto12="",
                Texto13="",
                Texto14="",
                Texto15="",
                Texto16="",
                Texto17="",
                Texto18="",
                Texto19="",
                Texto20="",
                TextoLibre="",
                
                # Altri campi
                PesoPieza=1.000,  # Default come nel CSV
                UnidadesCaja=0,
                NombrePlataforma="",
                HayTaraAplicada=0,
                
                # Stato linea (dal CSV di esempio)
                LineaCerrada=1,  # 1 = linea chiusa
                EstadoLinea=0,   # 0 = stato normale
                
                # Origine (se da DDT)
                TipoOrigen='I' if ddt_reference else 'F',  # 'I' come nel CSV di esempio
                IdOrigen=ddt_reference.IdAlbaran if ddt_reference else None,
                NumeroOrigen=str(ddt_reference.NumAlbaran)[:20] if ddt_reference else None,
                FechaOrigen=ddt_reference.Fecha if ddt_reference else None,
                IdLineaOrigen=None,
                
                # Audit (come nel CSV di esempio)
                Usuario=(current_user.username if current_user and hasattr(current_user, 'username') else 'BELL')[:20],  # Default 'BELL' come CSV
                TimeStamp=datetime.now(),
                Modificado=1,  # 1 = modificato (come nel CSV)
                Operacion='A'  # 'A' = insert (come nel CSV)
            )
            
            db.session.add(fattura_linea)
        
        # Commit delle modifiche
        db.session.commit()
        
        logger.info(f"📊 Fattura {fattura.NumFactura} salvata nel database con ID {fattura.IdFactura}")
        return fattura
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Errore nel salvataggio fattura nel database: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def create_fattura_pa_from_data(invoice_data):
    """Create a FatturaPA XML file from invoice data"""
    try:
        company = invoice_data['company']
        client = invoice_data['client']
        lines = invoice_data['lines']
        note = invoice_data.get('note', '')
        date = invoice_data.get('date', datetime.now())
        
        if not company or not client:
            return None, "Company or client data missing"
            
        if not lines:
            return None, "No items found in the invoice"
            
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
        
        # First, calculate all line items and VAT summary to get the total amount
        # Group VAT rates for summary
        vat_summary = {}
        line_items_data = []
        
        # Process each line item from the invoice data
        for i, line in enumerate(lines, 1):
            # Quantità (peso/quantità dell'articolo)
            quantity = float(line['quantita'] or 1)
            
            # PrezzoUnitario (prezzo unitario senza IVA)
            unit_price = float(line['prezzo_unitario'] or 0)
            
            # PrezzoTotale = Quantità × PrezzoUnitario (secondo specifiche PA)
            line_total = quantity * unit_price
            # Arrotonda a 2 decimali come richiesto dalle specifiche
            line_total = round(line_total, 2)
            
            # VAT rate for the line
            vat_rate = float(line['aliquota_iva'] or 0)
            
            # Store line data for later XML generation
            line_items_data.append({
                'numero_linea': i,
                'descrizione': line['descrizione'],
                'quantita': quantity,
                'unita_misura': line['unita_misura'],
                'prezzo_unitario': unit_price,
                'prezzo_totale': line_total,
                'aliquota_iva': vat_rate
            })
            
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
            # 🔧 CORREZIONE CALCOLO IVA: Calcola l'imposta per questa linea specifica e accumulala
            # Invece di ricalcolare l'imposta sul totale accumulato (che era sbagliato)
            vat_summary[vat_key]['Imposta'] += round(line_total * (vat_rate / 100), 2)
        
        # Calculate the total invoice amount (ImponibileImporto + Imposta)
        total_invoice_amount = 0.0
        for vat_data in vat_summary.values():
            total_invoice_amount += vat_data['ImponibileImporto'] + vat_data['Imposta']

        # Round the total to 2 decimal places
        total_invoice_amount = round(total_invoice_amount, 2)
        
        # 2.1 DatiGenerali
        dati_generali = ET.SubElement(body, 'DatiGenerali')
        
        # 2.1.1 DatiGeneraliDocumento
        dati_generali_doc = ET.SubElement(dati_generali, 'DatiGeneraliDocumento')
        
        # Check if this is based on a DDT
        ddt_reference = invoice_data.get('ddt_reference')
        
        if ddt_reference:
            # If it's based on a DDT, set the type to TD24 (fattura differita)
            ET.SubElement(dati_generali_doc, 'TipoDocumento').text = 'TD24'  # TD24 for 'fattura differita'
            
            # Add causation (Causale) with DDT reference
            ET.SubElement(dati_generali_doc, 'Causale').text = f"Fattura differita da DDT n. {ddt_reference.NumAlbaran} del {ddt_reference.Fecha.strftime('%d/%m/%Y') if ddt_reference.Fecha else 'N/A'}"
            
            # Add DDT references
            dati_ddt = ET.SubElement(dati_generali, 'DatiDDT')
            ET.SubElement(dati_ddt, 'NumeroDDT').text = str(ddt_reference.NumAlbaran)
            ET.SubElement(dati_ddt, 'DataDDT').text = ddt_reference.Fecha.strftime('%Y-%m-%d') if ddt_reference.Fecha else datetime.now().strftime('%Y-%m-%d')
        else:
            # Set the type to TD01 (fattura normale) since this is not based on a DDT
            ET.SubElement(dati_generali_doc, 'TipoDocumento').text = 'TD01'  # TD01 for 'fattura'
            
            # Add causation (Causale) if there's a note
            if note:
                ET.SubElement(dati_generali_doc, 'Causale').text = note
        
        # Set the invoice currency to EUR
        ET.SubElement(dati_generali_doc, 'Divisa').text = 'EUR'
        
        # Invoice date in ISO format (YYYY-MM-DD)
        invoice_date = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else datetime.now().strftime('%Y-%m-%d')
        ET.SubElement(dati_generali_doc, 'Data').text = invoice_date
        
        # Invoice number (must be unique)
        ET.SubElement(dati_generali_doc, 'Numero').text = str(invoice_number)
        
        # Add the total invoice amount as required by Italian Electronic Invoice specifications
        ET.SubElement(dati_generali_doc, 'ImportoTotaleDocumento').text = format_decimal(total_invoice_amount, 2)
        
        # 2.2 DatiBeniServizi (Invoice Line Items)
        dati_beni_servizi = ET.SubElement(body, 'DatiBeniServizi')
        
        # Add each line item from the pre-calculated data
        for line_data in line_items_data:
            dati_linea = ET.SubElement(dati_beni_servizi, 'DettaglioLinee')
            ET.SubElement(dati_linea, 'NumeroLinea').text = str(line_data['numero_linea'])
            ET.SubElement(dati_linea, 'Descrizione').text = line_data['descrizione']
            ET.SubElement(dati_linea, 'Quantita').text = format_decimal(line_data['quantita'], 2)
            ET.SubElement(dati_linea, 'UnitaMisura').text = line_data['unita_misura']
            ET.SubElement(dati_linea, 'PrezzoUnitario').text = format_decimal(line_data['prezzo_unitario'], 8)
            ET.SubElement(dati_linea, 'PrezzoTotale').text = format_decimal(line_data['prezzo_totale'], 2)
            ET.SubElement(dati_linea, 'AliquotaIVA').text = format_decimal(line_data['aliquota_iva'], 2)
        
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
        
        # Use the already calculated total invoice amount for ImportoPagamento
        ET.SubElement(dettaglio_pagamento, 'ImportoPagamento').text = format_decimal(total_invoice_amount, 2)
        
        # Generate the invoice XML
        xml_data = prettify_xml(root)
        
        return xml_data, None  # Return the XML data and no error
        
    except Exception as e:
        logger.error(f"Error generating FatturaPA XML: {str(e)}")
        return None, str(e)

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
            
        # Prepare invoice data
        invoice_data = {
            'company': company,
            'client': client,
            'lines': [],
            'note': ddt.ObservacionesDocumento or '',
            'date': ddt.Fecha or datetime.now(),
            'ddt_reference': ddt
        }
        
        # Convert DDT lines to invoice lines
        for line in ddt_lines:
            quantity = float(line.Peso or 1)


            # 🔧 CORREZIONE SCONTO: Usa il totale scontato dal DDT per calcolare il prezzo unitario corretto
            # Invece di usare PrecioSinIVA (che non include lo sconto), calcola il prezzo unitario
            # dal totale scontato ImporteSinIVASinDtoL
            if quantity > 0 and line.ImporteSinIVASinDtoL:
                # Prezzo unitario scontato = totale scontato / quantità
                unit_price = float(line.ImporteSinIVASinDtoL) / quantity
            else:
                # Fallback al prezzo originale se non disponibile
                unit_price = float(line.PrecioSinIVA or 0)

            line_total = float(line.ImporteSinIVASinDtoL or 0)  # Usa il totale già calcolato nel DDT
            vat_rate = float(line.PorcentajeIVA or 0)

            invoice_data['lines'].append({
                'descrizione': line.Descripcion,
                'quantita': quantity,
                'unita_misura': line.Medida2 or 'PZ',
                'prezzo_unitario': unit_price,
                'prezzo_totale': line_total,
                'aliquota_iva': vat_rate
            })
        
        # Generate the invoice using the data function
        xml_data, error_message = create_fattura_pa_from_data(invoice_data)
        
        if xml_data is None:
            return None, error_message
            
        # Save the file
        import os
        invoice_year = ddt.Fecha.year if ddt.Fecha else datetime.now().year
        invoice_dir = os.path.join(current_app.root_path, 'Fatture', str(invoice_year))
        os.makedirs(invoice_dir, exist_ok=True)
        
        # Generate filename
        client_name_clean = "".join(c for c in (client.Nombre or 'Cliente_Sconosciuto') if c.isalnum() or c in (' ', '-', '_')).replace(' ', '_')
        timestamp = datetime.now().strftime('%y%m%d%H%M')
        xml_filename = f"IT{company.CIF_VAT.replace('IT', '')}_FPR12_{timestamp}.xml"
        xml_path = os.path.join(invoice_dir, xml_filename)
        
        # Save the file
        with open(xml_path, 'wb') as xml_file:
            xml_file.write(xml_data)
        
        # Salva la fattura nel database
        filename_only = os.path.basename(xml_path)
        try:
            fattura_db = save_fattura_to_db(invoice_data, filename_only, xml_path, ddt)
            if fattura_db:
                logger.info(f"💾 Fattura salvata nel database: ID {fattura_db.IdFattura}")
        except Exception as e:
            logger.error(f"⚠️  Errore nel salvataggio database (ma file XML creato): {str(e)}")
        
        return xml_path, None
        
    except Exception as e:
        logger.error(f"Error generating FatturaPA XML from DDT: {str(e)}")
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
    """List all generated invoices from database"""
    try:
        # Ottiene fatture dal database ordinate per data (più recenti prime)
        fatture_db = FatturaCabecera.query.order_by(FatturaCabecera.Fecha.desc(), FatturaCabecera.IdFactura.desc()).all()
        
        # Se non ci sono fatture nel DB, fallback ai file XML
        if not fatture_db:
            return list_invoices_from_files()
        
        return render_template('fattura_pa/list.html', fatture=fatture_db, from_database=True)
        
    except Exception as e:
        logger.error(f"Errore nel recupero fatture dal database: {str(e)}")
        flash('Errore nel recupero delle fatture dal database. Mostro i file XML.', 'warning')
        return list_invoices_from_files()

@fattura_pa_bp.route('/list_files')
@login_required  
@admin_required
def list_invoices_from_files():
    """List all generated invoices from XML files (fallback)"""
    fatture_dir = os.path.join(current_app.root_path, 'Fatture')
    os.makedirs(fatture_dir, exist_ok=True)
    
    invoices = []
    
    # Cerca in tutte le sottocartelle per anno
    for year_dir in os.listdir(fatture_dir):
        year_path = os.path.join(fatture_dir, year_dir)
        if os.path.isdir(year_path):
            for filename in os.listdir(year_path):
                if filename.endswith('.xml'):
                    file_path = os.path.join(year_path, filename)
                    creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    invoices.append({
                        'filename': filename,
                        'created_at': creation_time,
                        'size': os.path.getsize(file_path),
                        'year': year_dir,
                        'full_path': file_path
                    })
    
    # Cerca anche nella cartella principale
    for filename in os.listdir(fatture_dir):
        if filename.endswith('.xml'):
            file_path = os.path.join(fatture_dir, filename)
            if os.path.isfile(file_path):
                creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                
                invoices.append({
                    'filename': filename,
                    'created_at': creation_time,
                    'size': os.path.getsize(file_path),
                    'year': 'root',
                    'full_path': file_path
                })
    
    # Sort by creation time (newest first)
    invoices.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('fattura_pa/list.html', invoices=invoices, from_database=False)

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
                elif 'ImportoTotaleDocumento' in elem.tag and elem.text:
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
                        
                        # Total invoice amount
                        importo_totale_elem = dati_gen_doc.find('ImportoTotaleDocumento', namespaces)
                        if importo_totale_elem is not None:
                            invoice_details['importo_totale_documento'] = importo_totale_elem.text
                            invoice_details['total_amount'] = importo_totale_elem.text  # Set the display field
                    
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

@fattura_pa_bp.route('/detail_db/<int:fattura_id>')
@login_required
@admin_required
def invoice_detail_db(fattura_id):
    """Show invoice detail from database"""
    try:
        fattura = FatturaCabecera.query.get_or_404(fattura_id)
        
        return render_template('fattura_pa/detail_db.html', fattura=fattura)
        
    except Exception as e:
        logger.error(f"Error loading invoice detail for ID {fattura_id}: {str(e)}")
        flash(f'Errore nel caricamento della fattura: {str(e)}', 'danger')
        return redirect(url_for('fattura_pa.list_invoices'))

@fattura_pa_bp.route('/update_stato/<int:fattura_id>', methods=['POST'])
@login_required
@admin_required
def update_stato_fattura(fattura_id):
    """Update invoice status"""
    try:
        fattura = FatturaCabecera.query.get_or_404(fattura_id)
        nuovo_stato = request.form.get('stato')
        
        # Mappa i valori di input ai codici a carattere singolo
        stato_map = {
            'generata': 'G',
            'inviata': 'I', 
            'pagata': 'P',
            'annullata': 'A'
        }
        
        if nuovo_stato in stato_map:
            fattura.EstadoFactura = stato_map[nuovo_stato]
            fattura.Usuario = current_user.username[:20]  # varchar(20) constraint
            fattura.TimeStamp = datetime.now()
            
            db.session.commit()
            
            flash(f'Stato fattura aggiornato a: {fattura.stato_display}', 'success')
        else:
            flash('Stato non valido', 'danger')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nell\'aggiornamento: {str(e)}', 'danger')
        
    return redirect(url_for('fattura_pa.invoice_detail_db', fattura_id=fattura_id))

@fattura_pa_bp.route('/download_db/<int:fattura_id>')
@login_required
@admin_required
def download_invoice_db(fattura_id):
    """Download invoice XML from database record"""
    try:
        fattura = FatturaCabecera.query.get_or_404(fattura_id)
        
        # Il file XML dovrebbe essere nella cartella Fatture con nome basato sulla ReferenciaDocumento
        xml_filename = fattura.ReferenciaDocumento
        if not xml_filename:
            flash('Nome file XML non trovato nella fattura', 'danger')
            return redirect(url_for('fattura_pa.invoice_detail_db', fattura_id=fattura_id))
        
        # Prova a trovare il file nella cartella per anno
        year = fattura.Fecha.year if fattura.Fecha else datetime.now().year
        fatture_dir = os.path.join(current_app.root_path, 'Fatture', str(year))
        file_path = os.path.join(fatture_dir, xml_filename)
        
        if not os.path.exists(file_path):
            # Ultimo tentativo nella cartella root
            file_path = os.path.join(current_app.root_path, 'Fatture', xml_filename)
        
        if not os.path.exists(file_path):
            flash('File XML non trovato', 'danger')
            return redirect(url_for('fattura_pa.invoice_detail_db', fattura_id=fattura_id))
        
        with open(file_path, 'rb') as f:
            data = f.read()
            
        return send_file(
            io.BytesIO(data),
            mimetype='application/xml',
            as_attachment=True,
            download_name=xml_filename
        )
        
    except Exception as e:
        logger.error(f"Error downloading invoice {fattura_id}: {str(e)}")
        flash(f'Errore nel download: {str(e)}', 'danger')
        return redirect(url_for('fattura_pa.invoice_detail_db', fattura_id=fattura_id))

@fattura_pa_bp.route('/delete_db/<int:fattura_id>', methods=['POST'])
@login_required
@admin_required
def delete_invoice_db(fattura_id):
    """Delete invoice from database (and optionally XML file)"""
    try:
        fattura = FatturaCabecera.query.get_or_404(fattura_id)
        nome_file = fattura.ReferenciaDocumento
        
        # Prima di eliminare la fattura, ripristina lo stato dei ticket a 'giacenza'
        try:
            # Recupera tutte le linee della fattura
            linee_fattura = FatturaLinea.query.filter_by(IdFactura=fattura_id).all()
            
            # Trova tutti i ticket unici referenziati nelle linee
            ticket_ids = set()
            for linea in linee_fattura:
                # Se la linea proviene da un DDT/ticket (TipoOrigen = 'I')
                if linea.TipoOrigen == 'I' and linea.IdOrigen:
                    # IdOrigen contiene l'IdAlbaran del DDT
                    # Dobbiamo trovare i ticket associati a questo DDT
                    from app.models import AlbaranCabecera, AlbaranLinea
                    
                    # Trova le linee del DDT
                    albaran_lineas = AlbaranLinea.query.filter_by(IdAlbaran=linea.IdOrigen).all()
                    
                    for albaran_linea in albaran_lineas:
                        # Ogni linea DDT ha riferimenti al ticket originale
                        if hasattr(albaran_linea, 'IdOrigen') and albaran_linea.IdOrigen:
                            ticket_ids.add(albaran_linea.IdOrigen)
            
            # Ripristina lo stato Enviado = 0 per tutti i ticket trovati
            if ticket_ids:
                from app.models import TicketHeader
                tickets_to_restore = TicketHeader.query.filter(TicketHeader.IdTicket.in_(ticket_ids)).all()
                
                for ticket in tickets_to_restore:
                    if ticket.Enviado == 1:  # Solo se era processato
                        ticket.Enviado = 0  # Ripristina a 'giacenza'
                        logger.info(f"🔄 Ticket {ticket.IdTicket} ripristinato a stato giacenza")
                
                logger.info(f"📦 Ripristinati {len(tickets_to_restore)} ticket a stato giacenza")
            
        except Exception as restore_error:
            logger.error(f"⚠️ Errore nel ripristino stato ticket: {str(restore_error)}")
            # Non blocchiamo l'eliminazione della fattura per questo errore
        
        # Elimina il record dal database (le linee vengono eliminate automaticamente per CASCADE)
        db.session.delete(fattura)
        
        # Opzionalmente elimina anche il file XML
        delete_file = request.form.get('delete_file') == 'true'
        if delete_file and nome_file:
            try:
                # Cerca il file
                year = fattura.Fecha.year if fattura.Fecha else datetime.now().year
                fatture_dir = os.path.join(current_app.root_path, 'Fatture', str(year))
                file_path = os.path.join(fatture_dir, nome_file)
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"File XML eliminato: {file_path}")
                else:
                    # Prova nella cartella root
                    file_path = os.path.join(current_app.root_path, 'Fatture', nome_file)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"File XML eliminato: {file_path}")
                        
            except Exception as file_error:
                logger.warning(f"Impossibile eliminare file XML {nome_file}: {str(file_error)}")
        
        db.session.commit()
        
        flash(f'Fattura {nome_file} eliminata dal database e ticket ripristinati a giacenza', 'success')
        return redirect(url_for('fattura_pa.list_invoices'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting invoice {fattura_id}: {str(e)}")
        flash(f'Errore nell\'eliminazione: {str(e)}', 'danger')
        return redirect(url_for('fattura_pa.invoice_detail_db', fattura_id=fattura_id))

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