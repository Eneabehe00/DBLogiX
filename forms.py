from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, IntegerField, DecimalField, FileField, DateField
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

class CompanyConfigForm(FlaskForm):
    nombre_empresa = StringField('Nome Azienda', validators=[DataRequired(), Length(max=100)])
    cif_vat = StringField('Partita IVA/Codice Fiscale', validators=[DataRequired(), Length(max=50)])
    telefono = StringField('Telefono', validators=[DataRequired(), Length(max=20)])
    direccion = StringField('Indirizzo', validators=[DataRequired(), Length(max=200)])
    cod_postal = StringField('CAP', validators=[DataRequired(), Length(max=10)])
    poblacion = StringField('Città', validators=[DataRequired(), Length(max=100)])
    provincia = StringField('Provincia', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Salva Configurazione Azienda')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[Optional()])
    start_date = DateField('Start Date', validators=[Optional()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Search')

class FilterForm(FlaskForm):
    familia = SelectField('Family', choices=[], coerce=int)
    subfamilia = SelectField('Subfamily', choices=[], coerce=int)
    submit = SubmitField('Filter')

class ManualScanForm(FlaskForm):
    ticket_id = StringField('Ticket ID', validators=[DataRequired()])
    submit = SubmitField('Process')

class DDTClientSelectForm(FlaskForm):
    cliente_id = IntegerField('Cliente ID', validators=[DataRequired()])
    cliente_nome = StringField('Cliente', validators=[DataRequired()])
    submit = SubmitField('Seleziona Cliente')

class DDTTicketFilterForm(FlaskForm):
    from_date = StringField('Data Inizio', validators=[DataRequired()])
    to_date = StringField('Data Fine', validators=[DataRequired()])
    submit = SubmitField('Filtra')

class DDTCreateForm(FlaskForm):
    cliente_id = IntegerField('Cliente ID', validators=[DataRequired()])
    cliente_nome = StringField('Cliente', validators=[])
    tickets = TextAreaField('Tickets IDs (JSON)', validators=[DataRequired()])
    id_empresa = IntegerField('ID Azienda', validators=[DataRequired()])
    submit = SubmitField('Crea DDT')

class DDTDeleteForm(FlaskForm):
    confirm = BooleanField('Conferma Eliminazione', validators=[DataRequired()])
    submit = SubmitField('Elimina DDT')

class DDTExportForm(FlaskForm):
    format = SelectField('Formato', choices=[('pdf', 'PDF')], default='pdf')
    submit = SubmitField('Esporta')

class ArticleSearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search')

class ArticleForm(FlaskForm):
    id_articulo = IntegerField('ID Articolo', validators=[Optional()])
    descripcion = StringField('Descripcion', validators=[DataRequired(), Length(max=100)])
    descripcion1 = StringField('Descripcion1', validators=[Optional(), Length(max=100)])
    id_tipo = SelectField('Tipo', validators=[DataRequired()], 
                         choices=[(1, 'Pesato'), (2, 'Unitario'), (3, 'Peso Fisso'), (4, 'Reso')],
                         coerce=int, default=1)
    id_familia = SelectField('Famiglia', validators=[Optional()], coerce=int)
    id_subfamilia = IntegerField('SubFamilia', validators=[Optional()])
    id_departamento = SelectField('Reparto', validators=[Optional()], coerce=int)
    id_seccion = SelectField('Sezione', validators=[Optional()], coerce=int)
    tasto_directo = IntegerField('Tasto Diretto', validators=[Optional()])
    tara_fija = DecimalField('Tara Fissa', validators=[Optional()], places=3)
    favorito = BooleanField('Favorito', default=True)
    precio_sin_iva = DecimalField('Precio Sin IVA', validators=[Optional()], places=6)
    id_iva = SelectField('IVA', validators=[Optional()], coerce=int)
    precio_con_iva = DecimalField('Precio Con IVA', validators=[Optional()], places=3)
    ean_scanner = StringField('EAN', validators=[Optional(), Length(max=50)])
    logo_pantalla = StringField('Logo Pantalla', validators=[Optional(), Length(max=1000)])
    texto1 = TextAreaField('Texto 1', validators=[Optional()])
    texto2 = TextAreaField('Texto 2', validators=[Optional()])
    texto3 = TextAreaField('Texto 3', validators=[Optional()])
    texto4 = TextAreaField('Texto 4', validators=[Optional()])
    texto5 = TextAreaField('Texto 5', validators=[Optional()])
    texto6 = TextAreaField('Texto 6', validators=[Optional()])
    texto7 = TextAreaField('Texto 7', validators=[Optional()])
    texto8 = TextAreaField('Texto 8', validators=[Optional()])
    texto9 = TextAreaField('Texto 9', validators=[Optional()])
    texto10 = TextAreaField('Texto 10', validators=[Optional()])
    texto11 = TextAreaField('Texto 11', validators=[Optional()])
    texto12 = TextAreaField('Texto 12', validators=[Optional()])
    texto13 = TextAreaField('Texto 13', validators=[Optional()])
    texto14 = TextAreaField('Texto 14', validators=[Optional()])
    texto15 = TextAreaField('Texto 15', validators=[Optional()])
    texto16 = TextAreaField('Texto 16', validators=[Optional()])
    texto17 = TextAreaField('Texto 17', validators=[Optional()])
    texto18 = TextAreaField('Texto 18', validators=[Optional()])
    texto19 = TextAreaField('Texto 19', validators=[Optional()])
    texto20 = TextAreaField('Texto 20', validators=[Optional()])
    texto_libre = TextAreaField('Valori Nutrizionali', validators=[Optional()])
    stock_actual = DecimalField('Stock Actual', validators=[Optional()], places=3)
    peso_minimo = DecimalField('Peso Minimo', validators=[Optional()], places=3)
    peso_maximo = DecimalField('Peso Maximo', validators=[Optional()], places=3)
    peso_objetivo = DecimalField('Peso Objetivo', validators=[Optional()], places=3)
    fecha_caducidad_activada = BooleanField('Fecha Caducidad Activada', default=True)
    dias_caducidad = IntegerField('Días Caducidad', validators=[Optional()])
    en_venta = BooleanField('En Venta', default=True)
    incluir_gestion_stock = BooleanField('Incluir Gestion Stock', default=True)
    id_clase = SelectField('Classe di Tracciabilità', validators=[Optional()], coerce=int)
    submit = SubmitField('Save')

class ArticleDeleteForm(FlaskForm):
    confirm = BooleanField('Confirm Deletion', validators=[DataRequired()])
    submit = SubmitField('Delete')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Reimposta Password')

class SystemConfigForm(FlaskForm):
    expiry_warning_days = IntegerField(
        'Giorni Preavviso Scadenza', 
        validators=[DataRequired(), NumberRange(min=0, max=30)],
        description='Numero di giorni prima della scadenza per contrassegnare i ticket come "In Scadenza"'
    )
    submit = SubmitField('Salva Configurazioni') 