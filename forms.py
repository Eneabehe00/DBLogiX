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
    screen_task = BooleanField('Screen Task - Utente Schermo Task')
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
    
    articles_per_package = IntegerField(
        'Articoli per Collo',
        validators=[DataRequired(), NumberRange(min=1, max=100)],
        description='Numero di articoli necessari per determinare un collo nei DDT (escluso l\'articolo "trasporto")',
        default=5
    )
    
    # 1. Configurazioni Email SMTP
    smtp_server = StringField(
        'Server SMTP',
        validators=[Optional(), Length(max=100)],
        description='Indirizzo del server SMTP per invio email (es. smtp.gmail.com)'
    )
    
    smtp_port = IntegerField(
        'Porta SMTP',
        validators=[Optional(), NumberRange(min=1, max=65535)],
        description='Porta del server SMTP (587 per TLS, 465 per SSL, 25 per non cifrato)',
        default=587
    )
    
    smtp_username = StringField(
        'Username Email',
        validators=[Optional(), Length(max=100)],
        description='Username per autenticazione SMTP'
    )
    
    smtp_password = PasswordField(
        'Password Email',
        validators=[Optional(), Length(max=100)],
        description='Password per autenticazione SMTP'
    )
    
    smtp_use_tls = BooleanField(
        'Usa TLS',
        description='Abilita crittografia TLS per connessioni sicure',
        default=True
    )
    
    admin_email = StringField(
        'Email Amministratore',
        validators=[Optional(), Email(), Length(max=120)],
        description='Indirizzo email per ricevere notifiche di sistema'
    )
    
    enable_email_notifications = BooleanField(
        'Abilita Notifiche Email',
        description='Invia email automatiche per DDT, scadenze e alert',
        default=False
    )
    
    # 2. Backup Automatico
    backup_frequency_hours = IntegerField(
        'Frequenza Backup (ore)',
        validators=[Optional(), NumberRange(min=1, max=168)],
        description='Ogni quante ore eseguire backup automatico (max 168 = 1 settimana)',
        default=24
    )
    
    backup_retention_days = IntegerField(
        'Giorni Conservazione Backup',
        validators=[Optional(), NumberRange(min=1, max=90)],
        description='Per quanti giorni mantenere i file di backup',
        default=7
    )
    
    backup_path = StringField(
        'Percorso Backup',
        validators=[Optional(), Length(max=255)],
        description='Cartella dove salvare i backup (relativa alla root dell\'app)',
        default='backups'
    )
    
    # 3. Timeout Database  
    db_connect_timeout = IntegerField(
        'Timeout Connessione DB (secondi)',
        validators=[Optional(), NumberRange(min=5, max=60)],
        description='Timeout per stabilire connessione al database',
        default=10
    )
    
    db_read_timeout = IntegerField(
        'Timeout Lettura DB (secondi)',
        validators=[Optional(), NumberRange(min=10, max=300)],
        description='Timeout per operazioni di lettura dal database',
        default=30
    )
    
    db_write_timeout = IntegerField(
        'Timeout Scrittura DB (secondi)',
        validators=[Optional(), NumberRange(min=10, max=300)],
        description='Timeout per operazioni di scrittura nel database',
        default=30
    )
    
    # 4. Localizzazione
    timezone = SelectField(
        'Fuso Orario',
        choices=[
            ('Europe/Rome', 'Europa/Roma (GMT+1)'),
            ('Europe/London', 'Europa/Londra (GMT+0)'),
            ('America/New_York', 'America/New York (GMT-5)'),
            ('America/Los_Angeles', 'America/Los Angeles (GMT-8)'),
            ('Asia/Tokyo', 'Asia/Tokyo (GMT+9)'),
            ('UTC', 'UTC (GMT+0)')
        ],
        default='Europe/Rome',
        description='Fuso orario per timestamp e calcoli date'
    )
    
    date_format = SelectField(
        'Formato Data',
        choices=[
            ('%d/%m/%Y', 'DD/MM/YYYY (Europeo)'),
            ('%m/%d/%Y', 'MM/DD/YYYY (Americano)'),
            ('%Y-%m-%d', 'YYYY-MM-DD (ISO)'),
            ('%d-%m-%Y', 'DD-MM-YYYY')
        ],
        default='%d/%m/%Y',
        description='Formato di visualizzazione delle date nell\'interfaccia'
    )
    
    # 5. Logo Aziendale
    company_logo = FileField(
        'Logo Aziendale',
        validators=[Optional()],
        description='Upload logo aziendale per DDT (PNG, JPG, max 2MB) - verrà rinominato automaticamente in LogoDDT.png'
    )
    
    # 6. Alert e Monitoraggio
    enable_stock_alerts = BooleanField(
        'Alert Stock Minimo',
        description='Invia notifiche quando le scorte scendono sotto la soglia minima',
        default=True
    )
    
    stock_alert_threshold = IntegerField(
        'Soglia Alert Stock',
        validators=[Optional(), NumberRange(min=0, max=1000)],
        description='Quantità minima sotto la quale inviare alert',
        default=10
    )
    
    expiry_check_frequency_hours = IntegerField(
        'Frequenza Controllo Scadenze (ore)',
        validators=[Optional(), NumberRange(min=1, max=24)],
        description='Ogni quante ore controllare prodotti in scadenza',
        default=6
    )
    
    # 7. Logging
    log_level = SelectField(
        'Livello Logging',
        choices=[
            ('DEBUG', 'DEBUG - Molto dettagliato'),
            ('INFO', 'INFO - Informazioni generali'),
            ('WARNING', 'WARNING - Solo avvisi'),
            ('ERROR', 'ERROR - Solo errori')
        ],
        default='INFO',
        description='Livello di dettaglio per i log di sistema'
    )
    
    log_max_size_mb = IntegerField(
        'Dimensione Max Log (MB)',
        validators=[Optional(), NumberRange(min=1, max=100)],
        description='Dimensione massima file log prima della rotazione',
        default=10
    )
    
    # 8. Sessioni Utente
    session_timeout_hours = IntegerField(
        'Durata Sessione (ore)',
        validators=[Optional(), NumberRange(min=1, max=24)],
        description='Durata massima sessione utente prima del logout automatico',
        default=2
    )
    
    session_inactivity_minutes = IntegerField(
        'Timeout Inattività (minuti)',
        validators=[Optional(), NumberRange(min=5, max=180)],
        description='Minuti di inattività prima del logout automatico',
        default=30
    )
    
    # 9. Gestione Chat
    enable_chat_auto_cleanup = BooleanField(
        'Svuotamento Automatico Chat',
        description='Abilita svuotamento automatico periodico della chat',
        default=False
    )
    
    chat_cleanup_frequency_days = IntegerField(
        'Frequenza Svuotamento Chat (giorni)',
        validators=[Optional(), NumberRange(min=1, max=365)],
        description='Ogni quanti giorni svuotare automaticamente la chat',
        default=7
    )
    
    enable_chat_auto_backup = BooleanField(
        'Backup Automatico Chat',
        description='Crea backup automatico prima dello svuotamento',
        default=True
    )
    
    chat_backup_retention_days = IntegerField(
        'Conservazione Backup Chat (giorni)',
        validators=[Optional(), NumberRange(min=1, max=365)],
        description='Per quanti giorni conservare i backup della chat',
        default=30
    )
    
    chat_backup_path = StringField(
        'Percorso Backup Chat',
        validators=[Optional(), Length(max=255)],
        description='Cartella dove salvare i backup della chat (relativa alla root dell\'app)',
        default='Backup/Chat'
    )
    
    # 10. Gestione Backup Clienti
    enable_clienti_auto_backup = BooleanField(
        'Backup Automatico Clienti',
        description='Crea backup automatico periodico dei dati clienti',
        default=True
    )
    
    clienti_backup_frequency_days = IntegerField(
        'Frequenza Backup Clienti (giorni)',
        validators=[Optional(), NumberRange(min=1, max=365)],
        description='Ogni quanti giorni eseguire backup automatico dei clienti',
        default=7
    )
    
    clienti_backup_retention_days = IntegerField(
        'Conservazione Backup Clienti (giorni)',
        validators=[Optional(), NumberRange(min=1, max=365)],
        description='Per quanti giorni conservare i backup dei clienti',
        default=30
    )
    
    clienti_backup_path = StringField(
        'Percorso Backup Clienti',
        validators=[Optional(), Length(max=255)],
        description='Cartella dove salvare i backup dei clienti (relativa alla root dell\'app)',
        default='Backup/Clienti'
    )
    
    # 11. Gestione Backup DDT
    enable_ddt_auto_backup = BooleanField(
        'Backup Automatico DDT',
        description='Crea backup automatico periodico dei DDT',
        default=True
    )
    
    ddt_backup_frequency_days = IntegerField(
        'Frequenza Backup DDT (giorni)',
        validators=[Optional(), NumberRange(min=1, max=365)],
        description='Ogni quanti giorni eseguire backup automatico dei DDT',
        default=7
    )
    
    ddt_backup_retention_days = IntegerField(
        'Conservazione Backup DDT (giorni)',
        validators=[Optional(), NumberRange(min=1, max=365)],
        description='Per quanti giorni conservare i backup dei DDT',
        default=30
    )
    
    ddt_backup_path = StringField(
        'Percorso Backup DDT',
        validators=[Optional(), Length(max=255)],
        description='Cartella dove salvare i backup dei DDT (relativa alla root dell\'app)',
        default='Backup/DDT'
    )
    
    # 12. Gestione Backup Fatture
    enable_fatture_auto_backup = BooleanField(
        'Backup Automatico Fatture',
        description='Crea backup automatico periodico delle fatture',
        default=True
    )
    
    fatture_backup_frequency_days = IntegerField(
        'Frequenza Backup Fatture (giorni)',
        validators=[Optional(), NumberRange(min=1, max=365)],
        description='Ogni quanti giorni eseguire backup automatico delle fatture',
        default=7
    )
    
    fatture_backup_retention_days = IntegerField(
        'Conservazione Backup Fatture (giorni)',
        validators=[Optional(), NumberRange(min=1, max=365)],
        description='Per quanti giorni conservare i backup delle fatture',
        default=30
    )
    
    fatture_backup_path = StringField(
        'Percorso Backup Fatture',
        validators=[Optional(), Length(max=255)],
        description='Cartella dove salvare i backup delle fatture (relativa alla root dell\'app)',
        default='Backup/Fatture'
    )
    
    submit = SubmitField('Salva Configurazioni') 