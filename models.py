from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Initialize SQLAlchemy with specific engine options to force utf8
db = SQLAlchemy(engine_options={
    'connect_args': {
        'charset': 'utf8',
    },
    'pool_pre_ping': True,
})

# Remote Database Models (read-only)

class Client(db.Model):
    __tablename__ = 'dat_cliente'
    
    # NOTA: IdCliente non è AUTO_INCREMENT nel database, deve essere impostato manualmente
    IdCliente = db.Column(db.Integer, primary_key=True)
    IdEmpresa = db.Column(db.Integer)
    Nombre = db.Column(db.String(100))
    Direccion = db.Column(db.String(200))
    CodPostal = db.Column(db.String(10))
    Poblacion = db.Column(db.String(100))
    Provincia = db.Column(db.String(100))
    Pais = db.Column(db.String(100))
    DNI = db.Column(db.String(20))
    Telefono1 = db.Column(db.String(20))
    Telefono2 = db.Column(db.String(20))
    Telefono3 = db.Column(db.String(20))
    Email = db.Column(db.String(100))
    TipoEmailTicket = db.Column(db.Integer)
    TipoEmailAlbaran = db.Column(db.Integer)
    TipoEmailFactura = db.Column(db.Integer)
    Foto = db.Column(db.LargeBinary)
    IdTarifa = db.Column(db.Integer)
    Ofertas = db.Column(db.Integer)
    IdFormaPago = db.Column(db.Integer)
    IdEstado = db.Column(db.Integer)
    Observaciones = db.Column(db.Text)
    CodInterno = db.Column(db.String(50))
    Descuento = db.Column(db.Numeric(10, 2))
    PuntosFidelidad = db.Column(db.Integer)
    CuentaPendiente = db.Column(db.Numeric(10, 2))
    EANScanner = db.Column(db.String(50))
    FormatoAlbaran = db.Column(db.String(100))
    UsarRecargoEquivalencia = db.Column(db.Integer)
    DtoProntoPago = db.Column(db.Numeric(10, 2))
    NombreBanco = db.Column(db.String(100))
    CodigoCuenta = db.Column(db.String(50))
    NumeroVencimientos = db.Column(db.Integer)
    DiasEntreVencimientos = db.Column(db.Integer)
    TotalPorArticulo = db.Column(db.Integer)
    AplicarTarifaEtiqueta = db.Column(db.Integer)
    FormatoFactura = db.Column(db.String(100))
    ModoFacturacion = db.Column(db.Integer)
    Modificado = db.Column(db.Integer)
    Operacion = db.Column(db.Integer)
    Usuario = db.Column(db.String(50))
    TimeStamp = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Client {self.IdCliente}: {self.Nombre}>'

class Product(db.Model):
    __tablename__ = 'dat_articulo'
    
    IdArticulo = db.Column(db.Integer, primary_key=True)
    Descripcion = db.Column(db.String(100))
    PrecioConIVA = db.Column(db.Numeric(13, 3))
    EANScanner = db.Column(db.String(50))
    IdFamilia = db.Column(db.Integer)
    IdSubFamilia = db.Column(db.Integer)
    IdIva = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<Product {self.IdArticulo}: {self.Descripcion}>'

    @property
    def Precio(self):
        return self.PrecioConIVA
    
    @property
    def CodEAN(self):
        return self.EANScanner
    
    @property
    def IvaFormatted(self):
        if self.IdIva == 1:
            return "4%"
        elif self.IdIva == 2:
            return "10%"
        elif self.IdIva == 3:
            return "22%"
        else:
            return "Non disponibile"


