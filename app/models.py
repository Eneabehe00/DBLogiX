from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import foreign

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
    IdListino = db.Column(db.Integer, db.ForeignKey('price_list_header.IdListino'))  # Nuovo campo per associare listino
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
    
    # Relationship con il listino
    listino = db.relationship('ListinoPrezziHeader', backref='clienti', lazy='select')
    
    def __repr__(self):
        return f'<Client {self.IdCliente}: {self.Nombre}>'

class Product(db.Model):
    __tablename__ = 'dat_articulo'
    
    IdArticulo = db.Column(db.Integer, primary_key=True)
    Descripcion = db.Column(db.String(100))
    PrecioConIVA = db.Column(db.Numeric(13, 2))  # Price with IVA (max 2 decimali)
    PrecioSinIVA = db.Column(db.Numeric(13, 2))  # Price without IVA (max 2 decimali)
    EANScanner = db.Column(db.String(50))
    IdFamilia = db.Column(db.Integer)
    IdSubFamilia = db.Column(db.Integer)
    IdIva = db.Column(db.Integer)
    TeclaDirecta = db.Column(db.Integer)
    TaraFija = db.Column(db.Integer)
    
    # Relationships
    
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
    def is_expired(self):
        return self.Enviado == 4
    
    @property
    def status_text(self):
        """Restituisce il testo dello stato del ticket"""
        if self.Enviado == 0:
            return "Giacenza"
        elif self.Enviado == 1:
            return "Processato"
        elif self.Enviado == 2:
            return "DDT1"
        elif self.Enviado == 3:
            return "DDT2"
        elif self.Enviado == 4:
            return "Scaduto"
        elif self.Enviado == 10:
            return "Dentro Task"
        else:
            return "Sconosciuto"
    
    @property
    def status_class(self):
        """Restituisce la classe CSS per lo stato del ticket"""
        if self.Enviado == 0:
            return "warning"  # Giacenza
        elif self.Enviado == 1:
            return "success"  # Processato
        elif self.Enviado == 2:
            return "info"     # DDT1
        elif self.Enviado == 3:
            return "secondary"  # DDT2
        elif self.Enviado == 4:
            return "danger"   # Scaduto
        elif self.Enviado == 10:
            return "primary"  # Task
        else:
            return "dark"     # Sconosciuto
    
    @property
    def formatted_date(self):
        if self.Fecha:
            return self.Fecha.strftime('%d/%m/%Y %H:%M')
        return 'N/A'


class TicketLine(db.Model):
    __tablename__ = 'dat_ticket_linea'
    
    # Composite primary key matching the actual database structure
    IdLineaTicket = db.Column(db.Integer, primary_key=True)
    IdEmpresa = db.Column(db.Integer, primary_key=True, default=1)
    IdTienda = db.Column(db.Integer, primary_key=True, default=1)
    IdBalanzaMaestra = db.Column(db.Integer, primary_key=True, default=0)
    IdBalanzaEsclava = db.Column(db.Integer, primary_key=True, default=0)
    IdTicket = db.Column(db.BigInteger, db.ForeignKey('dat_ticket_cabecera.IdTicket'), primary_key=True)
    TipoVenta = db.Column(db.Integer, primary_key=True, default=2)
    
    # Other fields
    IdArticulo = db.Column(db.Integer, db.ForeignKey('dat_articulo.IdArticulo'))
    Descripcion = db.Column(db.String(100))
    Peso = db.Column(db.Numeric(15, 3))
    Precio = db.Column(db.Numeric(15, 3))  # Campo prezzo storico della linea del ticket
    FechaCaducidad = db.Column(db.DateTime)
    comportamiento = db.Column(db.Integer, default=0)  # 0 = unità, 1 = kg
    TextoLote = db.Column(db.Text)  # Campo per il lotto del prodotto

    # IVA fields for the ticket line
    IdIVA = db.Column(db.Integer)  # IVA ID for this ticket line
    PorcentajeIVA = db.Column(db.Numeric(5, 2))  # IVA percentage for this ticket line

    # Additional fields that might be needed
    PrecioSinIVA = db.Column(db.Numeric(15, 2))  # Price without IVA (max 2 decimali)
    Importe = db.Column(db.Numeric(15, 2))  # Total amount with IVA (max 2 decimali)
    
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
    screen_task = db.Column(db.Boolean, default=False)  # Flag per utenti schermo task
    is_active = db.Column(db.Boolean, default=True)  # Campo per disabilitare utenti
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
        return f'<ScanLog {self.id}: User {self.user_id} - {self.action}>'


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


class AlbaranCabecera(db.Model):
    __tablename__ = 'dat_albaran_cabecera'
    
    IdAlbaran = db.Column(db.BigInteger, primary_key=True, default=1)
    NumAlbaran = db.Column(db.BigInteger)
    IdEmpresa = db.Column(db.Integer, primary_key=True, default=1)
    NombreEmpresa = db.Column(db.String(100))
    CIF_VAT_Empresa = db.Column(db.String(14))
    DireccionEmpresa = db.Column(db.String(50))
    PoblacionEmpresa = db.Column(db.String(25))
    CPEmpresa = db.Column(db.String(8))
    TelefonoEmpresa = db.Column(db.String(20))
    ProvinciaEmpresa = db.Column(db.String(25))
    IdTienda = db.Column(db.Integer, primary_key=True, default=1)
    NombreTienda = db.Column(db.String(50))
    IdBalanzaMaestra = db.Column(db.Integer, primary_key=True, default=0)
    NombreBalanzaMaestra = db.Column(db.String(50))
    IdBalanzaEsclava = db.Column(db.Integer, primary_key=True, default=0)
    NombreBalanzaEsclava = db.Column(db.String(50))
    Tipo = db.Column(db.String(2), default="A")
    IdVendedor = db.Column(db.Integer)
    NombreVendedor = db.Column(db.String(50))
    IdCliente = db.Column(db.Integer)
    NombreCliente = db.Column(db.String(50))
    DNICliente = db.Column(db.String(30))
    EmailCliente = db.Column(db.String(100))
    DireccionCliente = db.Column(db.String(50))
    PoblacionCliente = db.Column(db.String(25))
    ProvinciaCliente = db.Column(db.String(25))
    PaisCliente = db.Column(db.String(10))
    CPCliente = db.Column(db.String(8))
    TelefonoCliente = db.Column(db.String(20))
    ObservacionesCliente = db.Column(db.Text)
    EANCliente = db.Column(db.String(50))
    ReferenciaDocumento = db.Column(db.String(50))
    ObservacionesDocumento = db.Column(db.Text)
    TipoVenta = db.Column(db.Integer, default=2)
    ImporteLineas = db.Column(db.Float(15, 3))
    PorcDescuento = db.Column(db.Float(9, 3))
    ImporteDescuento = db.Column(db.Float(15, 3))
    ImporteRE = db.Column(db.Float(15, 3))
    ImporteTotalSinRE = db.Column(db.Float(15, 3))
    ImporteTotalSinIVAConDtoLConDtoTotalConRE = db.Column(db.Float(15, 3))
    ImporteTotal = db.Column(db.Float(15, 3))
    ImporteLineas2 = db.Column(db.Float(15, 3))
    PorcDescuento2 = db.Column(db.Float(9, 3))
    ImporteDescuento2 = db.Column(db.Float(15, 3))
    ImporteTotal2 = db.Column(db.Float(15, 3))
    ImporteLineas3 = db.Column(db.Float(15, 3))
    PorcDescuento3 = db.Column(db.Float(9, 3))
    ImporteDescuento3 = db.Column(db.Float(15, 3))
    ImporteTotal3 = db.Column(db.Float(15, 3))
    ImporteTotalSinIVAConDtoL = db.Column(db.Float(15, 3))
    ImporteTotalSinIVAConDtoLConDtoTotal = db.Column(db.Float(15, 3))
    ImporteDtoTotalSinIVA = db.Column(db.Float(15, 3))
    ImporteTotalDelIVAConDtoLConDtoTotal = db.Column(db.Float(15, 3))
    ImporteSinRedondeo = db.Column(db.Float(15, 3))
    ImporteDelRedondeo = db.Column(db.Float(15, 3))
    PreseleccionCliente = db.Column(db.Boolean, default=1)
    Fecha = db.Column(db.DateTime)
    FechaModificacion = db.Column(db.DateTime)
    Enviado = db.Column(db.Boolean, default=0)
    NumLineas = db.Column(db.SmallInteger)
    CodigoBarras = db.Column(db.String(1000))
    CodBarrasTalonCaja = db.Column(db.String(1000))
    SerieLIdFinDeDia = db.Column(db.BigInteger)
    SerieLTicketErroneo = db.Column(db.Boolean, default=0)
    IdTarifa = db.Column(db.Integer)
    NombreTarifa = db.Column(db.String(25))
    DescuentoTarifa = db.Column(db.Numeric(9, 3))
    TipoTarifa = db.Column(db.String(1))
    FechaInicioTarifa = db.Column(db.DateTime)
    FechaFinTarifa = db.Column(db.DateTime)
    Modificado = db.Column(db.Boolean, default=1)
    Operacion = db.Column(db.String(1), default="A")
    Usuario = db.Column(db.String(20))
    TimeStamp = db.Column(db.DateTime, default=datetime.utcnow)
    EstadoTicket = db.Column(db.String(1), default="C")
    ImporteEntregado = db.Column(db.Float(15, 3))
    ImporteDevuelto = db.Column(db.Float(15, 3))
    PuntosFidelidad = db.Column(db.Float(15, 3))
    PuntosFidelidadTotales = db.Column(db.Float(15, 3))
    REAplicado = db.Column(db.Boolean, default=0)
    IdBotonVendedor = db.Column(db.Integer)
    Version = db.Column(db.String(5), default="4.7.0")
    
    # Relationships
    lineas = db.relationship('AlbaranLinea', 
                           backref='cabecera', 
                           lazy='dynamic',
                           cascade="all, delete-orphan",
                           primaryjoin="and_(AlbaranCabecera.IdAlbaran == foreign(AlbaranLinea.IdAlbaran), "
                                      "AlbaranCabecera.IdEmpresa == foreign(AlbaranLinea.IdEmpresa), "
                                      "AlbaranCabecera.IdTienda == foreign(AlbaranLinea.IdTienda), "
                                      "AlbaranCabecera.IdBalanzaMaestra == foreign(AlbaranLinea.IdBalanzaMaestra), "
                                      "AlbaranCabecera.IdBalanzaEsclava == foreign(AlbaranLinea.IdBalanzaEsclava), "
                                      "AlbaranCabecera.TipoVenta == foreign(AlbaranLinea.TipoVenta))")
    
    def __repr__(self):
        return f'<AlbaranCabecera {self.IdAlbaran}: Cliente {self.IdCliente}>'


