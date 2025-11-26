from django.db import models
import json
import re
from decimal import Decimal


class CSVDataSource(models.Model):
    """Model to track CSV files and their last modification times"""
    name = models.CharField(max_length=100, unique=True)
    file_path = models.CharField(max_length=500)
    last_modified = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name


class Schacht(models.Model):
    """Schacht (Shaft) types from Schacht.csv"""
    schachttyp = models.CharField(max_length=100, unique=True)
    artikelnummer = models.CharField(max_length=50, blank=True, null=True)
    artikelbezeichnung = models.CharField(max_length=200, blank=True, null=True)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return self.schachttyp
    
    class Meta:
        verbose_name_plural = "Schächte"


class HVB(models.Model):
    """Hauptverteilerbalken (Main Distribution Beam) from HVB.csv"""
    hauptverteilerbalken = models.CharField(max_length=50)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"HVB {self.hauptverteilerbalken}"
    
    class Meta:
        verbose_name_plural = "HVBs"


class Sondengroesse(models.Model):
    """Probe sizes and lengths from Sondengroesse - Sondenlaenge.csv"""
    durchmesser_sonde = models.CharField(max_length=10)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    schachttyp = models.CharField(max_length=100)
    hvb = models.CharField(max_length=50)
    bauform = models.CharField(max_length=50, blank=True, null=True)
    sondenanzahl_min = models.IntegerField(blank=True, null=True)
    sondenanzahl_max = models.IntegerField(blank=True, null=True)
    ruecklauf_laenge = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    vorlauf_laenge = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    vorlauf_formel = models.CharField(max_length=200, blank=True, null=True)
    ruecklauf_formel = models.CharField(max_length=200, blank=True, null=True)
    hinweis = models.CharField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return f"Sonde {self.durchmesser_sonde}mm - {self.schachttyp}"
    
    class Meta:
        verbose_name_plural = "Sondengrößen"


class Sondenabstand(models.Model):
    """Probe distances from Sondenabstaende.csv"""
    sondenabstand = models.IntegerField()
    anschlussart = models.CharField(max_length=50)
    zuschlag_links = models.IntegerField()
    zuschlag_rechts = models.IntegerField()
    hinweis = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.sondenabstand}mm - {self.anschlussart}"
    
    class Meta:
        verbose_name_plural = "Sondenabstände"


class Kugelhahn(models.Model):
    """Ball valves from Kugelhaehne.csv"""
    kugelhahn = models.CharField(max_length=100)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    et_hvb = models.CharField(max_length=200, blank=True, null=True)  # Compatibility with HVB
    et_sonden = models.CharField(max_length=200, blank=True, null=True)  # Compatibility with probes
    kh_hvb = models.CharField(max_length=200, blank=True, null=True)  # Ball valve HVB compatibility
    
    def __str__(self):
        return f"{self.kugelhahn} - {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "Kugelhähne"


