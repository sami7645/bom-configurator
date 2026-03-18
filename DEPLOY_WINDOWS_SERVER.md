## BOM Configurator – Einfach auf Windows Server installieren

Die folgenden Schritte sind für eine **einfache Installation** auf einem Windows Server gedacht.  
Ziel: Ein nicht‑technischer Benutzer kann das Projekt selbst starten.

### 1. Programme installieren (einmalig)

Auf dem Server:

1. **Git for Windows** installieren  
2. **Python 3.12 (64‑bit)** installieren  
   - Beim Setup das Häkchen **“Add python.exe to PATH”** setzen

### 2. Projekt herunterladen (einmalig)

PowerShell als Administrator öffnen:

```powershell
mkdir C:\apps
cd C:\apps
git clone <IHRE_GITHUB_URL> bom-configurator
cd bom-configurator
```

> `<IHRE_GITHUB_URL>` durch die echte HTTPS‑URL des Repositories ersetzen.

### 3. Python‑Umgebung und Bibliotheken installieren (einmalig)

```powershell
cd C:\apps\bom-configurator

py -m venv .venv
.\.venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Einstellungen (`.env`)

Für den Client wird die Datei `.env` bereits **fertig mitgeliefert**.  
Es sind **keine Änderungen** an dieser Datei nötig.

Die Anwendung verwendet standardmäßig eine lokale SQLite‑Datenbank – es ist
keine zusätzliche Datenbank‑Installation erforderlich.

### 5. Datenbank vorbereiten und CSV‑Daten importieren (einmalig)

```powershell
cd C:\apps\bom-configurator
.\.venv\Scripts\activate

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py import_csv_data
```

Warten, bis der Vorgang ohne Fehlermeldungen durchgelaufen ist.

### 6. Anwendung starten (jedes Mal, wenn Sie sie nutzen wollen)

```powershell
cd C:\apps\bom-configurator
.\.venv\Scripts\activate

python manage.py runserver 0.0.0.0:8001
```

Dieses Fenster muss **offen bleiben**, solange der Konfigurator genutzt wird.

### 7. Aufruf im Browser

Auf dem Server oder einem anderen PC im gleichen Netzwerk den Browser öffnen und:

```text
http://SERVERNAME:8001/
```

eingeben.

- `SERVERNAME` durch den Namen oder die IP‑Adresse des Windows‑Servers ersetzen  
- Beispiel: `http://bom-server:8001/` oder `http://192.168.1.50:8001/`

Fertig. Damit ist der BOM‑Konfigurator einsatzbereit.  
Später kann man ihn auf Wunsch noch als Windows‑Dienst oder hinter IIS (HTTPS) betreiben – für die Grundnutzung ist das aber nicht nötig.

