# Gestione Fatture - Sistema File-Based

Questa directory contiene i file delle fatture caricate e processate dal sistema.

## Struttura Directory

```
data/fatture/
├── metadata.json           # Indice locale delle fatture
├── price_history.json      # Storico modifiche prezzi
├── 20241201_120000_fattura1.pdf  # File PDF fatture
├── 20241201_120000_fattura1.raw.json   # Dati grezzi GEMINI
├── 20241201_120000_fattura1.norm.json  # Dati normalizzati
├── 20241201_120000_fattura1.log.json   # Log operazioni
└── ...
```

## Configurazione

### Chiave API GEMINI

Per utilizzare il sistema di estrazione automatica, è necessario configurare la chiave API di Google GEMINI.

1. Ottieni una chiave API da [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Aggiungi la chiave nel file `DBLogix.exe.config`:

```xml
<appSettings>
    <!-- Altre configurazioni... -->
    <add key="GEMINI_API_KEY" value="LA_TUA_CHIAVE_API_QUI" />
</appSettings>
```

3. Riavvia l'applicazione

### Funzionalità

- **Upload PDF**: Carica e processa automaticamente fatture in formato PDF
- **Estrazione Dati**: Utilizza AI per estrarre fornitore, intestazione e righe
- **Gestione Fornitori**: Crea/aggiorna automaticamente fornitori nel database
- **Gestione Ingredienti**: Crea/aggiorna automaticamente ingredienti e prezzi
- **Rilevamento Duplicati**: Previene il caricamento di fatture duplicate
- **Storico Prezzi**: Traccia le modifiche ai prezzi degli ingredienti
- **Modifica Manuale**: Permette correzioni manuali dei dati estratti

### Sicurezza

- I file PDF sono accessibili solo agli utenti autenticati
- Le operazioni di eliminazione sono riservate agli amministratori
- Tutti i log delle operazioni sono tracciati con timestamp e utente

### Backup

È consigliabile fare backup regolari di questa directory, specialmente:
- `metadata.json`: Indice principale
- `price_history.json`: Storico prezzi
- File PDF originali

### Manutenzione

- I file vengono nominati automaticamente con timestamp per evitare conflitti
- L'indice `metadata.json` viene aggiornato automaticamente
- I log delle operazioni sono mantenuti per audit trail