class DFM(models.Model):
    """Flow meters from DFM.csv"""
    durchflussarmatur = models.CharField(max_length=100)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    et_hvb = models.CharField(max_length=200, blank=True, null=True)
    et_sonden = models.CharField(max_length=200, blank=True, null=True)
    dfm_hvb = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.durchflussarmatur} - {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "DFMs"


class Entlueftung(models.Model):
    """Ventilation components from Entlueftung.csv"""
    name = models.CharField(max_length=100)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    et_hvb = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "Entlüftungen"


class Sondenverschlusskappe(models.Model):
    """Probe closure caps from Sondenverschlusskappe.csv"""
    name = models.CharField(max_length=100)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    sonden_durchmesser = models.CharField(max_length=10, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "Sondenverschlusskappen"


class StumpfschweissEndkappe(models.Model):
    """Butt weld end caps from Stumpfschweiss-Endkappen.csv"""
    name = models.CharField(max_length=100)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    hvb_durchmesser = models.CharField(max_length=10, blank=True, null=True)
    is_short_version = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} - {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "Stumpfschweiss-Endkappen"


class WPVerschlusskappe(models.Model):
    """Heat pump closure caps from WP-Verschlusskappen.csv"""
    name = models.CharField(max_length=100)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "WP-Verschlusskappen"


class WPA(models.Model):
    """Heat pump components from WPA.csv"""
    name = models.CharField(max_length=100)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "WPAs"


class Verrohrung(models.Model):
    """Piping components from Verrohrung.csv"""
    verrohrung = models.CharField(max_length=100)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.verrohrung} - {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "Verrohrungen"


class Schachtgrenze(models.Model):
    """Shaft boundaries from Schachtgrenze.csv"""
    name = models.CharField(max_length=100)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "Schachtgrenzen"


class Schachtkompatibilitaet(models.Model):
    """Shaft compatibility from Schachtkompatibilitaet.csv"""
    name = models.CharField(max_length=100)
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge_statisch = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    menge_formel = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "Schachtkompatibilitäten"


class BOMConfiguration(models.Model):
    """Main BOM Configuration model"""
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Configuration parameters
    schachttyp = models.CharField(max_length=100)
    hvb_size = models.CharField(max_length=50)
    sonden_durchmesser = models.CharField(max_length=10)
    sondenanzahl = models.IntegerField()
    sondenabstand = models.IntegerField()
    anschlussart = models.CharField(max_length=50)
    kugelhahn_type = models.CharField(max_length=100, blank=True, null=True)
    dfm_type = models.CharField(max_length=100, blank=True, null=True)
    dfm_category = models.CharField(max_length=50, blank=True, null=True)
    bauform = models.CharField(max_length=1, choices=(('I', 'I-Form'), ('U', 'U-Form')), default='I')
    
    # Article number management
    mother_article_number = models.CharField(max_length=50, blank=True, null=True)
    child_article_number = models.CharField(max_length=50, blank=True, null=True)
    full_article_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Configuration status
    is_existing_configuration = models.BooleanField(default=False)
    is_existing_mother_article = models.BooleanField(default=False)
    
    # Additional parameters for calculations
    zuschlag_links = models.IntegerField(default=100)
    zuschlag_rechts = models.IntegerField(default=100)
    
    def __str__(self):
        return f"{self.name} - {self.schachttyp}"
    
    def calculate_quantities(self):
        """Calculate quantities based on formulas"""
        context = {
            'sondenanzahl': self.sondenanzahl,
            'sondenabstand': self.sondenabstand,
            'zuschlag_links': self.zuschlag_links,
            'zuschlag_rechts': self.zuschlag_rechts,
        }
        return context
    
    def generate_article_number(self):
        """Generate article number based on configuration"""
        if self.full_article_number:
            return self.full_article_number
        elif self.mother_article_number:
            # Auto-generate child number if mother exists
            return f"{self.mother_article_number}-001"
        else:
            # New configuration - needs manual input
            return None
    
    class Meta:
        verbose_name_plural = "BOM Configurations"


class BOMItem(models.Model):
    """Individual items in a BOM configuration"""
    configuration = models.ForeignKey(BOMConfiguration, on_delete=models.CASCADE, related_name='items')
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    menge = models.DecimalField(max_digits=10, decimal_places=3)
    calculated_quantity = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    source_table = models.CharField(max_length=50)  # Which CSV/model this item came from
    
    def __str__(self):
        return f"{self.artikelnummer} - {self.menge}"
    
    class Meta:
        verbose_name_plural = "BOM Items"


class GNXChamberArticle(models.Model):
    """Special articles for GN X chambers based on HVB size"""
    hvb_size_min = models.IntegerField()
    hvb_size_max = models.IntegerField()
    artikelnummer = models.CharField(max_length=50)
    artikelbezeichnung = models.CharField(max_length=200)
    is_automatic = models.BooleanField(default=True)  # Auto-selected based on HVB size
    
    def __str__(self):
        return f"GNX {self.hvb_size_min}-{self.hvb_size_max}mm: {self.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "GN X Chamber Articles"


class GNXChamberConfiguration(models.Model):
    """Configuration for GN X chambers with custom quantities"""
    bom_configuration = models.ForeignKey(BOMConfiguration, on_delete=models.CASCADE)
    gnx_article = models.ForeignKey(GNXChamberArticle, on_delete=models.CASCADE)
    custom_quantity = models.DecimalField(max_digits=10, decimal_places=3)
    
    def __str__(self):
        return f"{self.bom_configuration.name} - {self.gnx_article.artikelnummer}"
    
    class Meta:
        verbose_name_plural = "GN X Chamber Configurations"