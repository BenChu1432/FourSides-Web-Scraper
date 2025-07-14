class NewsParsingError(Exception):
    """Base class for parsing-related errors."""
    pass

class UnmappedMediaNameError(NewsParsingError):
    def __init__(self, alt_value: str):
        super().__init__(f"❌ Failed to map Chinese media name: '{alt_value}' to English abbreviation.")
        self.alt_value = alt_value

