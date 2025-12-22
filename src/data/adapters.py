"""Data adapters for CSV files and WHO API."""

import csv
import requests
from pathlib import Path


class DataAdapter():
    """Base adapter interface. Subclasses must implement fetch(), source_name, source_type."""
    
    def fetch(self):
        """Fetch data and return as list of dicts."""
        pass
    
    @property
    def source_name(self):
        """Return human-readable name for this data source."""
        pass
    
    @property
    def source_type(self):
        """Return source type: 'csv' or 'api'."""
        pass


class CSVAdapter(DataAdapter):
    """Adapter for CSV file import."""
    
    def __init__(self, filepath):
        """Init with filepath. Raises FileNotFoundError if missing."""
        self.filepath = Path(filepath)
        
        if not self.filepath.exists():
            raise FileNotFoundError("CSV file not found: " + str(filepath))
    
    def fetch(self):
        """Read CSV and return list of dicts. Empty strings become None."""
        records = []
        file = open(self.filepath, 'r', encoding='utf-8-sig')  # utf-8-sig handles Excel BOM
        
        try:
            reader = csv.DictReader(file)
            for row in reader:
                cleaned_row = {k: (v if v != "" else None) for k, v in row.items()}
                records.append(cleaned_row)        
        finally:
            file.close()      
        return records
    
    @property
    def source_name(self):
        """Return filename."""
        return self.filepath.name
    
    @property
    def source_type(self):
        """Return 'csv'."""
        return "csv"


class WHOAPIAdapter(DataAdapter):
    """Adapter for WHO Global Health Observatory API."""
    
    BASE_URL = "https://ghoapi.azureedge.net/api"
    
    # Map friendly names to WHO indicator codes
    INDICATORS = {
        "life_expectancy": "WHOSIS_000001",
        "infant_mortality": "MDG_0000000001",
        "vaccination_dtp3": "WHS4_100",
        "vaccination_measles": "WHS8_110",
        "neonatal_mortality": "MDG_0000000003",
    }
    
    def __init__(self, indicator="life_expectancy", limit=1000):
        """Init with indicator name/code and fetch limit."""
        self.indicator_name = indicator
        
        if indicator in self.INDICATORS:
            self.indicator_code = self.INDICATORS[indicator]
        else:
            self.indicator_code = indicator
        
        self.limit = limit
    
    def fetch(self):
        """Fetch from WHO API and return normalized list of dicts."""
        url = self.BASE_URL + "/" + self.indicator_code
        params = {"$top": self.limit}
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        raw_records = data.get("value", [])
        
        cleaned_records = []
        for record in raw_records:
            cleaned_record = {
                "indicator_code": record.get("IndicatorCode"),
                "country_code": record.get("SpatialDim"),
                "year": record.get("TimeDim"),
                "value": record.get("NumericValue"),
                "sex": record.get("Dim1"),
                "age_group": record.get("Dim2"),
            }
            cleaned_records.append(cleaned_record)
        
        return cleaned_records
    
    @property
    def source_name(self):
        """Return WHO_GHO_{indicator_name}."""
        return "WHO_GHO_" + self.indicator_name
    
    @property
    def source_type(self):
        """Return 'api'."""
        return "api"
