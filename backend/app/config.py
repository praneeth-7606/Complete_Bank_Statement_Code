# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
        GEMINI_API_KEY: str = ""
        GEMINI_MODEL: str = "gemini-2.5-flash"
        GROQ_API_KEY: str = ""
        GROQ_MODEL: str = "openai/gpt-oss-20b"
        GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
        MONGO_URI: str = ""
        SECRET_KEY: str = ""
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

        # Groww MCP Configuration
        GROWW_MCP_SERVER_COMMAND: str = ""  # Local stdio command, e.g., "uvx groww-mcp-server"
        GROWW_MCP_SERVER_URL: str = ""      # Remote SSE URL if applicable
        GROWW_API_KEY: str = ""
        GROWW_API_SECRET: str = ""

        # Request/resource controls
        MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024
        MAX_UPLOAD_PAGES: int = 100
        MAX_BATCH_STATEMENTS: int = 10

        # This line tells Pydantic to ignore any extra variables found in the .env file
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

if not settings.MONGO_URI:
    raise RuntimeError("MONGO_URI must be configured")
if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be configured with at least 32 characters")
