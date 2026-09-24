# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
        GEMINI_API_KEY: str = ""
        GEMINI_MODEL: str = "gemini-3.8-flash"
        GROQ_API_KEY: str = ""
        GROQ_MODEL: str = "openai/gpt-oss-20b"
        GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
        ZAI_API_KEY: str = ""
        ZAI_MODEL: str = "glm-4.7-flash"
        ZAI_VISION_MODEL: str = "glm-4.6v-flash"
        ZAI_BASE_URL: str = "https://api.z.ai/api/paas/v4"
        LLM_TIMEOUT_SECONDS: float = 30.0
        OCR_TIMEOUT_SECONDS: float = 90.0
        OCR_MAX_CONCURRENCY: int = 2
        OCR_ANNOTATION_PAGE_LIMIT: int = 3
        OCR_MAX_RETRIES: int = 2
        OCR_TABLE_PAGE_LIMIT: int = 20
        MONGO_URI: str = ""
        MONGO_MOCK: bool = False  # Test-only in-memory MongoDB implementation
        SECRET_KEY: str = ""
        # Pinecone Vector Database Configuration (Production-Ready)
        PINECONE_API_KEY: str = ""
        PINECONE_ENVIRONMENT: str = "us-east-1"  # Your Pinecone region
        PINECONE_INDEX_NAME: str = "financial-transactions"  # Your index name
        
        # Mistral OCR Configuration
        MISTRAL_API_KEY: str = ""  # Mistral API key for OCR 4.1 extraction
        MISTRAL_OCR_MODEL: str = "mistral-ocr-4-1"
        # Explicit opt-in for scanned/image-only PDFs that cannot be locally
        # redacted before hosted OCR. Keep false for privacy-first operation.
        ALLOW_UNREDACTED_OCR: bool = False

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

        # Privacy: visually redact phone/account/UPI/email spans in the PDF
        # before it is sent to OCR providers. Default False because redaction
        # can remove counterparty names from descriptions and hurt extraction
        # accuracy. Descriptions sent to LLM stages are always masked instead
        # (see node_verify). See README "Provider data-processing policy".
        OCR_MASK_PII_BEFORE_SEND: bool = False

        # Hosted-model concurrency is deliberately configuration-driven. Local
        # free-tier testing can keep this low, while enterprise deployments can
        # raise it without changing the processing code.
        CATEGORIZATION_BATCH_SIZE: int = 20
        LLM_BATCH_SIZE: int = 20
        LLM_MAX_CONCURRENCY: int = 3
        LLM_MAX_CONCURRENT_BATCHES: int = 2
        LLM_AGENT_RECURSION_LIMIT: int = 12

        # OpenTelemetry is optional. Set LANGFUSE_PUBLIC_KEY and
        # LANGFUSE_SECRET_KEY to export traces/metrics to Langfuse.
        OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
        OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: str = ""
        OTEL_EXPORTER_OTLP_HEADERS: str = ""
        OTEL_SERVICE_NAME: str = "bank-statement-analyzer"
        APP_ENV: str = "development"
        LANGFUSE_PUBLIC_KEY: str = ""
        LANGFUSE_SECRET_KEY: str = ""
        LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
        LANGFUSE_DASHBOARD_URL: str = ""

        # Durable MongoDB-backed post-processing worker. The web process runs a
        # small consumer by default for easy local use. Production can disable
        # it and run `python -m app.worker` as one or more dedicated workers.
        RUN_EMBEDDED_WORKER: bool = True
        JOB_POLL_INTERVAL_SECONDS: float = 2.0
        JOB_LEASE_SECONDS: int = 300
        JOB_MAX_ATTEMPTS: int = 5
        JOB_RETRY_BASE_SECONDS: int = 10

        # This line tells Pydantic to ignore any extra variables found in the .env file
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

if not settings.MONGO_URI:
    raise RuntimeError("MONGO_URI must be configured")
if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be configured with at least 32 characters")