class AlbaranLinea(db.Model):
    __tablename__ = 'dat_albaran_linea'
    
    IdLineaAlbaran = db.Column(db.Integer, primary_key=True)
    IdEmpresa = db.Column(db.Integer, primary_key=True, default=1)
    IdTienda = db.Column(db.Integer, primary_key=True, default=1)
    IdBalanzaMaestra = db.Column(db.Integer, primary_key=True, default=1)
    IdBalanzaEsclava = db.Column(db.Integer, primary_key=True, default=-1)
    IdAlbaran = db.Column(db.BigInteger, primary_key=True, default=0)
    TipoVenta = db.Column(db.Integer, primary_key=True, default=2)
    EstadoLinea = db.Column(db.SmallInteger, default=0)
    IdArticulo = db.Column(db.Integer)
    Descripcion = db.Column(db.String(100))
    Descripcion1 = db.Column(db.String(100))
    Comportamiento = db.Column(db.SmallInteger, default=0)
    ComportamientoDevolucion = db.Column(db.SmallInteger, default=0)
    EntradaManual = db.Column(db.Boolean, default=0)
    Tara = db.Column(db.Numeric(11, 3), default=0)
    TaraPreprogramada = db.Column(db.SmallInteger)
    Peso = db.Column(db.Float(15, 3), default=1)
    PesoBruto = db.Column(db.Float(15, 3))
    PesoEmbalaje = db.Column(db.Float(15, 3))
    PesoRegalado = db.Column(db.Float(15, 3))
    PesoNetoNoEscurrido = db.Column(db.Float(15, 3))
    ValorTaraPorcentual = db.Column(db.Float(15, 3))
    TaraNoEscurrida = db.Column(db.Float(15, 3))
    DetalleTara = db.Column(db.Text)
    Cantidad2 = db.Column(db.Float(15, 3))
    Cantidad2Regalada = db.Column(db.Float(15, 3))
    Medida2 = db.Column(db.String(10), default="un")
    PrecioPorCienGramos = db.Column(db.Boolean, default=0)
    Precio = db.Column(db.Float(15, 3), default=0)
    PrecioSinOferta = db.Column(db.Float(15, 3))
    PrecioSinIVA = db.Column(db.Numeric(12, 6), default=0)
    PrecioConIVASinDtoL = db.Column(db.Float(15, 3))
    IdIVA = db.Column(db.Integer)
    PorcentajeIVA = db.Column(db.Numeric(11, 3), default=0)
    RecargoEquivalencia = db.Column(db.Float(9, 3), default=0)
    Descuento = db.Column(db.Float(9, 5), default=0)
    TipoDescuento = db.Column(db.Integer, default=1)
    Importe = db.Column(db.Float(15, 3), default=0)
    ImporteSinOferta = db.Column(db.Float(15, 3))
    ImporteSinIVASinDtoL = db.Column(db.Numeric(12, 6), default=0)
    ImporteConIVASinDtoL = db.Column(db.Float(15, 3))
    ImporteSinIVAConDtoL = db.Column(db.Numeric(12, 6), default=0)
    ImporteDelIVAConDtoL = db.Column(db.Float(15, 3), default=0)
    ImporteSinIVAConDtoLConDtoTotal = db.Column(db.Float(15, 3), default=0)
    ImporteDelIVAConDtoLConDtoTotal = db.Column(db.Float(15, 3), default=0)
    ImporteDelRE = db.Column(db.Float(15, 3), default=0)
    ImporteDelDescuento = db.Column(db.Float(15, 3), default=0)
    ImporteConDtoTotal = db.Column(db.Float(15, 3), default=0)
    TaraFija = db.Column(db.Numeric(11, 3))
    TaraPorcentual = db.Column(db.Numeric(11, 3))
    DiasCaducidad = db.Column(db.Integer)
    HorasCaducidad = db.Column(db.Integer)
    FechaCaducidad = db.Column(db.DateTime)
    DiasExtra = db.Column(db.Integer)
    HorasExtra = db.Column(db.Integer)
    FechaExtra = db.Column(db.DateTime)
    DiasEnvasado = db.Column(db.Integer)
    HorasEnvasado = db.Column(db.Integer)
    FechaEnvasado = db.Column(db.DateTime)
    DiasCongelacion = db.Column(db.Integer)
    HorasCongelacion = db.Column(db.Integer)
    FechaCongelacion = db.Column(db.DateTime)
    DiasConsumo = db.Column(db.Integer)
    HorasConsumo = db.Column(db.Integer)
    FechaConsumo = db.Column(db.DateTime)
    DiasFabricacion = db.Column(db.Integer)
    HorasFabricacion = db.Column(db.Integer)
    FechaFabricacion = db.Column(db.DateTime)
    LogoEtiqueta = db.Column(db.String(1000))
    CodInterno = db.Column(db.Integer)
    EANScannerArticulo = db.Column(db.String(20))
    TextoLote = db.Column(db.Text)
    IdClase = db.Column(db.Integer)
    NombreClase = db.Column(db.String(25), default="ARTICOLI")
    IdElemAsociado = db.Column(db.BigInteger)
    NombreElemAsociado = db.Column(db.String(25))
    IdFamilia = db.Column(db.Integer)
    NombreFamilia = db.Column(db.String(25))
    IdSeccion = db.Column(db.Integer)
    NombreSeccion = db.Column(db.String(30))
    IdSubFamilia = db.Column(db.Integer)
    NombreSubFamilia = db.Column(db.String(25))
    IdDepartamento = db.Column(db.Integer)
    NombreDepartamento = db.Column(db.String(25))
    Texto1 = db.Column(db.Text)
    Texto2 = db.Column(db.Text)
    Texto3 = db.Column(db.Text)
    Texto4 = db.Column(db.Text)
    Texto5 = db.Column(db.Text)
    Texto6 = db.Column(db.Text)
    Texto7 = db.Column(db.Text)
    Texto8 = db.Column(db.Text)
    Texto9 = db.Column(db.Text)
    Texto10 = db.Column(db.Text)
    Texto11 = db.Column(db.Text)
    Texto12 = db.Column(db.Text)
    Texto13 = db.Column(db.Text)
    Texto14 = db.Column(db.Text)
    Texto15 = db.Column(db.Text)
    Texto16 = db.Column(db.Text)
    Texto17 = db.Column(db.Text)
    Texto18 = db.Column(db.Text)
    Texto19 = db.Column(db.Text)
    Texto20 = db.Column(db.Text)
    TextoLibre = db.Column(db.Text)
    PesoPieza = db.Column(db.Numeric(11, 3))
    UnidadesCaja = db.Column(db.Integer)
    Facturada = db.Column(db.Boolean, default=0)
    IdCampania = db.Column(db.Integer)
    NombreCampania = db.Column(db.String(50))
    IdArticuloVisualizado = db.Column(db.Integer)
    ProductoEnPromocion = db.Column(db.Boolean)
    CantidadFacturada = db.Column(db.Float(15, 3), default=0)
    CantidadFacturada2 = db.Column(db.Float(15, 3), default=0)
    NombrePlataforma = db.Column(db.String(50))
    HayTaraAplicada = db.Column(db.SmallInteger, default=0)
    Modificado = db.Column(db.Boolean, default=1)
    Operacion = db.Column(db.String(1), default="A")
    Usuario = db.Column(db.String(20))
    TimeStamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AlbaranLinea {self.IdLineaAlbaran}: Articulo {self.IdArticulo}>'


