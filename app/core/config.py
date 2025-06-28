"""
Configuration settings for the orgID API.
"""

class Settings:
    """Application settings."""
    
    # API settings
    API_V1_STR: str = ""
    PROJECT_NAME: str = "orgID API"
    
    # OpenAlex API settings
    OPENALEX_API_KEY: str = "PevDKCMHv88RXESPAWpja4"
    
    # File paths
    ROR_DATA_PATH: str = "ror_with_openalex.csv"
    
    # API endpoints
    TEST_DATA_URL: str = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_sVx4ts9ndZJ6UP8mPqKd-Rw_v-_A_ShaIvgIE4QhmdPeNb5H7GUPZIBZiMEXvLax1iAChlH6Mk6W/pub?output=csv"


settings = Settings()
