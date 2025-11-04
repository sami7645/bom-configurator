# BOM Konfigurator

Ein professioneller Bill of Materials (BOM) Konfigurator, entwickelt für Ingenieure und technische Anwendungen.

## Funktionen

### 🔧 Hauptfunktionen
- **Intelligente BOM-Generierung**: Automatische Berechnung aller erforderlichen Komponenten
- **Dynamische CSV-Integration**: Echtzeit-Synchronisation mit CSV-Dateien
- **Artikelnummer-Management**: Intelligente Erkennung bestehender Konfigurationen
- **GN X Kammer-Spezialbehandlung**: Automatische HVB-größenabhängige Artikelauswahl

### 📊 Konfigurationsoptionen
- Schachttypen (GN X1, GN X2, GN X3, GN X4, GN 1, GN 2, GN R Serie)
- HVB-Größen (63mm bis 355mm)
- Sonden-Durchmesser und -anzahl
- Sondenabstände und Anschlussarten
- Zusätzliche Komponenten (Kugelhähne, Durchflussmesser)

### 🎯 Zielgruppe
- Bauingenieure
- Technische Planer
- Projektmanager
- Systemintegratoren

## Installation

### Voraussetzungen
- Python 3.8+
- Django 5.2.7

### Setup
1. **Repository klonen oder Dateien kopieren**
2. **Virtuelle Umgebung erstellen** (empfohlen):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # oder
   source venv/bin/activate  # Linux/Mac
   ```

3. **Abhängigkeiten installieren**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Datenbank migrieren**:
   ```bash
   python manage.py migrate
   ```

5. **CSV-Daten importieren**:
   ```bash
   python manage.py import_csv_data
   ```

6. **Admin-Benutzer erstellen**:
   ```bash
   python manage.py createsuperuser
   ```

7. **Entwicklungsserver starten**:
   ```bash
   python manage.py runserver
   ```

8. **Anwendung öffnen**: http://localhost:8000

## Verwendung

### 1. Dashboard
- Übersicht über verfügbare Schachttypen und HVB-Größen
- Schnellzugriff auf letzte Konfigurationen
- Systemstatistiken

### 2. BOM Konfigurator
**Schritt 1: Grundkonfiguration**
- Konfigurationsname eingeben
- Schachttyp auswählen
- HVB-Größe definieren
- Anschlussart wählen

**Schritt 2: Sonden-Konfiguration**
- Sonden-Durchmesser auswählen
- Anzahl Sonden definieren
- Sondenabstand festlegen
- Zuschläge anpassen

**Schritt 3: Zusätzliche Komponenten**
- Kugelhahn-Typ (optional)
- Durchflussmesser-Typ (optional)
- GN X Kammer-Artikel (automatisch bei GN X Typen)

**Schritt 4: Konfiguration prüfen**
- Automatische Prüfung auf bestehende Konfigurationen
- Artikelnummer-Verwaltung
- Mutterartikel-Erkennung

**Schritt 5: BOM generieren**
- Vollständige Stückliste
- Exportfunktion
- Druckansicht

### 3. Konfigurationsverwaltung
- Alle Konfigurationen anzeigen
- Details einsehen
- Konfigurationen löschen
- Suchfunktion

### 4. Admin-Bereich
- CSV-Daten verwalten
- Artikelstammdaten bearbeiten
- Systemeinstellungen
- Benutzerverwaltung

## CSV-Datenstruktur

Die Anwendung verwendet folgende CSV-Dateien im `excel_sheets_extracted/` Verzeichnis:

### Hauptdateien
- **Schacht.csv**: Schachttypen und Artikelnummern
- **HVB.csv**: Hauptverteilerbalken-Größen
- **Sondengroesse - Sondenlaenge.csv**: Sonden-Spezifikationen
- **Sondenabstaende.csv**: Abstandsoptionen
- **Kugelhaehne.csv**: Kugelhahn-Varianten
- **DFM.csv**: Durchflussmesser-Typen

### Zusatzdateien
- **Entlueftung.csv**: Entlüftungskomponenten
- **Sondenverschlusskappe.csv**: Verschlusskappen
- **Stumpfschweiss-Endkappen.csv**: Endkappen
- **WP-Verschlusskappen.csv**: Wärmepumpen-Verschlüsse
- **WPA.csv**: Wärmepumpen-Anschlüsse
- **Verrohrung.csv**: Verrohrungskomponenten

### Automatische Synchronisation
- Änderungen in CSV-Dateien werden automatisch erkannt
- Reimport mit: `python manage.py import_csv_data --force`
- Unterstützt verschiedene Encodings (UTF-8, Latin1, CP1252)

## Besondere Funktionen

### Artikelnummer-Management
1. **Vollständige Konfiguration**: Existiert bereits → Artikelnummer anzeigen
2. **Mutterartikel**: Basis existiert → Automatische Kindnummer-Generierung
3. **Neue Konfiguration**: Komplett neu → Manuelle Artikelnummer-Eingabe

### GN X Kammer-Behandlung
- Automatische Erkennung von GN X1, GN X2, GN X3, GN X4
- HVB-größenabhängige Zusatzartikel:
  - 63-125mm: Artikel 2001837, 2001838
  - 140-180mm: Artikel 2001839, 2001840
  - 200-250mm: Artikel 2001841, 2001842
- Benutzerdefinierte Mengen möglich

### Formel-Berechnung
Unterstützt dynamische Berechnungen mit Variablen:
- `sondenanzahl`: Anzahl der Sonden
- `sondenabstand`: Abstand zwischen Sonden
- `zuschlag_links`: Linker Zuschlag
- `zuschlag_rechts`: Rechter Zuschlag

Beispiel: `=(sondenanzahl-1) * sondenabstand * 2 + zuschlag_links + zuschlag_rechts`

## Technische Details

### Architektur
- **Backend**: Django 5.2.7
- **Frontend**: Bootstrap 5.3, jQuery 3.7
- **Datenbank**: SQLite (Standard), PostgreSQL/MySQL unterstützt
- **Styling**: Professionelles Engineering-Theme

### Sicherheit
- CSRF-Schutz aktiviert
- SQL-Injection-Schutz durch Django ORM
- Eingabevalidierung auf Client- und Server-Seite

### Performance
- Optimierte Datenbankabfragen
- Lazy Loading für große Datensätze
- Client-seitiges Caching

## Wartung

### CSV-Daten aktualisieren
```bash
# Einzelne Datei
python manage.py import_csv_data --file Schacht.csv --force