class TicketHeader(db.Model):
    __tablename__ = 'dat_ticket_cabecera'
    
    IdTicket = db.Column(db.Integer, primary_key=True)
    IdEmpresa = db.Column(db.Integer, default=1)
    IdTienda = db.Column(db.Integer, default=1)
    IdBalanzaMaestra = db.Column(db.Integer, default=1)
    IdBalanzaEsclava = db.Column(db.Integer, default=1)
    TipoVenta = db.Column(db.Integer, default=1)
    NumTicket = db.Column(db.Integer)
    Fecha = db.Column(db.DateTime)
    CodigoBarras = db.Column(db.String(50))
    NumLineas = db.Column(db.Integer)
    Enviado = db.Column(db.Integer, default=0)
    
    # Relationship
    lines = db.relationship('TicketLine', backref='header', lazy='dynamic',
                          primaryjoin="TicketHeader.IdTicket == TicketLine.IdTicket")
    
    def __repr__(self):
        return f'<TicketHeader {self.IdTicket}: Ticket #{self.NumTicket}>'
    
    @property
    def is_processed(self):
        return self.Enviado == 1
    
    @property
    def formatted_date(self):
        if self.Fecha:
            return self.Fecha.strftime('%d/%m/%Y %H:%M')
        return 'N/A'


class TicketLine(db.Model):
    __tablename__ = 'dat_ticket_linea'
    
    IdLineaTicket = db.Column(db.Integer, primary_key=True)
    IdTicket = db.Column(db.Integer, db.ForeignKey('dat_ticket_cabecera.IdTicket'))
    IdArticulo = db.Column(db.Integer, db.ForeignKey('dat_articulo.IdArticulo'))
    Descripcion = db.Column(db.String(100))
    Peso = db.Column(db.Numeric(15, 3))
    FechaCaducidad = db.Column(db.DateTime)
    comportamiento = db.Column(db.Integer, default=0)  # 0 = unità, 1 = kg
    
    # Relationship
    product = db.relationship('Product', 
                             primaryjoin="TicketLine.IdArticulo == Product.IdArticulo",
                             backref='ticket_lines')
    
    def __repr__(self):
        return f'<TicketLine {self.IdLineaTicket}: {self.Descripcion}>'


