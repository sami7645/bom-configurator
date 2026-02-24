# BOM Konfigurator (Windows Setup)

Ein schlanker BOM‑Konfigurator auf Basis von Django.

## Systemvoraussetzungen

- Windows 10 oder 11  
- Python 3.8 oder höher (`py --version`)  
- Git (optional, für `git clone`)

## Schnelles Setup unter Windows

1. **Projekt holen**
   ```powershell
   git clone https://github.com/sami7645/bom-configurator.git
   cd bom-configurator
   ```

2. **Virtuelle Umgebung anlegen und aktivieren**
   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```

3. **Python‑Abhängigkeiten installieren**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Datenbank vorbereiten**
   ```powershell
   py manage.py migrate
   ```

5. **CSV‑Daten importieren**
   ```powershell
   py manage.py import_csv_data --force
   ```

6. **Admin‑Benutzer (optional, empfohlen)**
   ```powershell
   py manage.py createsuperuser
   ```

7. **Entwicklungsserver starten**
   ```powershell
   py manage.py runserver
   ```
   Öffne dann im Browser:  
   `http://127.0.0.1:8000`

## Nützliche Befehle

- Alle CSVs neu importieren:
  ```powershell
  py manage.py import_csv_data --force
  ```
- Admin‑Bereich:  
  `http://127.0.0.1:8000/admin/`

## Artikel / CSV‑Daten aktualisieren (Kurzfassung)

- **1. Datenquelle**:  
  Die Stammdaten liegen in einer Excel‑Datei (z.B. in `main excel/…xlsx`).  
  Die Anwendung selbst liest nur aus den CSV‑Dateien im Ordner `csv_files` und der Datenbank.

- **2. Artikel hinzufügen oder ändern** (Standardweg über Excel):
  1. Excel‑Datei öffnen und das passende Tabellenblatt wählen (z.B. `Schacht`, `HVB`, `DFM`, `Sondengröße - Sondenlänge`, …).
  2. **Neuen Artikel**: Neue Zeile am Ende einfügen und alle benötigten Spalten ausfüllen (Artikelnummer, Bezeichnung, Mengen, Kompatibilität etc.).  
     **Artikel ändern**: Bestehende Zeile suchen und nur die gewünschten Werte anpassen.
  3. Excel speichern.
  4. Im Projektordner im Terminal ausführen:
     ```powershell
     py manage.py import_csv_data --force
     ```

- **3. Einzelnes CSV direkt anpassen** (nur für erfahrene Nutzer):
  1. CSV‑Datei im Ordner `csv_files` öffnen.
  2. Nur Zeilen unterhalb der Kopfzeile bearbeiten (keine Spaltenüberschriften ändern oder löschen).
  3. CSV speichern.
  4. Optional gezielt nur einzelne Datei importieren, z.B.:
     ```powershell
     py manage.py import_csv_data --file DFM.csv --force
     ```

- **4. Mehr Details / Beispiele**:  
  Siehe Ordner `updating/`:
  - `updating/UPDATE_ARTICLES_EN.txt` – ausführliche Anleitung auf Englisch  
  - `updating/UPDATE_ARTICLES_DE.txt` – ausführliche Anleitung auf Deutsch