class Article(Product):
    """This is an alias for the Product model that points to the same database table."""
    
    # Add fields needed by the form that aren't in Product
    Descripcion1 = db.Column(db.String(100))
    IdTipo = db.Column(db.Integer, default=1)
    IdDepartamento = db.Column(db.Integer)
    IdSeccion = db.Column(db.Integer)
    Favorito = db.Column(db.Boolean, default=1)
    PesoMinimo = db.Column(db.Float)
    PesoMaximo = db.Column(db.Float)
    PesoObjetivo = db.Column(db.Float)
    FechaCaducidadActivada = db.Column(db.Boolean, default=1)
    DiasCaducidad = db.Column(db.Integer)
    # PrecioSinIVA è ereditato dalla classe Product
    Texto1 = db.Column(db.Text)
    TextoLibre = db.Column(db.Text)
    StockActual = db.Column(db.Float)
    EnVenta = db.Column(db.Boolean, default=1)
    IncluirGestionStock = db.Column(db.Boolean, default=1)
    IdClase = db.Column(db.Integer)
    IdEmpresa = db.Column(db.Integer, default=1)
    Usuario = db.Column(db.String(20))
    TimeStamp = db.Column(db.DateTime, default=datetime.utcnow)
    Marca = db.Column(db.Integer, default=1)
    Modificado = db.Column(db.Boolean)
    Operacion = db.Column(db.String(1))
    LogoPantalla = db.Column(db.String(1000))
    
    # Add non-database attributes for the form
    # These will not be queried from or saved to the database
    # But they will be available as properties in Python code
    _Texto2 = None
    _Texto3 = None
    _Texto4 = None
    _Texto5 = None
    _Texto6 = None
    _Texto7 = None
    _Texto8 = None
    _Texto9 = None
    _Texto10 = None
    _Texto11 = None
    _Texto12 = None
    _Texto13 = None
    _Texto14 = None
    _Texto15 = None
    _Texto16 = None
    _Texto17 = None
    _Texto18 = None
    _Texto19 = None
    _Texto20 = None
    
    # Property accessors for non-database fields
    @property
    def Texto2(self):
        return self._Texto2
    
    @Texto2.setter
    def Texto2(self, value):
        self._Texto2 = value
    
    @property
    def Texto3(self):
        return self._Texto3
    
    @Texto3.setter
    def Texto3(self, value):
        self._Texto3 = value
    
    @property
    def Texto4(self):
        return self._Texto4
    
    @Texto4.setter
    def Texto4(self, value):
        self._Texto4 = value
    
    @property
    def Texto5(self):
        return self._Texto5
    
    @Texto5.setter
    def Texto5(self, value):
        self._Texto5 = value
    
    @property
    def Texto6(self):
        return self._Texto6
    
    @Texto6.setter
    def Texto6(self, value):
        self._Texto6 = value
    
    @property
    def Texto7(self):
        return self._Texto7
    
    @Texto7.setter
    def Texto7(self, value):
        self._Texto7 = value
    
    @property
    def Texto8(self):
        return self._Texto8
    
    @Texto8.setter
    def Texto8(self, value):
        self._Texto8 = value
    
    @property
    def Texto9(self):
        return self._Texto9
    
    @Texto9.setter
    def Texto9(self, value):
        self._Texto9 = value
    
    @property
    def Texto10(self):
        return self._Texto10
    
    @Texto10.setter
    def Texto10(self, value):
        self._Texto10 = value
    
    @property
    def Texto11(self):
        return self._Texto11
    
    @Texto11.setter
    def Texto11(self, value):
        self._Texto11 = value
    
    @property
    def Texto12(self):
        return self._Texto12
    
    @Texto12.setter
    def Texto12(self, value):
        self._Texto12 = value
    
    @property
    def Texto13(self):
        return self._Texto13
    
    @Texto13.setter
    def Texto13(self, value):
        self._Texto13 = value
    
    @property
    def Texto14(self):
        return self._Texto14
    
    @Texto14.setter
    def Texto14(self, value):
        self._Texto14 = value
    
    @property
    def Texto15(self):
        return self._Texto15
    
    @Texto15.setter
    def Texto15(self, value):
        self._Texto15 = value
    
    @property
    def Texto16(self):
        return self._Texto16
    
    @Texto16.setter
    def Texto16(self, value):
        self._Texto16 = value
    
    @property
    def Texto17(self):
        return self._Texto17
    
    @Texto17.setter
    def Texto17(self, value):
        self._Texto17 = value
    
    @property
    def Texto18(self):
        return self._Texto18
    
    @Texto18.setter
    def Texto18(self, value):
        self._Texto18 = value
    
    @property
    def Texto19(self):
        return self._Texto19
    
    @Texto19.setter
    def Texto19(self, value):
        self._Texto19 = value
    
    @property
    def Texto20(self):
        return self._Texto20
    
    @Texto20.setter
    def Texto20(self, value):
        self._Texto20 = value
    
    # Correctly map IdIVA to match case in database
    @property
    def IdIVA(self):
        return self.IdIva
    
    @IdIVA.setter
    def IdIVA(self, value):
        self.IdIva = value
    
    def __repr__(self):
        return f'<Article {self.IdArticulo}: {self.Descripcion}>'

class Section(db.Model):
    """Model representing the dat_seccion table."""
    __tablename__ = 'dat_seccion'
    
    IdSeccion = db.Column(db.Integer, primary_key=True)
    NombreSeccion = db.Column(db.String(50), nullable=False)
    IdLogo = db.Column(db.Integer, nullable=True)
    Imagen = db.Column(db.LargeBinary, nullable=True)
    FtoTarjetaArticuloA = db.Column(db.Integer, nullable=True)
    FtoTarjetaArticuloB = db.Column(db.Integer, nullable=True)
    IdEmpresa = db.Column(db.Integer, primary_key=True, default=1)
    IdSeccionCliente = db.Column(db.Integer, nullable=True)
    Modificado = db.Column(db.Boolean, nullable=True)
    Operacion = db.Column(db.String(1), nullable=True)
    Usuario = db.Column(db.String(20), nullable=True)
    TimeStamp = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Section {self.IdSeccion}: {self.NombreSeccion}>'

class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(50), unique=True, nullable=False)
    config_value = db.Column(db.String(255))
    description = db.Column(db.String(255))
    data_type = db.Column(db.String(20), default='string')  # string, integer, boolean, float
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemConfig {self.config_key}: {self.config_value}>'
    
    def get_typed_value(self):
        """Restituisce il valore con il tipo corretto"""
        if self.data_type == 'integer':
            return int(self.config_value) if self.config_value else 0
        elif self.data_type == 'boolean':
            return self.config_value.lower() in ('true', '1', 'yes') if self.config_value else False
        elif self.data_type == 'float':
            return float(self.config_value) if self.config_value else 0.0
        else:
            return self.config_value or ''
    
    @staticmethod
    def get_config(key, default=None):
        """Ottiene un valore di configurazione"""
        config = SystemConfig.query.filter_by(config_key=key).first()
        if config:
            return config.get_typed_value()
        return default
    
    @staticmethod
    def set_config(key, value, description=None, data_type='string'):
        """Imposta un valore di configurazione"""
        config = SystemConfig.query.filter_by(config_key=key).first()
        if config:
            config.config_value = str(value)
            config.updated_at = datetime.utcnow()
            if description:
                config.description = description
            if data_type:
                config.data_type = data_type
        else:
            config = SystemConfig(
                config_key=key,
                config_value=str(value),
                description=description,
                data_type=data_type
            )
            db.session.add(config)
        db.session.commit()
        return config 
    
