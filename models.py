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

class Product(db.Model):
    __tablename__ = 'dat_articulo'
    
    IdArticulo = db.Column(db.Integer, primary_key=True)
    Descripcion = db.Column(db.String(100))
    PrecioConIVA = db.Column(db.Numeric(13, 3))
    EANScanner = db.Column(db.String(50))
    IdFamilia = db.Column(db.Integer)
    IdSubFamilia = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<Product {self.IdArticulo}: {self.Descripcion}>'

    @property
    def Precio(self):
        return self.PrecioConIVA
    
    @property
    def CodEAN(self):
        return self.EANScanner


class TicketHeader(db.Model):
    __tablename__ = 'dat_ticket_cabecera'
    
    IdTicket = db.Column(db.Integer, primary_key=True)
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