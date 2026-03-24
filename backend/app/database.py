from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from .config import settings
from . import models

async def init_db():
    """Initializes the MongoDB database connection and Beanie."""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    
    # Initialize Beanie with the Document models
    await init_beanie(
        database=client.get_default_database(),
        document_models=[
            models.User,
            models.Upload,
            models.Transaction,
            models.Correction
        ]
    )
    print("Database connection initialized with authentication support.")