# Local Database Models

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    scan_logs = db.relationship('ScanLog', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class ScanLog(db.Model):
    __tablename__ = 'scan_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ticket_id = db.Column(db.Integer)
    action = db.Column(db.String(20))  # 'view', 'scan', 'scan_attempt', or 'checkout'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # New fields for the QR code data
    raw_code = db.Column(db.String(50))
    product_code = db.Column(db.Integer)
    scan_date = db.Column(db.String(20))
    scan_time = db.Column(db.String(20))
    
    def __repr__(self):
        return f'<ScanLog {self.id}: User {self.user_id} - Ticket {self.ticket_id}>'


class Company(db.Model):
    __tablename__ = 'dat_empresa'
    
    IdEmpresa = db.Column(db.Integer, primary_key=True)
    NombreEmpresa = db.Column(db.String(100))
    CIF_VAT = db.Column(db.String(50))
    Telefono1 = db.Column(db.String(20))
    Direccion = db.Column(db.String(200))
    CodPostal = db.Column(db.String(10))
    Poblacion = db.Column(db.String(100))
    Provincia = db.Column(db.String(100))
    # Adding only the fields we need for the DDT functionality
    
    def __repr__(self):
        return f'<Company {self.IdEmpresa}: {self.NombreEmpresa}>'


class DDTHead(db.Model):
    __tablename__ = 'ddt_head'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('dat_cliente.IdCliente'), nullable=False)
    id_empresa = db.Column(db.Integer, db.ForeignKey('dat_empresa.IdEmpresa'), nullable=False)
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    totale_senza_iva = db.Column(db.Numeric(10, 2), default=0)
    totale_iva = db.Column(db.Numeric(10, 2), default=0)
    totale_importo = db.Column(db.Numeric(10, 2), default=0)
    
    # Relationships
    cliente = db.relationship('Client', 
                              primaryjoin="DDTHead.id_cliente == Client.IdCliente",
                              foreign_keys=[id_cliente])
    empresa = db.relationship('Company',
                               primaryjoin="DDTHead.id_empresa == Company.IdEmpresa",
                               foreign_keys=[id_empresa])
    lines = db.relationship('DDTLine', backref='ddt', lazy='dynamic',
                            cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<DDTHead {self.id}: Cliente {self.id_cliente}>'
    
    def calculate_totals(self):
        """Calculate and update the totals for this DDT"""
        total_senza_iva = 0
        total_iva = 0
        
        for ddt_line in self.lines:
            # Get the ticket
            ticket = TicketHeader.query.filter_by(
                IdTicket=ddt_line.id_ticket,
                IdEmpresa=ddt_line.id_empresa,
                IdTienda=ddt_line.id_tienda,
                IdBalanzaMaestra=ddt_line.id_balanza_maestra,
                IdBalanzaEsclava=ddt_line.id_balanza_esclava,
                TipoVenta=ddt_line.tipo_venta
            ).first()
            
            if not ticket:
                continue
            
            # Get ticket lines
            ticket_lines = TicketLine.query.filter_by(
                IdTicket=ticket.IdTicket
            ).all()
            
            # Calculate totals for each line
            for t_line in ticket_lines:
                product = Product.query.get(t_line.IdArticulo)
                if not product:
                    continue
                
                # Determine VAT rate
                vat_rate = 0
                if product.IdIva == 1:
                    vat_rate = 0.04  # 4%
                elif product.IdIva == 2:
                    vat_rate = 0.10  # 10%
                elif product.IdIva == 3:
                    vat_rate = 0.22  # 22%
                
                # Calculate price without VAT
                price_with_vat = float(product.PrecioConIVA)
                price_without_vat = price_with_vat / (1 + vat_rate)
                
                # Multiply by weight/quantity
                line_total = price_without_vat * float(t_line.Peso)
                line_vat = line_total * vat_rate
                
                total_senza_iva += line_total
                total_iva += line_vat
        
        # Update totals
        self.totale_senza_iva = total_senza_iva
        self.totale_iva = total_iva
        self.totale_importo = total_senza_iva + total_iva
        db.session.commit()
        
        return {
            'totale_senza_iva': self.totale_senza_iva,
            'totale_iva': self.totale_iva,
            'totale_importo': self.totale_importo
        }


class DDTLine(db.Model):
    __tablename__ = 'ddt_line'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_ddt = db.Column(db.Integer, db.ForeignKey('ddt_head.id'), nullable=False)
    id_empresa = db.Column(db.Integer, nullable=False)
    id_tienda = db.Column(db.Integer, nullable=False)
    id_balanza_maestra = db.Column(db.Integer, nullable=False)
    id_balanza_esclava = db.Column(db.Integer, nullable=False)
    tipo_venta = db.Column(db.Integer, nullable=False)
    id_ticket = db.Column(db.BigInteger, nullable=False)
    
    # Add composite foreign key constraint in __table_args__
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['id_empresa', 'id_tienda', 'id_balanza_maestra', 
             'id_balanza_esclava', 'tipo_venta', 'id_ticket'],
            ['dat_ticket_cabecera.IdEmpresa', 'dat_ticket_cabecera.IdTienda',
             'dat_ticket_cabecera.IdBalanzaMaestra', 'dat_ticket_cabecera.IdBalanzaEsclava',
             'dat_ticket_cabecera.TipoVenta', 'dat_ticket_cabecera.IdTicket']
        ),
    )
    
    # Relationship to ticket header
    ticket = db.relationship('TicketHeader',
                             primaryjoin="and_(DDTLine.id_ticket == TicketHeader.IdTicket, "
                                         "DDTLine.id_empresa == TicketHeader.IdEmpresa, "
                                         "DDTLine.id_tienda == TicketHeader.IdTienda, "
                                         "DDTLine.id_balanza_maestra == TicketHeader.IdBalanzaMaestra, "
                                         "DDTLine.id_balanza_esclava == TicketHeader.IdBalanzaEsclava, "
                                         "DDTLine.tipo_venta == TicketHeader.TipoVenta)",
                             foreign_keys=[id_ticket, id_empresa, id_tienda, id_balanza_maestra, id_balanza_esclava, tipo_venta])
    
    def __repr__(self):
        return f'<DDTLine {self.id}: DDT {self.id_ddt} - Ticket {self.id_ticket}>' 