# Alle Dateien
python manage.py import_csv_data --force
```

### Datenbank-Backup
```bash
python manage.py dumpdata > backup.json
```

### Logs einsehen
- Django-Logs: Console-Output
- Admin-Aktionen: Django Admin Interface

## Anpassungen

### Neue CSV-Felder hinzufügen
1. Model in `configurator/models.py` erweitern
2. Migration erstellen: `python manage.py makemigrations`
3. Migration anwenden: `python manage.py migrate`
4. Import-Funktion in `import_csv_data.py` anpassen

### UI-Anpassungen
- CSS: `static/css/style.css`
- JavaScript: `static/js/main.js`, `static/js/configurator.js`
- Templates: `templates/configurator/`

### Neue Berechnungslogik
- Views: `configurator/views.py`
- Models: `configurator/models.py`

## Support

### Häufige Probleme
1. **CSV-Import schlägt fehl**: Encoding prüfen, BOM entfernen
2. **Leere Dropdowns**: CSV-Daten importieren
3. **Formelfehler**: Syntax und Variablennamen prüfen

### Debugging
```bash
# Debug-Modus aktivieren
DEBUG = True  # in settings.py

# Detaillierte Logs
python manage.py runserver --verbosity=2
```

## Lizenz

Entwickelt für technische Präzision und professionelle Anwendungen.

---

**Version**: 1.0  
**Entwickelt**: November 2024  
**Kompatibilität**: Django 5.2+, Python 3.8+
