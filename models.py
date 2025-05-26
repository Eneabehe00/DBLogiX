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
    Comportamiento = db.Column(db.SmallInteger, default=1)
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