class ChatMessage(db.Model):
    """Model for chat messages"""
    __tablename__ = 'chat_message'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('chat_messages', lazy='dynamic'))
    room = db.relationship('ChatRoom', backref=db.backref('messages', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'is_read': self.is_read,
            'formatted_time': self.timestamp.strftime('%H:%M'),
            'room_id': self.room_id
        }
    
    def __repr__(self):
        return f'<ChatMessage {self.id}: {self.user.username}>'


class ChatRoom(db.Model):
    """Model for chat rooms (for future expansion to private chats)"""
    __tablename__ = 'chat_room'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_global = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationship
    creator = db.relationship('User', backref=db.backref('created_rooms', lazy='dynamic'))
    
    def __repr__(self):
        return f'<ChatRoom {self.id}: {self.name}>'
    

class Task(db.Model):
    """Model for task management"""
    __tablename__ = 'tasks'
    
    id_task = db.Column(db.Integer, primary_key=True)
    task_number = db.Column(db.String(20), unique=True, nullable=False)  # Unique task number
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, assigned
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    deadline = db.Column(db.DateTime)
    priority = db.Column(db.String(10), default='medium')  # low, medium, high, urgent
    
    # Progress tracking
    total_tickets = db.Column(db.Integer, default=0)
    completed_tickets = db.Column(db.Integer, default=0)
    
    # DDT generation fields
    client_id = db.Column(db.Integer, db.ForeignKey('dat_cliente.IdCliente'))
    ddt_generated = db.Column(db.Boolean, default=False)
    ddt_id = db.Column(db.BigInteger)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref=db.backref('created_tasks', lazy='dynamic'))
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref=db.backref('assigned_tasks', lazy='dynamic'))
    client = db.relationship('Client', backref=db.backref('tasks', lazy='dynamic'))
    task_tickets = db.relationship('TaskTicket', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage including both tickets and preparation items"""
        total_items = self.total_tickets + self.total_preparation_items
        if total_items == 0:
            return 0
        completed_items = self.completed_tickets + self.completed_preparation_items
        return int((completed_items / total_items) * 100)
    
    @property
    def total_preparation_items(self):
        """Total number of preparation items"""
        return self.preparation_items.count()
    
    @property
    def completed_preparation_items(self):
        """Number of completed preparation items"""
        return self.preparation_items.filter(TaskPreparationItem.status.in_(['prepared', 'completed'])).count()
    
    @property
    def is_completed(self):
        """Check if task is completed (both tickets and preparation items)"""
        tickets_completed = (self.total_tickets == 0) or (self.completed_tickets == self.total_tickets)
        prep_items_completed = (self.total_preparation_items == 0) or (self.completed_preparation_items == self.total_preparation_items)
        return self.status == 'completed' and tickets_completed and prep_items_completed
    
    @property
    def is_overdue(self):
        """Check if task is overdue (deadline passed and not completed)
        
        A task is only considered overdue if the deadline date has passed
        (not if it's today - so a task can be opened and closed on the same day)
        """
        if not self.deadline:
            return False
        today = datetime.utcnow().date()
        deadline_date = self.deadline.date()
        return deadline_date < today and self.status != 'completed'
    
    def update_progress(self):
        """Update the progress counters including preparation items"""
        # Update ticket progress
        completed_tickets = self.task_tickets.filter_by(status='completed').count()
        total_tickets = self.task_tickets.count()
        
        self.completed_tickets = completed_tickets
        self.total_tickets = total_tickets
        
        # Calculate total progress including preparation items
        completed_prep_items = self.completed_preparation_items
        total_prep_items = self.total_preparation_items
        
        total_items = total_tickets + total_prep_items
        completed_items = completed_tickets + completed_prep_items
        
        # Auto-update status based on progress
        if total_items == 0:
            self.status = 'pending'
        elif completed_items == total_items and total_items > 0:
            self.status = 'completed'
            if not self.completed_at:
                self.completed_at = datetime.utcnow()
        elif completed_items > 0:
            self.status = 'in_progress'
        
        db.session.commit()
    
    def generate_task_number(self):
        """Generate a unique task number"""
        from datetime import datetime
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Find the highest task number for today
        existing_tasks = Task.query.filter(Task.task_number.like(f'TASK-{date_str}-%')).all()
        
        if not existing_tasks:
            sequence = 1
        else:
            sequences = []
            for task in existing_tasks:
                try:
                    seq_part = task.task_number.split('-')[-1]
                    sequences.append(int(seq_part))
                except (ValueError, IndexError):
                    continue
            
            sequence = max(sequences) + 1 if sequences else 1
        
        return f'TASK-{date_str}-{sequence:04d}'
    
    def __repr__(self):
        return f'<Task {self.id_task}: {self.task_number}>'


class TaskTicket(db.Model):
    """Model for associating tickets with tasks"""
    __tablename__ = 'task_tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id_task'), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('dat_ticket_cabecera.IdTicket'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, verified
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    
    # Scan tracking
    total_items = db.Column(db.Integer, default=0)
    scanned_items = db.Column(db.Integer, default=0)
    
    # Relationships
    ticket = db.relationship('TicketHeader', backref=db.backref('task_assignments', lazy='dynamic'))
    verifier = db.relationship('User', backref=db.backref('verified_task_tickets', lazy='dynamic'))
    scan_results = db.relationship('TaskTicketScan', backref='task_ticket', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def scan_progress_percentage(self):
        if self.total_items is None or self.total_items == 0:
            return 0
        scanned = self.scanned_items or 0
        return int((scanned / self.total_items) * 100)
    
    @property
    def is_scan_completed(self):
        total = self.total_items or 0
        scanned = self.scanned_items or 0
        return total > 0 and scanned >= total
    
    def update_scan_progress(self):
        """Update scan progress from ticket lines"""
        if self.ticket:
            self.total_items = self.ticket.lines.count()
            self.scanned_items = self.scan_results.filter_by(status='success').count()
            
            # Auto-update status based on scan progress
            if self.is_scan_completed and self.status != 'completed':
                self.status = 'completed'
                self.completed_at = datetime.utcnow()
            elif self.scanned_items > 0 and self.status == 'pending':
                self.status = 'in_progress'
                self.started_at = datetime.utcnow()
        
        db.session.commit()
    
    def __repr__(self):
        return f'<TaskTicket {self.id}: Task {self.task_id} - Ticket {self.ticket_id}>'


class TaskTicketScan(db.Model):
    """Model for tracking individual product scans within task tickets"""
    __tablename__ = 'task_ticket_scans'
    
    id = db.Column(db.Integer, primary_key=True)
    task_ticket_id = db.Column(db.Integer, db.ForeignKey('task_tickets.id'), nullable=False)
    ticket_line_id = db.Column(db.Integer, db.ForeignKey('dat_ticket_linea.IdLineaTicket'))
    product_id = db.Column(db.Integer, db.ForeignKey('dat_articulo.IdArticulo'))
    scanned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Scan data
    scanned_code = db.Column(db.String(100))  # The QR code that was scanned
    expected_code = db.Column(db.String(100))  # The expected QR code from ticket line
    status = db.Column(db.String(20), default='pending')  # success, error, mismatch
    error_message = db.Column(db.Text)
    
    # Timestamps
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Additional verification data
    weight_expected = db.Column(db.Numeric(15, 3))
    weight_scanned = db.Column(db.Numeric(15, 3))
    expiry_date_expected = db.Column(db.DateTime)
    expiry_date_scanned = db.Column(db.DateTime)
    
    # Relationships
    ticket_line = db.relationship('TicketLine', backref=db.backref('scan_results', lazy='dynamic'))
    product = db.relationship('Product', backref=db.backref('task_scans', lazy='dynamic'))
    scanner = db.relationship('User', backref=db.backref('performed_scans', lazy='dynamic'))
    
    @property
    def is_match(self):
        return self.status == 'success'
    
    @property
    def formatted_status(self):
        status_map = {
            'success': 'Verificato ✓',
            'error': 'Errore ✗',
            'mismatch': 'Non corrispondente ⚠',
            'pending': 'In attesa...'
        }
        return status_map.get(self.status, self.status)
    
    def __repr__(self):
        return f'<TaskTicketScan {self.id}: {self.status}>'


class TaskNotification(db.Model):
    """Model for task-related notifications"""
    __tablename__ = 'task_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id_task'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # task_assigned, task_completed, task_updated
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    task = db.relationship('Task', backref=db.backref('notifications', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('task_notifications', lazy='dynamic'))
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<TaskNotification {self.id}: {self.title}>'


class TaskPreparationItem(db.Model):
    """Model for preparation items (products not in warehouse) in tasks"""
    __tablename__ = 'task_preparation_items'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id_task'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('dat_articulo.IdArticulo'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Numeric(15, 3), nullable=False, default=1.000)
    unit_price = db.Column(db.Numeric(15, 3), nullable=False, default=0.000)
    total_price = db.Column(db.Numeric(15, 3), nullable=False, default=0.000)
    status = db.Column(db.String(20), default='pending')  # pending, prepared, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    prepared_at = db.Column(db.DateTime)
    prepared_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    
    # Relationships
    task = db.relationship('Task', backref=db.backref('preparation_items', lazy='dynamic'))
    product = db.relationship('Product', backref=db.backref('preparation_items', lazy='dynamic'))
    preparer = db.relationship('User', backref=db.backref('prepared_items', lazy='dynamic'))
    
    @property
    def is_prepared(self):
        """Check if the item has been marked as prepared"""
        return self.status in ['prepared', 'completed']
    
    @property
    def is_completed(self):
        """Check if the item has been completed"""
        return self.status == 'completed'
    
    @property
    def status_text(self):
        """Get human readable status"""
        status_map = {
            'pending': 'In attesa',
            'prepared': 'Preparato',
            'completed': 'Completato'
        }
        return status_map.get(self.status, 'Sconosciuto')
    
    @property
    def status_class(self):
        """Get CSS class for status badge"""
        status_classes = {
            'pending': 'warning',
            'prepared': 'info', 
            'completed': 'success'
        }
        return status_classes.get(self.status, 'secondary')
        
    def mark_as_prepared(self, user_id):
        """Mark the item as prepared"""
        self.status = 'prepared'
        self.prepared_at = datetime.utcnow()
        self.prepared_by = user_id
    
    def mark_as_completed(self):
        """Mark the item as completed"""
        self.status = 'completed'
    
    def calculate_total_price(self):
        """Calculate total price based on quantity and unit price"""
        self.total_price = self.quantity * self.unit_price
    
    def __repr__(self):
        return f'<TaskPreparationItem {self.id}: Task {self.task_id}, Product {self.product_name}>'


class ListinoPrezziHeader(db.Model):
    """Model per la testata dei listini prezzi"""
    __tablename__ = 'price_list_header'
    
    IdListino = db.Column(db.Integer, primary_key=True, autoincrement=True)
    NomeListino = db.Column(db.String(100), nullable=False)
    Descrizione = db.Column(db.Text)
    DataCreazione = db.Column(db.DateTime, default=None)
    DataModifica = db.Column(db.DateTime, default=None)
    Attivo = db.Column(db.Boolean, default=True)
    CreatoDA = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    righe = db.relationship('ListinoPrezziRiga', backref='listino_header', lazy='dynamic', cascade='all, delete-orphan')
    creatore = db.relationship('User', backref='listini_creati')
    
    def __repr__(self):
        return f'<ListinoPrezziHeader {self.IdListino}: {self.NomeListino}>'
    
    @property
    def numero_articoli(self):
        """Restituisce il numero di articoli nel listino"""
        return self.righe.count()
    
    @property
    def data_creazione_formatted(self):
        """Restituisce la data di creazione formattata"""
        if self.DataCreazione:
            return self.DataCreazione.strftime('%d/%m/%Y %H:%M')
        return 'N/A'
    
    @property
    def data_modifica_formatted(self):
        """Restituisce la data di modifica formattata"""
        if self.DataModifica:
            return self.DataModifica.strftime('%d/%m/%Y %H:%M')
        return 'N/A'


class ListinoPrezziRiga(db.Model):
    """Model per le righe dei listini prezzi"""
    __tablename__ = 'price_list_line'
    
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    IdListino = db.Column(db.Integer, db.ForeignKey('price_list_header.IdListino'), nullable=False)
    IdArticolo = db.Column(db.Integer, db.ForeignKey('dat_articulo.IdArticulo'), nullable=False)
    Prezzo = db.Column(db.Numeric(15, 3), nullable=False)
    DataCreazione = db.Column(db.DateTime, default=None)
    DataModifica = db.Column(db.DateTime, default=None)
    
    # Relationships
    articolo = db.relationship('Product', backref='righe_listino')
    
    def __repr__(self):
        return f'<ListinoPrezziRiga {self.Id}: Listino {self.IdListino}, Articolo {self.IdArticolo}, Prezzo {self.Prezzo}>'
    
    @property
    def prezzo_formatted(self):
        """Restituisce il prezzo formattato con 3 decimali"""
        return f"{float(self.Prezzo):.3f}"
    
    @property
    def descrizione_articolo(self):
        """Restituisce la descrizione dell'articolo"""
        return self.articolo.Descripcion if self.articolo else 'Articolo non trovato' 





# ===========================================
# MODELLI FATTURE ELETTRONICHE - TABELLE ESISTENTI
# ===========================================

class FatturaCabecera(db.Model):
    """Modello per la testata delle fatture (dat_factura_cabecera)"""
    __tablename__ = 'dat_factura_cabecera'
    
    IdFactura = db.Column(db.Integer, primary_key=True)
    NumFactura = db.Column(db.String(20))
    IdEmpresa = db.Column(db.Integer)
    NombreEmpresa = db.Column(db.String(100))
    CIF_VAT_Empresa = db.Column(db.String(20))
    DireccionEmpresa = db.Column(db.String(200))
    PoblacionEmpresa = db.Column(db.String(100))
    CPEmpresa = db.Column(db.String(10))
    TelefonoEmpresa = db.Column(db.String(20))
    ProvinciaEmpresa = db.Column(db.String(100))
    AuditFileVersion = db.Column(db.String(10))
    IdTienda = db.Column(db.Integer)
    NombreTienda = db.Column(db.String(100))
    IdTiendaCreacion = db.Column(db.Integer)
    NombreTiendaCreacion = db.Column(db.String(100))
    IdBalanzaMaestra = db.Column(db.Integer)
    NombreBalanzaMaestra = db.Column(db.String(100))
    IdBalanzaEsclava = db.Column(db.Integer)
    NombreBalanzaEsclava = db.Column(db.String(100))
    IdVendedor = db.Column(db.Integer)
    NombreVendedor = db.Column(db.String(100))
    IdCliente = db.Column(db.Integer, db.ForeignKey('dat_cliente.IdCliente'))
    NombreCliente = db.Column(db.String(100))
    DNICliente = db.Column(db.String(20))
    EmailCliente = db.Column(db.String(100))
    DireccionCliente = db.Column(db.String(200))
    PoblacionCliente = db.Column(db.String(100))
    ProvinciaCliente = db.Column(db.String(100))
    PaisCliente = db.Column(db.String(100))
    CPCliente = db.Column(db.String(10))
    TelefonoCliente = db.Column(db.String(20))
    ObservacionesCliente = db.Column(db.Text)
    EANCliente = db.Column(db.String(50))
    ReferenciaDocumento = db.Column(db.String(100))
    ObservacionesDocumento = db.Column(db.Text)
    
    # Pagamento
    DtoProntoPago = db.Column(db.Numeric(5, 2))
    NumeroVencimientos = db.Column(db.Integer)
    DiasEntreVencimientos = db.Column(db.Integer)
    TotalPorArticulo = db.Column(db.Integer)
    
    # Importi e totali
    ImporteLineas = db.Column(db.Numeric(10, 2))
    PorcDescuento = db.Column(db.Numeric(5, 2))
    ImporteDescuento = db.Column(db.Numeric(10, 2))
    ImporteDescuentoPP = db.Column(db.Numeric(10, 2))
    ImporteTotalConDtoTotal = db.Column(db.Numeric(10, 2))
    ImporteTotalConDtoTotalConDtoPP = db.Column(db.Numeric(10, 2))
    ImporteRE = db.Column(db.Numeric(10, 2))
    ImporteTotalSinRE = db.Column(db.Numeric(10, 2))
    ImporteTotalSinIVAConDtoL = db.Column(db.Numeric(10, 2))
    ImporteTotalSinIVAConDtoLConDtoTotalConDtoPPConRE = db.Column(db.Numeric(10, 2))
    ImporteTotalSinIVAConDtoLConDtoTotalConDtoPP = db.Column(db.Numeric(10, 2))
    ImporteTotalSinIVAConDtoLConDtoTotal = db.Column(db.Numeric(10, 2))
    ImporteDtoTotalSinIVA = db.Column(db.Numeric(10, 2))
    ImporteTotalDelIVAConDtoLConDtoTotal = db.Column(db.Numeric(10, 2))
    ImporteTotalDelIVAConDtoLConDtoTotalConDtoPP = db.Column(db.Numeric(10, 2))
    ImporteSinRedondeo = db.Column(db.Numeric(10, 2))
    ImporteDelRedondeo = db.Column(db.Numeric(10, 2))
    
    # Date e riferimenti
    Fecha = db.Column(db.Date)
    FechaOperacion = db.Column(db.Date)
    FechaAnulacion = db.Column(db.Date)
    IdFactura_Original = db.Column(db.Integer)
    NumFactura_Original = db.Column(db.String(20))
    MotivoAnulacion = db.Column(db.String(200))
    Tipo = db.Column(db.String(10))
    FechaModificacion = db.Column(db.DateTime)
    NumLineas = db.Column(db.Integer)
    CodigoBarras = db.Column(db.String(100))
    
    # Tariffe
    IdTarifa = db.Column(db.Integer)
    NombreTarifa = db.Column(db.String(100))
    DescuentoTarifa = db.Column(db.Numeric(5, 2))
    TipoTarifa = db.Column(db.String(20))
    FechaInicioTarifa = db.Column(db.Date)
    FechaFinTarifa = db.Column(db.Date)
    
    # Controlli e gestione
    CodigoHash = db.Column(db.String(100))
    EstadoFactura = db.Column(db.String(20))
    ImporteSolicitado = db.Column(db.Numeric(10, 2))
    ImporteEntregado = db.Column(db.Numeric(10, 2))
    ImporteDevuelto = db.Column(db.Numeric(10, 2))
    PuntosFidelidad = db.Column(db.Integer)
    PuntosFidelidadTotales = db.Column(db.Integer)
    REAplicado = db.Column(db.Integer)
    IdBotonVendedor = db.Column(db.Integer)
    UsuarioAnulacion = db.Column(db.String(50))
    
    # Audit
    Version = db.Column(db.Integer)
    Modificado = db.Column(db.Integer)
    Operacion = db.Column(db.Integer)
    Usuario = db.Column(db.String(50))
    TimeStamp = db.Column(db.DateTime)
    
    # Campi TicketBai
    TB_TBAI = db.Column(db.String(50))
    TB_NumSerieBalanza = db.Column(db.String(20))
    TB_SerieFactura = db.Column(db.String(20))
    TB_TipoFactura = db.Column(db.String(10))
    TB_FacturaRectificada = db.Column(db.String(50))
    TB_FacturaAnulada = db.Column(db.String(50))
    TB_ContenidoQR = db.Column(db.Text)
    TB_IdentificativoTB = db.Column(db.String(50))
    TB_IdfacturaAnt = db.Column(db.Integer)
    TB_TipoFacturaAnt = db.Column(db.String(10))
    TB_IdfacturaRec = db.Column(db.Integer)
    TB_TipoFacturaRec = db.Column(db.String(10))
    TB_TipoRectificacion = db.Column(db.String(10))
    TB_CodigoRectificacion = db.Column(db.String(10))
    TB_FacturaSustitutiva = db.Column(db.String(50))
    IdNegativaAuxiliar = db.Column(db.Integer)
    
    # Relationships
    cliente = db.relationship('Client', backref='fatture', lazy='select')
    linee = db.relationship('FatturaLinea', backref='fattura', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Fattura {self.NumFactura}: {self.NombreCliente}>'
    
    @property
    def numero_linee(self):
        """Ritorna il numero di linee della fattura"""
        return self.linee.count()
    
    @property
    def stato_display(self):
        """Ritorna lo stato in formato leggibile"""
        stati = {
            'G': 'Generata',
            'I': 'Inviata',
            'P': 'Pagata',
            'A': 'Annullata',
            'C': 'Completata'
        }
        return stati.get(self.EstadoFactura, self.EstadoFactura or 'Non definito')
    
    @property 
    def tipo_documento_display(self):
        """Ritorna il tipo documento in formato leggibile"""
        if self.Tipo == '24':
            return 'Fattura Differita'
        elif self.Tipo == '01':
            return 'Fattura'
        return self.Tipo or 'Fattura'
    
    @property
    def importo_totale(self):
        """Ritorna l'importo totale della fattura (imponibile + IVA)"""
        # Usa ImporteTotalSinRE che contiene imponibile + IVA, non solo l'imponibile
        return float(self.ImporteTotalSinRE or 0)
    
    @property
    def importo_imponibile(self):
        """Ritorna l'importo imponibile"""
        return float(self.ImporteTotalSinIVAConDtoLConDtoTotalConDtoPP or 0)
    
    @property
    def importo_iva(self):
        """Ritorna l'importo IVA"""
        return float(self.ImporteTotalDelIVAConDtoLConDtoTotalConDtoPP or 0)
    
    @property
    def numero_fattura(self):
        """Alias per NumFactura"""
        return self.NumFactura
        
    @property
    def data_fattura(self):
        """Alias per Fecha"""
        return self.Fecha
        
    @property
    def nome_cliente(self):
        """Alias per NombreCliente"""
        return self.NombreCliente


class FatturaLinea(db.Model):
    """Modello per le linee delle fatture (dat_factura_linea)"""
    __tablename__ = 'dat_factura_linea'
    
    IdLineaFactura = db.Column(db.Integer, primary_key=True)
    IdLineaFactura_Original = db.Column(db.Integer)
    IdEmpresa = db.Column(db.Integer)
    IdTienda = db.Column(db.Integer)
    IdTiendaCreacion = db.Column(db.Integer)
    IdBalanzaMaestra = db.Column(db.Integer)
    IdBalanzaEsclava = db.Column(db.Integer)
    IdBalanzaMaestraOrigen = db.Column(db.Integer)
    IdBalanzaEsclavaOrigen = db.Column(db.Integer)
    IdFactura = db.Column(db.Integer, db.ForeignKey('dat_factura_cabecera.IdFactura'), nullable=False)
    
    # Tipo e origine
    TipoVenta = db.Column(db.String(20))
    TipoOrigen = db.Column(db.String(20))
    IdOrigen = db.Column(db.Integer)
    NumeroOrigen = db.Column(db.String(20))
    FechaOrigen = db.Column(db.Date)
    IdLineaOrigen = db.Column(db.Integer)
    
    # Dati articolo
    IdArticulo = db.Column(db.Integer, db.ForeignKey('dat_articulo.IdArticulo'))
    Descripcion = db.Column(db.String(100))
    Descripcion1 = db.Column(db.String(100))
    Comportamiento = db.Column(db.String(20))
    EntradaManual = db.Column(db.Integer)
    
    # Peso e quantità
    Tara = db.Column(db.Numeric(10, 3))
    TaraPreprogramada = db.Column(db.Numeric(10, 3))
    Peso = db.Column(db.Numeric(10, 3))
    PesoBruto = db.Column(db.Numeric(10, 3))
    PesoEmbalaje = db.Column(db.Numeric(10, 3))
    PesoRegalado = db.Column(db.Numeric(10, 3))
    PesoNetoNoEscurrido = db.Column(db.Numeric(10, 3))
    ValorTaraPorcentual = db.Column(db.Numeric(5, 2))
    TaraNoEscurrida = db.Column(db.Numeric(10, 3))
    DetalleTara = db.Column(db.String(200))
    Cantidad2 = db.Column(db.Numeric(10, 3))
    Cantidad2Regalada = db.Column(db.Numeric(10, 3))
    Medida2 = db.Column(db.String(10))
    PrecioPorCienGramos = db.Column(db.Numeric(10, 8))
    
    # Prezzi
    Precio = db.Column(db.Numeric(10, 8))
    PrecioSinOferta = db.Column(db.Numeric(10, 8))
    PrecioSinIVA = db.Column(db.Numeric(10, 8))
    PrecioConIVASinDtoL = db.Column(db.Numeric(10, 8))
    IdIVA = db.Column(db.Integer)
    PorcentajeIVA = db.Column(db.Numeric(5, 2))
    RecargoEquivalencia = db.Column(db.Numeric(5, 2))
    Descuento = db.Column(db.Numeric(5, 2))
    
    # Importi
    Importe = db.Column(db.Numeric(10, 2))
    ImporteSinOferta = db.Column(db.Numeric(10, 2))
    ImporteSinIVASinDtoL = db.Column(db.Numeric(10, 2))
    ImporteConIVASinDtoL = db.Column(db.Numeric(10, 2))
    ImporteSinIVAConDtoL = db.Column(db.Numeric(10, 2))
    ImporteDelIVAConDtoL = db.Column(db.Numeric(10, 2))
    ImporteSinIVAConDtoLConDtoTotal = db.Column(db.Numeric(10, 2))
    ImporteDelIVAConDtoLConDtoTotal = db.Column(db.Numeric(10, 2))
    ImporteSinIVAConDtoLConDtoTotalConDtoPP = db.Column(db.Numeric(10, 2))
    ImporteDelIVAConDtoLConDtoTotalConDtoPP = db.Column(db.Numeric(10, 2))
    ImporteDelRE = db.Column(db.Numeric(10, 2))
    ImporteDelDescuento = db.Column(db.Numeric(10, 2))
    ImporteConDtoTotalConDtoPP = db.Column(db.Numeric(10, 2))
    
    # Tara e date
    TaraFija = db.Column(db.Numeric(10, 3))
    TaraPorcentual = db.Column(db.Numeric(5, 2))
    DiasCaducidad = db.Column(db.Integer)
    HorasCaducidad = db.Column(db.Integer)
    FechaCaducidad = db.Column(db.Date)
    DiasExtra = db.Column(db.Integer)
    HorasExtra = db.Column(db.Integer)
    FechaExtra = db.Column(db.Date)
    DiasEnvasado = db.Column(db.Integer)
    HorasEnvasado = db.Column(db.Integer)
    FechaEnvasado = db.Column(db.Date)
    DiasCongelacion = db.Column(db.Integer)
    HorasCongelacion = db.Column(db.Integer)
    FechaCongelacion = db.Column(db.Date)
    DiasConsumo = db.Column(db.Integer)
    HorasConsumo = db.Column(db.Integer)
    FechaConsumo = db.Column(db.Date)
    DiasFabricacion = db.Column(db.Integer)
    HorasFabricacion = db.Column(db.Integer)
    FechaFabricacion = db.Column(db.Date)
    
    # Codici e classificazioni
    LogoEtiqueta = db.Column(db.String(100))
    CodInterno = db.Column(db.String(50))
    EANScannerArticulo = db.Column(db.String(50))
    TextoLote = db.Column(db.String(50))
    IdClase = db.Column(db.Integer)
    NombreClase = db.Column(db.String(100))
    IdElemAsociado = db.Column(db.Integer)
    NombreElemAsociado = db.Column(db.String(100))
    IdFamilia = db.Column(db.Integer)
    NombreFamilia = db.Column(db.String(100))
    IdSeccion = db.Column(db.Integer)
    NombreSeccion = db.Column(db.String(100))
    IdSubFamilia = db.Column(db.Integer)
    NombreSubFamilia = db.Column(db.String(100))
    IdDepartamento = db.Column(db.Integer)
    NombreDepartamento = db.Column(db.String(100))
    
    # Campi testo
    Texto1 = db.Column(db.String(100))
    Texto2 = db.Column(db.String(100))
    Texto3 = db.Column(db.String(100))
    Texto4 = db.Column(db.String(100))
    Texto5 = db.Column(db.String(100))
    Texto6 = db.Column(db.String(100))
    Texto7 = db.Column(db.String(100))
    Texto8 = db.Column(db.String(100))
    Texto9 = db.Column(db.String(100))
    Texto10 = db.Column(db.String(100))
    Texto11 = db.Column(db.String(100))
    Texto12 = db.Column(db.String(100))
    Texto13 = db.Column(db.String(100))
    Texto14 = db.Column(db.String(100))
    Texto15 = db.Column(db.String(100))
    Texto16 = db.Column(db.String(100))
    Texto17 = db.Column(db.String(100))
    Texto18 = db.Column(db.String(100))
    Texto19 = db.Column(db.String(100))
    Texto20 = db.Column(db.String(100))
    TextoLibre = db.Column(db.Text)
    
    # Altri campi
    PesoPieza = db.Column(db.Numeric(10, 3))
    UnidadesCaja = db.Column(db.Integer)
    NombrePlataforma = db.Column(db.String(100))
    HayTaraAplicada = db.Column(db.Integer)
    LineaCerrada = db.Column(db.Integer)
    EstadoLinea = db.Column(db.String(20))
    
    # Audit
    Modificado = db.Column(db.Integer)
    Operacion = db.Column(db.Integer)
    Usuario = db.Column(db.String(50))
    TimeStamp = db.Column(db.DateTime)
    
    # Relationships
    articolo = db.relationship('Product', backref='fatture_linee', lazy='select')
    
    def __repr__(self):
        return f'<FatturaLinea {self.IdLineaFactura}: {self.Descripcion[:30]}...>'
    
    @property
    def importo_totale_con_iva(self):
        """Calcola l'importo totale della linea con IVA"""
        return float(self.ImporteConDtoTotalConDtoPP or self.Importe or 0)
        
    @property 
    def quantita(self):
        """Ritorna la quantità (peso per articoli pesabili, quantità per articoli numerici)"""
        # Per articoli numerici (unità di misura != peso), usa Cantidad2
        # Per articoli pesabili (kg, g), usa Peso
        unita_peso = ['kg', 'g', 'KG', 'G', 'Kg']
        if self.Medida2 and self.Medida2 in unita_peso:
            # Articolo pesabile - usa Peso
            return float(self.Peso or 0)
        else:
            # Articolo numerabile - usa Cantidad2, fallback su Peso se non disponibile
            return float(self.Cantidad2 or self.Peso or 0)
    
    @property
    def prezzo_unitario(self):
        """Ritorna il prezzo unitario"""
        return float(self.Precio or 0)
    
    @property
    def aliquota_iva(self):
        """Ritorna l'aliquota IVA"""
        return float(self.PorcentajeIVA or 0)
    
    @property
    def importo_iva_linea(self):
        """Ritorna l'importo IVA della linea"""
        return float(self.ImporteDelIVAConDtoLConDtoTotalConDtoPP or 0)


class AlbaranMaxNumAlbaran(db.Model):
    """Modello per la tabella dat_albaran_max_num_albaran che tiene traccia del numero massimo di DDT"""
    __tablename__ = 'dat_albaran_max_num_albaran'
    
    NumAlbaran = db.Column(db.BigInteger)
    IdEmpresa = db.Column(db.Integer, primary_key=True, default=1)
    IdTienda = db.Column(db.Integer, primary_key=True, default=1)
    IdBalanzaMaestra = db.Column(db.Integer, primary_key=True, default=1)
    IdBalanzaEsclava = db.Column(db.Integer, primary_key=True, default=-1)
    Modificado = db.Column(db.Boolean, default=1)
    Operacion = db.Column(db.String(1), default="A")
    Usuario = db.Column(db.String(20), default="DBLogiX")
    TimeStamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AlbaranMaxNumAlbaran {self.NumAlbaran}>'
    
    @classmethod
    def update_max_num_albaran(cls, num_albaran):
        """Aggiorna il numero massimo di DDT nella tabella"""
        # Cerca il record esistente
        max_record = cls.query.filter_by(
            IdEmpresa=1,
            IdTienda=1,
            IdBalanzaMaestra=1,
            IdBalanzaEsclava=-1
        ).first()
        
        if max_record:
            # Aggiorna il record esistente
            max_record.NumAlbaran = num_albaran
            max_record.TimeStamp = datetime.utcnow()
            max_record.Modificado = 1
        else:
            # Crea un nuovo record
            max_record = cls(
                NumAlbaran=num_albaran,
                IdEmpresa=1,
                IdTienda=1,
                IdBalanzaMaestra=1,
                IdBalanzaEsclava=-1,
                Modificado=1,
                Operacion="A",
                Usuario="DBLogiX",
                TimeStamp=datetime.utcnow()
            )
            db.session.add(max_record)
        
        return max_record


# ===========================================
# NUOVO SISTEMA GESTIONE INGREDIENTI E FORNITORI
# Design semplificato con relazioni N-N
# ===========================================

class Ingrediente(db.Model):
    """Modello per la gestione degli ingredienti - versione semplificata"""
    __tablename__ = 'ingredienti'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    descrizione = db.Column(db.Text)
    unita_misura = db.Column(db.String(10), default='kg')
    categoria = db.Column(db.String(50))
    
    # Informazioni nutrizionali per 100g
    calorie = db.Column(db.Numeric(6, 1))
    proteine = db.Column(db.Numeric(5, 2))
    carboidrati = db.Column(db.Numeric(5, 2))
    grassi = db.Column(db.Numeric(5, 2))
    
    # Informazioni aggiuntive
    allergeni = db.Column(db.Text)
    conservazione = db.Column(db.Text)
    
    # Fornitore preferito per questo ingrediente
    fornitore_preferito_id = db.Column(db.Integer, db.ForeignKey('fornitori.id'), nullable=True)
    
    # Campi sistema
    attivo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    fornitori = db.relationship('IngredienteFornitore', backref='ingrediente', lazy='dynamic', cascade='all, delete-orphan')
    articoli = db.relationship('ArticoloIngrediente', backref='ingrediente', lazy='dynamic', cascade='all, delete-orphan')
    fornitore_preferito = db.relationship('Fornitore', foreign_keys=[fornitore_preferito_id], backref='ingredienti_preferiti')
    
    def __repr__(self):
        return f'<Ingrediente {self.id}: {self.nome}>'
    
    @property
    def numero_fornitori(self):
        """Restituisce il numero di fornitori attivi per questo ingrediente"""
        return self.fornitori.filter_by(attivo=True).count()
    
    @property
    def numero_articoli(self):
        """Restituisce il numero di articoli che utilizzano questo ingrediente"""
        return self.articoli.filter_by(attivo=True).count()
    
    @property
    def fornitori_attivi(self):
        """Restituisce la lista dei fornitori attivi per questo ingrediente"""
        return self.fornitori.filter_by(attivo=True).all()
    
    @property
    def prezzo_medio(self):
        """Calcola il prezzo medio tra tutti i fornitori attivi"""
        fornitori_attivi = self.fornitori.filter_by(attivo=True).all()
        if not fornitori_attivi:
            return 0.0
        
        total_price = sum(float(f.prezzo_unitario) for f in fornitori_attivi)
        return total_price / len(fornitori_attivi)
    
    @property
    def miglior_prezzo(self):
        """Restituisce il miglior prezzo (più basso) per questo ingrediente"""
        fornitori_attivi = self.fornitori.filter_by(attivo=True).all()
        if not fornitori_attivi:
            return 0.0
        
        prezzi = [float(f.prezzo_unitario) for f in fornitori_attivi]
        return min(prezzi)
    
    @property
    def miglior_fornitore(self):
        """Restituisce il fornitore con il prezzo migliore"""
        fornitori_attivi = self.fornitori.filter_by(attivo=True).all()
        if not fornitori_attivi:
            return None
        
        return min(fornitori_attivi, key=lambda f: float(f.prezzo_unitario))


class Fornitore(db.Model):
    """Modello per la gestione dei fornitori - versione semplificata"""
    __tablename__ = 'fornitori'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    indirizzo = db.Column(db.String(200))
    citta = db.Column(db.String(100))
    provincia = db.Column(db.String(50))
    cap = db.Column(db.String(10))
    paese = db.Column(db.String(50), default='Italia')
    partita_iva = db.Column(db.String(16))
    codice_fiscale = db.Column(db.String(16))
    iban = db.Column(db.String(34))
    note = db.Column(db.Text)
    
    # Campi sistema
    attivo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ingredienti = db.relationship('IngredienteFornitore', backref='fornitore', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Fornitore {self.id}: {self.nome}>'
    
    @property
    def numero_ingredienti(self):
        """Restituisce il numero di ingredienti forniti da questo fornitore"""
        return self.ingredienti.filter_by(attivo=True).count()
    
    @property
    def indirizzo_completo(self):
        """Restituisce l'indirizzo completo formattato"""
        parts = []
        if self.indirizzo:
            parts.append(self.indirizzo)
        if self.cap and self.citta:
            parts.append(f"{self.cap} {self.citta}")
        elif self.citta:
            parts.append(self.citta)
        if self.provincia:
            parts.append(f"({self.provincia})")
        return ', '.join(parts) if parts else 'N/A'
    
    @property
    def prezzo_medio_ingredienti(self):
        """Calcola il prezzo medio degli ingredienti forniti"""
        ingredienti_attivi = self.ingredienti.filter_by(attivo=True).all()
        if not ingredienti_attivi:
            return 0.0
        
        total_price = sum(float(i.prezzo_unitario) for i in ingredienti_attivi)
        return total_price / len(ingredienti_attivi)


class IngredienteFornitore(db.Model):
    """Tabella associazione N-N tra ingredienti e fornitori con prezzi"""
    __tablename__ = 'ingredienti_fornitori'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ingrediente_id = db.Column(db.Integer, db.ForeignKey('ingredienti.id'), nullable=False)
    fornitore_id = db.Column(db.Integer, db.ForeignKey('fornitori.id'), nullable=False)
    prezzo_unitario = db.Column(db.Numeric(10, 3), nullable=False)
    codice_fornitore = db.Column(db.String(50))
    tempo_consegna_giorni = db.Column(db.Integer, default=0)
    quantita_minima = db.Column(db.Numeric(10, 3), default=0.000)
    note = db.Column(db.Text)
    
    # Campi sistema
    attivo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint per evitare duplicati
    __table_args__ = (db.UniqueConstraint('ingrediente_id', 'fornitore_id', name='uk_ingrediente_fornitore'),)
    
    def __repr__(self):
        return f'<IngredienteFornitore I:{self.ingrediente_id} F:{self.fornitore_id} €{self.prezzo_unitario}>'
    
    @property
    def prezzo_formatted(self):
        """Restituisce il prezzo formattato con simbolo euro e unità di misura"""
        unit = self.ingrediente.unita_misura if self.ingrediente else 'N/A'
        return f"€ {float(self.prezzo_unitario):.2f}/{unit}".replace('.', ',')
    
    @property
    def tempo_consegna_text(self):
        """Restituisce il tempo di consegna in formato leggibile"""
        if self.tempo_consegna_giorni == 1:
            return "1 giorno"
        elif self.tempo_consegna_giorni == 0:
            return "Consegna immediata"
        else:
            return f"{self.tempo_consegna_giorni} giorni"
    
    @property
    def quantita_minima_formatted(self):
        """Restituisce la quantità minima formattata"""
        if self.quantita_minima and self.quantita_minima > 0:
            unit = self.ingrediente.unita_misura if self.ingrediente else 'N/A'
            
            # Per unità come "pz", "pezzo", "n°" usa 0 decimali se è un numero intero
            if unit.lower() in ['pz', 'pezzo', 'pezzi', 'n°', 'nr', 'num']:
                if float(self.quantita_minima) == int(float(self.quantita_minima)):
                    return f"{int(float(self.quantita_minima))} {unit}"
                else:
                    return f"{float(self.quantita_minima):.1f} {unit}"
            
            # Per peso e volumi usa 2 decimali
            return f"{float(self.quantita_minima):.2f} {unit}".replace('.', ',')
        return "Nessuna"


class ArticoloIngrediente(db.Model):
    """Tabella associazione N-N tra articoli e ingredienti"""
    __tablename__ = 'articoli_ingredienti'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    articolo_id = db.Column(db.Integer, nullable=False)  # Riferimento a dat_articulo.IdArticulo
    ingrediente_id = db.Column(db.Integer, db.ForeignKey('ingredienti.id'), nullable=False)
    fornitore_preferito_id = db.Column(db.Integer, db.ForeignKey('fornitori.id'), nullable=True)
    quantita = db.Column(db.Numeric(10, 3), nullable=False, default=0.000)
    note = db.Column(db.Text)
    
    # Campi sistema
    attivo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    fornitore_preferito = db.relationship('Fornitore', backref='articoli_preferiti')
    
    # Unique constraint per evitare duplicati
    __table_args__ = (db.UniqueConstraint('articolo_id', 'ingrediente_id', name='uk_articolo_ingrediente'),)
    
    def __repr__(self):
        return f'<ArticoloIngrediente A:{self.articolo_id} I:{self.ingrediente_id}>'
    
    @property
    def articolo(self):
        """Relazione con l'articolo (senza foreign key per evitare problemi)"""
        return Article.query.filter_by(IdArticulo=self.articolo_id).first()
    
    @property
    def costo_totale(self):
        """Calcola il costo totale per questo ingrediente nell'articolo"""
        # PRIORITÀ 1: Usa il fornitore preferito specifico per questo articolo-ingrediente
        if self.fornitore_preferito_id:
            associazione = IngredienteFornitore.query.filter_by(
                ingrediente_id=self.ingrediente_id,
                fornitore_id=self.fornitore_preferito_id,
                attivo=True
            ).first()
            if associazione:
                return float(self.quantita) * float(associazione.prezzo_unitario)
        
        # PRIORITÀ 2: Usa il fornitore attivo impostato nell'ingrediente (dalla pagina ingredienti)
        if self.ingrediente and self.ingrediente.fornitore_preferito_id:
            associazione_attiva = IngredienteFornitore.query.filter_by(
                ingrediente_id=self.ingrediente_id,
                fornitore_id=self.ingrediente.fornitore_preferito_id,
                attivo=True
            ).first()
            if associazione_attiva:
                return float(self.quantita) * float(associazione_attiva.prezzo_unitario)
        
        # PRIORITÀ 3: Se non c'è fornitore attivo, usa il miglior prezzo
        miglior_associazione = self.ingrediente.miglior_fornitore
        if miglior_associazione:
            return float(self.quantita) * float(miglior_associazione.prezzo_unitario)
        
        return 0.0
    
    @property
    def costo_formatted(self):
        """Restituisce il costo formattato"""
        return f"€ {self.costo_totale:.2f}".replace('.', ',')
    
    @property
    def quantita_formatted(self):
        """Restituisce la quantità formattata con unità di misura"""
        unit = self.ingrediente.unita_misura if self.ingrediente else 'N/A'
        
        # Per unità come "pz", "pezzo", "n°" usa 0 decimali se è un numero intero
        if unit.lower() in ['pz', 'pezzo', 'pezzi', 'n°', 'nr', 'num']:
            if float(self.quantita) == int(float(self.quantita)):
                return f"{int(float(self.quantita))} {unit}"
            else:
                return f"{float(self.quantita):.1f} {unit}"
        
        # Per peso e volumi usa 2 decimali
        return f"{float(self.quantita):.2f} {unit}".replace('.', ',')
    
    @property
    def fornitore_utilizzato(self):
        """Restituisce il fornitore attualmente utilizzato per il calcolo del prezzo"""
        # PRIORITÀ 1: Fornitore preferito specifico per questo articolo-ingrediente
        if self.fornitore_preferito_id:
            associazione = IngredienteFornitore.query.filter_by(
                ingrediente_id=self.ingrediente_id,
                fornitore_id=self.fornitore_preferito_id,
                attivo=True
            ).first()
            if associazione:
                return associazione.fornitore
        
        # PRIORITÀ 2: Fornitore attivo impostato nell'ingrediente (dalla pagina ingredienti)
        if self.ingrediente and self.ingrediente.fornitore_preferito_id:
            associazione_attiva = IngredienteFornitore.query.filter_by(
                ingrediente_id=self.ingrediente_id,
                fornitore_id=self.ingrediente.fornitore_preferito_id,
                attivo=True
            ).first()
            if associazione_attiva:
                return associazione_attiva.fornitore
        
        # PRIORITÀ 3: Miglior fornitore (prezzo più basso)
        miglior_associazione = self.ingrediente.miglior_fornitore
        if miglior_associazione:
            return miglior_associazione.fornitore
        
        return None
    
    @property
    def tipo_fornitore_utilizzato(self):
        """Restituisce il tipo di fornitore utilizzato per il prezzo"""
        # PRIORITÀ 1: Fornitore preferito specifico per questo articolo-ingrediente
        if self.fornitore_preferito_id:
            associazione = IngredienteFornitore.query.filter_by(
                ingrediente_id=self.ingrediente_id,
                fornitore_id=self.fornitore_preferito_id,
                attivo=True
            ).first()
            if associazione:
                return "Fornitore specifico"
        
        # PRIORITÀ 2: Fornitore attivo impostato nell'ingrediente
        if self.ingrediente and self.ingrediente.fornitore_preferito_id:
            associazione_attiva = IngredienteFornitore.query.filter_by(
                ingrediente_id=self.ingrediente_id,
                fornitore_id=self.ingrediente.fornitore_preferito_id,
                attivo=True
            ).first()
            if associazione_attiva:
                return "Fornitore attivo"
        
        # PRIORITÀ 3: Miglior prezzo
        return "Miglior prezzo"


# ===========================================
# VISTE PER REPORTING FOOD COST
# ===========================================

class ViewFoodCost(db.Model):
    """Vista per il calcolo del food cost per articolo"""
    __tablename__ = 'view_food_cost'
    
    articolo_id = db.Column(db.Integer, primary_key=True)
    nome_articolo = db.Column(db.String(100))
    prezzo_vendita = db.Column(db.Numeric(13, 3))
    costo_ingredienti = db.Column(db.Numeric(15, 3))
    percentuale_food_cost = db.Column(db.Numeric(10, 2))
    numero_ingredienti = db.Column(db.Integer)
    attivo = db.Column(db.Boolean)
    ultimo_aggiornamento = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<ViewFoodCost {self.articolo_id}: {self.percentuale_food_cost}%>'
    
    @property
    def food_cost_status(self):
        """Restituisce lo stato del food cost basato sulla percentuale"""
        if not self.percentuale_food_cost:
            return 'unknown'
        
        percentuale = float(self.percentuale_food_cost)
        if percentuale <= 25:
            return 'excellent'  # Eccellente (verde)
        elif percentuale <= 35:
            return 'good'       # Buono (verde chiaro)
        elif percentuale <= 45:
            return 'acceptable' # Accettabile (giallo)
        else:
            return 'high'       # Alto (rosso)
    
    @property
    def food_cost_class(self):
        """Restituisce la classe CSS per il badge del food cost"""
        status_classes = {
            'excellent': 'success',
            'good': 'info', 
            'acceptable': 'warning',
            'high': 'danger',
            'unknown': 'secondary'
        }
        return status_classes.get(self.food_cost_status, 'secondary')


class ViewFornitoriIngredienti(db.Model):
    """Vista per il riepilogo fornitori e ingredienti"""
    __tablename__ = 'view_fornitori_ingredienti'
    
    fornitore_id = db.Column(db.Integer, primary_key=True)
    nome_fornitore = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    ingrediente_id = db.Column(db.Integer, primary_key=True)
    nome_ingrediente = db.Column(db.String(100))
    unita_misura = db.Column(db.String(10))
    prezzo_unitario = db.Column(db.Numeric(10, 3))
    quantita_minima = db.Column(db.Numeric(10, 3))
    tempo_consegna_giorni = db.Column(db.Integer)
    attivo = db.Column(db.Boolean)
    
    def __repr__(self):
        return f'<ViewFornitoriIngredienti F:{self.fornitore_id} I:{self.ingrediente_id}>'