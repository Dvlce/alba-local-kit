# Alba Local Kit

Motore integrabile per conversazioni locali con memoria continua, profili, fatti/inferenze/incertezze separati, isolamento privato/gruppi, feedback esplicito, Telegram, chiavi web monouso, esportazioni personali e backup cifrati. SQLite FTS5 e contesto limitato; Ollama o llama.cpp sostituibili. Default 20 utenti autorizzati e 5 persone attive. Pensato anche per Raspberry Pi 5 8 GB.

Il progetto completo con sito, editor Tramonto, SPICE e APK è [alba-tramonto](https://github.com/Dvlce/alba-tramonto). Questo kit non include l’interfaccia web: si collega alla tua applicazione.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install .
ollama pull qwen3:4b-instruct-2507-q4_K_M
```

Installa Ollama dal [sito ufficiale](https://ollama.com/download). Il modello richiede il download iniziale, poi gira localmente. Con meno di 6 GB di RAM scegli un modello più piccolo, per esempio `qwen3:1.7b`; verifica latenza e qualità sul tuo hardware.

```python
import asyncio
from alba_local import AlbaLocal

async def main():
    async with AlbaLocal('./archivio-alba', admins=[1], allowed=[2]) as alba:
        print(await alba.reply(2, 'Vorrei organizzare meglio lo studio', 'Anna'))

asyncio.run(main())
```

**L’applicazione ospite deve autenticare gli utenti.** Non usare un `user_id` scelto liberamente da una richiesta anonima. `reply` e `web_key` richiedono un’identità già verificata dal tuo sistema. `authorize(id, actor)` richiede un amministratore. Il kit non unisce automaticamente account per nome o email.

Per integrare Telegram, passa `bot_token` e un `public_url` HTTPS del tuo sito, abilita l’accesso automatico quando desiderato e chiama `run_telegram()`:

```python
import asyncio
import os
from alba_local import AlbaLocal

async def main():
    async with AlbaLocal('./archivio-alba', admins=[123456789],
            bot_token=os.environ['TELEGRAM_BOT_TOKEN'],
            public_url='https://alba.example.org') as alba:
        alba.store.set_setting('automatic_web_access', '1')
        await alba.run_telegram()

asyncio.run(main())
```

Il bot supporta `/web_key`, `/web_password`, `/profile`, `/memory`, `/timeline`, `/export_key`, `/export`, `/forget`, `/feedback`, `/memory_key` e i comandi amministrativi. Gruppi: mention/reply/comandi, modalità auto configurabile e autorizzazione dell’amministratore Telegram del gruppo. La memoria privata non entra nei gruppi.

Quando una chiave `/web_key` arriva al sito come frammento `/#web_key=…`, rimuovila subito dalla barra con `history.replaceState`; inviala solo via HTTPS al tuo endpoint di login. `verify_web_key(token)` la consuma una volta e restituisce sessione, CSRF e identità risolta sul server. Conserva la sessione in cookie Secure/HttpOnly/SameSite, verifica CSRF sulle mutazioni e usa `identify_session(cookie)` per ogni richiesta. Non mettere chiavi in query, log o analytics. Il sito completo implementa già questo flusso.

CLI per il database dell’installazione, accessibile solo al gestore del server:

```sh
alba-local users --root /percorso/archivio-alba
alba-local web-key 123456789 --root /percorso/archivio-alba
alba-local backup --root /percorso/archivio-alba
```

Il CLI legge `.env` nella root: `ADMIN_IDS`, `PUBLIC_URL`, `MODEL`, `LLM_BACKEND`, `LLM_URL`. Per una prima installazione completa con download di dipendenze/modello e configurazione guidata BotFather o admin terminale, usa `python3 install.py` di alba-tramonto.

Memoria e feedback migliorano il contesto e lo stile; non viene effettuato fine-tuning dei pesi. Non è un sistema clinico né un servizio di emergenza. I controlli di provenienza riducono i ricordi inventati ma non garantiscono l’infallibilità delle risposte. Chi integra il kit conserva separatamente le chiavi locali, protegge il database e configura privacy, autorizzazioni e backup.

Licenza MIT; dipendenze e modelli hanno le rispettive licenze. Nessuna telemetria applicativa.

La consultazione amministrativa nel sito completo richiede `/memory_key` emesso dal proprietario in privato: codice monouso, 15 minuti, revocabile. Un integratore deve applicare lo stesso consenso sui propri endpoint; l’accesso diretto al database rimane riservato al gestore del server.

Verifica adapter: `python -m unittest discover -s tests` (7 test senza LLM: isolamento privato/gruppo, autorizzazioni, chiavi monouso, export altrui negato, consenso memoria e consolidamento). Il sito completo include altri 313 test.
