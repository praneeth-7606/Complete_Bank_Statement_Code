from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from .config import settings
from . import models

async def init_db():
    """Initializes the MongoDB database connection and Beanie."""
    if settings.MONGO_MOCK:
        from mongomock_motor import AsyncMongoMockClient

        client = AsyncMongoMockClient()
        database = client.get_database("financial_e2e")
    else:
        client = AsyncIOMotorClient(settings.MONGO_URI)
        database = client.get_default_database()
    
    # Initialize Beanie with the Document models
    await init_beanie(
        database=database,
        document_models=[
            models.User,
            models.Upload,
            models.Transaction,
            models.Correction,
            models.ProcessingJob,
            models.ObservabilityTrace,
        ]
    )
    print("Database connection initialized with authentication support.")
