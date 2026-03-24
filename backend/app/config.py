# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
        GEMINI_API_KEY: str
        MONGO_URI: str
        SECRET_KEY: str = "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
        GOOGLE_CLIENT_ID: str = ""  # Optional, for Google OAuth

        # Pinecone Vector Database Configuration (Production-Ready)
        PINECONE_API_KEY: str = ""
        PINECONE_ENVIRONMENT: str = "us-east-1"  # Your Pinecone region
        PINECONE_INDEX_NAME: str = "financial-transactions"  # Your index name
        
        # Mistral OCR Configuration
        MISTRAL_API_KEY: str = ""  # Mistral API key for OCR 3 extraction

        # Data Encryption Configuration (for database encryption)
        ENCRYPTION_KEY: str = ""  # Base64-encoded 256-bit key
        ENCRYPTION_SALT: str = ""  # Base64-encoded salt

        # This line tells Pydantic to ignore any extra variables found in the .env file
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()