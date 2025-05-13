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
    descripcion = StringField('Descripcion', validators=[DataRequired(), Length(max=100)])
    descripcion1 = StringField('Descripcion1', validators=[Optional(), Length(max=100)])
    id_tipo = IntegerField('Tipo', validators=[DataRequired()], default=1)
    id_familia = IntegerField('Familia', validators=[Optional()])
    id_subfamilia = IntegerField('SubFamilia', validators=[Optional()])
    id_departamento = IntegerField('Departamento', validators=[Optional()])
    id_seccion = IntegerField('Seccion', validators=[Optional()])
    favorito = BooleanField('Favorito', default=True)
    precio_sin_iva = DecimalField('Precio Sin IVA', validators=[Optional()], places=6)
    id_iva = IntegerField('IVA', validators=[Optional()])
    precio_con_iva = DecimalField('Precio Con IVA', validators=[Optional()], places=3)
    ean_scanner = StringField('EAN', validators=[Optional(), Length(max=50)])
    texto1 = TextAreaField('Ingredientes/Descrizione', validators=[Optional()])
    texto_libre = TextAreaField('Valori Nutrizionali', validators=[Optional()])
    stock_actual = DecimalField('Stock Actual', validators=[Optional()], places=3)
    peso_minimo = DecimalField('Peso Minimo', validators=[Optional()], places=3)
    peso_maximo = DecimalField('Peso Maximo', validators=[Optional()], places=3)
    peso_objetivo = DecimalField('Peso Objetivo', validators=[Optional()], places=3)
    fecha_caducidad_activada = BooleanField('Fecha Caducidad Activada', default=True)
    dias_caducidad = IntegerField('Días Caducidad', validators=[Optional()])
    en_venta = BooleanField('En Venta', default=True)
    incluir_gestion_stock = BooleanField('Incluir Gestion Stock', default=True)
    submit = SubmitField('Save')

class ArticleDeleteForm(FlaskForm):
    confirm = BooleanField('Confirm Deletion', validators=[DataRequired()])
    submit = SubmitField('Delete') 