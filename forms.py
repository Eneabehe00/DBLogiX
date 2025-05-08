from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, IntegerField, DecimalField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional, NumberRange
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    is_admin = BooleanField('Administrator')
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class DbConfigForm(FlaskForm):
    host = StringField('Host IP', validators=[DataRequired()])
    user = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    database = StringField('Database Name', validators=[DataRequired()])
    port = StringField('Port', validators=[DataRequired()])
    submit = SubmitField('Save Configuration')
    test_connection = SubmitField('Test Connection')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search')

class FilterForm(FlaskForm):
    familia = SelectField('Family', choices=[], coerce=int)
    subfamilia = SelectField('Subfamily', choices=[], coerce=int)
    submit = SubmitField('Filter')

class ManualScanForm(FlaskForm):
    ticket_id = StringField('Ticket ID', validators=[DataRequired()])
    submit = SubmitField('Process')

class ClientSearchForm(FlaskForm):
    query = StringField('Cerca Cliente', validators=[DataRequired()])
    submit = SubmitField('Cerca')

class ClientForm(FlaskForm):
    # Dati anagrafici
    nombre = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    dni = StringField('DNI', validators=[Length(max=20)])
    direccion = StringField('Indirizzo', validators=[Length(max=200)])
    cod_postal = StringField('Codice Postale', validators=[Length(max=10)])
    poblacion = StringField('Città', validators=[Length(max=100)])
    provincia = StringField('Provincia', validators=[Length(max=100)])
    pais = StringField('Paese', validators=[Length(max=100)])
    
    # Contatti
    telefono1 = StringField('Telefono 1', validators=[Length(max=20)])
    telefono2 = StringField('Telefono 2', validators=[Length(max=20)])
    telefono3 = StringField('Telefono 3', validators=[Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=100)])
    
    # Preferenze email
    tipo_email_ticket = SelectField('Email Ticket', choices=[(0, 'No'), (1, 'Si')], coerce=int)
    tipo_email_albaran = SelectField('Email Albaran', choices=[(0, 'No'), (1, 'Si')], coerce=int)
    tipo_email_factura = SelectField('Email Fattura', choices=[(0, 'No'), (1, 'Si')], coerce=int)
    
    # Pagamenti e sconti
    id_tarifa = IntegerField('Tariffa', validators=[Optional()])
    ofertas = SelectField('Offerte', choices=[(0, 'No'), (1, 'Si')], coerce=int)
    id_forma_pago = IntegerField('Forma di Pagamento', validators=[Optional()])
    descuento = DecimalField('Sconto (%)', validators=[Optional(), NumberRange(min=0, max=100)], places=2)
    dto_pronto_pago = DecimalField('Sconto Pronto Pagamento (%)', validators=[Optional(), NumberRange(min=0, max=100)], places=2)
    
    # Dati bancari
    nombre_banco = StringField('Nome Banca', validators=[Length(max=100)])
    codigo_cuenta = StringField('Codice Conto', validators=[Length(max=50)])
    numero_vencimientos = IntegerField('Numero Scadenze', validators=[Optional()])
    dias_entre_vencimientos = IntegerField('Giorni tra Scadenze', validators=[Optional()])
    
    # Altri dati
    id_estado = IntegerField('Stato', validators=[Optional()])
    observaciones = TextAreaField('Osservazioni')
    cod_interno = StringField('Codice Interno', validators=[Length(max=50)])
    ean_scanner = StringField('Codice EAN', validators=[Length(max=50)])
    
    # Opzioni
    puntos_fidelidad = IntegerField('Punti Fedeltà', validators=[Optional()])
    usar_recargo_equivalencia = SelectField('Usa Ricaricare Equivalenza', choices=[(0, 'No'), (1, 'Si')], coerce=int)
    total_por_articulo = SelectField('Totale per Articolo', choices=[(0, 'No'), (1, 'Si')], coerce=int)
    aplicar_tarifa_etiqueta = SelectField('Applica Tariffa Etichetta', choices=[(0, 'No'), (1, 'Si')], coerce=int)
    
    # Formati
    formato_albaran = StringField('Formato Albaran', validators=[Length(max=100)])
    formato_factura = StringField('Formato Fattura', validators=[Length(max=100)])
    modo_facturacion = IntegerField('Modalità Fatturazione', validators=[Optional()])
    
    foto = FileField('Foto')
    
    submit = SubmitField('Salva') 