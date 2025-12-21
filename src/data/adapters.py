"""
Data Adapters Module
====================

Contains base adapter class and all data source adapter implementations.
"""

import csv
import requests
from pathlib import Path


class DataAdapter():
    """
    Abstract base class defining the interface for all data source adapters.
    
    This follows the Adapter design pattern, allowing different data sources
    to be used interchangeably. Any class inheriting from DataAdapter must
    implement all methods and properties.
    
    The adapter pattern provides:
    - Consistent interface for different data sources
    - Easy extensibility (add new sources by creating new adapters)
    - Separation of concerns (each adapter handles its own data format)
    """
    
    def fetch(self):
        """
        Fetch data from the source and return as a list of dictionaries.
        
        Each dictionary represents one row/record, with keys being
        column names and values being the data.
        
        Returns:
            list: A list of dictionaries containing the fetched data
        """
        pass
    
    @property
    def source_name(self):
        """
        Return a human-readable name identifying this data source.
        
        Returns:
            str: The name of the data source (e.g., filename or API name)
        """
        pass
    
    @property
    def source_type(self):
        """
        Return the type of data source.
        
        Returns:
            str: Either 'csv' or 'api'
        """
        pass


# =============================================================================
# CSV ADAPTER
# =============================================================================

class CSVAdapter(DataAdapter):
    """
    Adapter for importing data from CSV files.
    
    This adapter can handle any CSV file structure. Column names and values
    are preserved exactly as they appear in the source file.
    
    Attributes:
        filepath (Path): Path to the CSV file to import
    """
    
    def __init__(self, filepath):
        """
        Initialize the CSV adapter with a file path.
        
        Args:
            filepath (str or Path): Path to the CSV file
            
        Raises:
            FileNotFoundError: If the specified file does not exist
        """
        self.filepath = Path(filepath)
        
        if not self.filepath.exists():
            raise FileNotFoundError("CSV file not found: " + str(filepath))
    
    def fetch(self):
        """
        Read the CSV file and return data as a list of dictionaries.
        
        Empty strings are converted to None for consistency in data handling.
        The csv.DictReader automatically uses the first row as headers.
        
        Returns:
            list: List of dictionaries, one per row in the CSV
        """
        records = []
        
        # utf-8-sig encoding handles BOM that Excel adds to CSV files
        file = open(self.filepath, 'r', encoding='utf-8-sig')
        
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
        """Return the filename as the source name."""
        return self.filepath.name
    
    @property
    def source_type(self):
        """Return 'csv' as the source type."""
        return "csv"


# =============================================================================
# WHO API ADAPTER
# =============================================================================

class WHOAPIAdapter(DataAdapter):
    """
    Adapter for fetching data from the WHO Global Health Observatory API.
    
    The WHO GHO API provides access to various health indicators such as
    life expectancy, mortality rates, and vaccination coverage statistics.
    
    API Documentation: https://www.who.int/data/gho/info/gho-odata-api
    
    Attributes:
        indicator_code (str): The WHO indicator code to fetch
        indicator_name (str): Human-readable name for the indicator
        limit (int): Maximum number of records to fetch
    """
    
    # Base URL for the WHO GHO API
    BASE_URL = "https://ghoapi.azureedge.net/api"
    
    # Dictionary mapping friendly names to WHO indicator codes
    # This makes it easier for users to request common indicators
    INDICATORS = {
        "life_expectancy": "WHOSIS_000001",
        "infant_mortality": "MDG_0000000001",
        "vaccination_dtp3": "WHS4_100",
        "vaccination_measles": "WHS8_110",
        "neonatal_mortality": "MDG_0000000003",
    }
    
    def __init__(self, indicator="life_expectancy", limit=1000):
        """
        Initialize the WHO API adapter.
        
        Args:
            indicator (str): Either a key from INDICATORS dict or a raw 
                           WHO indicator code
            limit (int): Maximum number of records to fetch (default 1000)
        """
        self.indicator_name = indicator
        
        if indicator in self.INDICATORS:
            self.indicator_code = self.INDICATORS[indicator]
        else:
            self.indicator_code = indicator
        
        self.limit = limit
    
    def fetch(self):
        """
        Fetch data from the WHO GHO API.
        
        The API returns JSON data which is parsed and simplified into
        a consistent dictionary format.
        
        Returns:
            list: List of dictionaries containing health indicator data
            
        Raises:
            requests.RequestException: If the API request fails
        """
        url = self.BASE_URL + "/" + self.indicator_code
        params = {"$top": self.limit}
        
        # Timeout prevents hanging on slow connections
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
        """Return a descriptive name for this API data source."""
        return "WHO_GHO_" + self.indicator_name
    
    @property
    def source_type(self):
        """Return 'api' as the source type."""
        return "api"
