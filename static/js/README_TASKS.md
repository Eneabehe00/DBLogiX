# Tasks JavaScript Documentation

## Struttura

Il JavaScript per la gestione dei task è stato centralizzato nel file `tasks.js` per migliorare l'organizzazione e la manutenibilità del codice.

## File Principale

### `tasks.js`
Contiene tutta la logica JavaScript per:
- Gestione notifiche
- Scansione QR code e fotocamera
- Interfaccia task detail
- Creazione task
- Funzionalità comuni

## Funzioni Principali

### Inizializzazione
- `initializeTasksPage()` - Inizializza la pagina in base al percorso corrente
- `initializeCommonTasks()` - Funzionalità comuni a tutte le pagine task
- `initializeNotifications()` - Specifico per pagina notifiche
- `initializeScanPage()` - Specifico per pagina scansione
- `initializeTaskDetail()` - Specifico per dettaglio task
- `initializeCreateTask()` - Specifico per creazione task

### Notifiche
- `handleNotificationClick(notificationId, taskId)` - Gestisce click su notifica
- `markAsRead(notificationId)` - Segna singola notifica come letta
- `markAllAsRead()` - Segna tutte le notifiche come lette

### Scansione
- `startCamera()` - Avvia la fotocamera per scansione QR
- `stopCamera()` - Ferma la fotocamera
- `processScan(code)` - Elabora il codice scansionato
- `showFeedback(message, type)` - Mostra feedback all'utente

### Utility
- `getTaskTicketId()` - Ottiene ID ticket da URL o attributi
- `getTaskIdFromUrl()` - Ottiene ID task da URL
- `getCSRFToken()` - Ottiene token CSRF
- `formatDate(dateString)` - Formatta date per visualizzazione
- `showLoading(element)` / `hideLoading(element, text)` - Gestione stati di caricamento

## Utilizzo nei Template

Tutti i template task includono il file JavaScript:

```html
{% block extra_js %}
<script src="{{ url_for('static', filename='js/tasks.js') }}"></script>
{% endblock %}
```

### Chiamate alle Funzioni

Le funzioni sono accessibili tramite il namespace `TasksJS`:

```html
<!-- Esempio: Segna tutto come letto -->
<button onclick="TasksJS.markAllAsRead()">Segna tutto come letto</button>

<!-- Esempio: Gestione notifica -->
<div onclick="TasksJS.handleNotificationClick({{ notification.id }}, {{ task_id }})">
```

## Dipendenze

- **jQuery** - Per manipolazione DOM e AJAX
- **ZXing Library** - Per scansione QR code (solo pagina scan)
- **Bootstrap** - Per componenti UI

## Template Aggiornati

I seguenti template sono stati aggiornati per utilizzare il nuovo sistema:

1. `notifications.html` - Gestione notifiche
2. `view_task.html` - Dettaglio task
3. `scan_ticket.html` - Scansione prodotti
4. `user_dashboard.html` - Dashboard utente
5. `admin_dashboard.html` - Dashboard admin
6. `create_task.html` - Creazione task

## Vantaggi

1. **Centralizzazione** - Tutto il codice JavaScript in un unico file
2. **Manutenibilità** - Più facile da aggiornare e debuggare
3. **Riusabilità** - Funzioni condivise tra diverse pagine
4. **Organizzazione** - Codice strutturato e documentato
5. **Performance** - Un solo file da caricare invece di script inline multipli

## Note Tecniche

- Il file utilizza il pattern namespace per evitare conflitti globali
- Tutte le funzioni sono esportate tramite `window.TasksJS`
- Il CSRF token viene recuperato automaticamente dal meta tag
- La gestione degli errori è centralizzata e consistente 