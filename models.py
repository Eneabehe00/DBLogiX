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
    TeclaDirecta = db.Column(db.Integer)
    TaraFija = db.Column(db.Integer)
    
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
    IdTicket = db.Column(db.BigInteger)
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
    PrecioSinIVA = db.Column(db.Numeric(12, 6))
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
        if self.total_tickets == 0:
            return 0
        return int((self.completed_tickets / self.total_tickets) * 100)
    
    @property
    def is_completed(self):
        return self.status == 'completed' and self.completed_tickets == self.total_tickets
    
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
        """Update the progress counters"""
        completed_count = self.task_tickets.filter_by(status='completed').count()
        total_count = self.task_tickets.count()
        
        self.completed_tickets = completed_count
        self.total_tickets = total_count
        
        # Auto-update status based on progress
        if total_count == 0:
            self.status = 'pending'
        elif completed_count == total_count and total_count > 0:
            self.status = 'completed'
            if not self.completed_at:
                self.completed_at = datetime.utcnow()
        elif completed_count > 0:
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
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<TaskNotification {self.id}: {self.notification_type}>' 