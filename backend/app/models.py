# app/models.py
from beanie import Document
from pydantic import BaseModel, Field, EmailStr
import uuid
import datetime
from typing import List, Dict, Any, Optional

# --- Beanie Document Models (for MongoDB) ---

class User(Document):
    """Represents a user account in the database."""
    model_config = {"arbitrary_types_allowed": True}
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()), unique=True)
    
    # User credentials
    email: EmailStr
    hashed_password: Optional[str] = None  # None for Google OAuth users
    full_name: str
    
    # OAuth fields
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None
    
    # Account status
    is_active: bool = True
    is_verified: bool = False
    
    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    last_login: Optional[datetime.datetime] = None
    
    class Settings:
        name = "users"
        indexes = ["email", "google_id"]

class Transaction(Document):
    """Represents a single transaction document in the database."""
    model_config = {"arbitrary_types_allowed": True}
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()), unique=True)
    
    # Core transaction fields
    date: datetime.date
    description: str
    amount: float
    category: str
    upload_id: str
    user_id: Optional[str] = None  # Link to user who uploaded this transaction

    # --- FIX IMPLEMENTED HERE ---
    # Add explicit fields for debit and credit to enable precise filtering.
    debit: float = 0.0
    credit: float = 0.0
    # --- END OF FIX ---
    
    # Encrypted fields for sensitive data
    description_encrypted: Optional[str] = None  # Encrypted version of description
    reference_encrypted: Optional[str] = None  # Encrypted transaction reference
    narration_encrypted: Optional[str] = None  # Encrypted narration field

    class Settings:
        name = "transactions" # MongoDB collection name
        indexes = ["user_id", "upload_id", "date", "category"]

class Upload(Document):
    """Represents a record of a file upload with comprehensive metadata."""
    model_config = {"arbitrary_types_allowed": True}
    
    # Basic info
    filename: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    user_id: Optional[str] = None  # Link to user who uploaded this statement
    
    # Processing metadata
    bank_name: Optional[str] = None
    extraction_method: Optional[str] = None  # PDFPLUMBER, GEMINI_TEXT, GEMINI_VISION
    processing_time_seconds: Optional[float] = None
    total_transactions: int = 0
    
    # File metadata
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    
    # Status
    status: str = "processing"  # processing, completed, failed
    error_message: Optional[str] = None
    
    # AI Insights
    insights: Optional[List[str]] = None
    
    # Background task status
    db_save_completed: bool = False
    vector_index_completed: bool = False
    
    # Timestamps
    processed_at: Optional[datetime.datetime] = None
    
    class Settings:
        name = "uploads"
        indexes = ["user_id", "timestamp"]

class Correction(Document):
    """Represents a user-defined rule for correcting categories."""
    model_config = {"arbitrary_types_allowed": True}
    transaction_description_keyword: str
    correct_category: str
    user_id: Optional[str] = None # Personalized learning

    class Settings:
        name = "corrections"
        indexes = ["transaction_description_keyword", "user_id"]

# --- Pydantic Models (for API request/response validation) ---

class CorrectionCreate(BaseModel):
    """Model for creating a new correction rule."""
    transaction_description_keyword: str
    correct_category: str
    user_id: Optional[str] = None

class Analysis(BaseModel):
    """Model for the financial analysis part of the report."""
    summary: Dict[str, Any]
    category_wise_split: Dict[str, float]
    insights: List[str]

class FullReport(BaseModel):
    """The final, complete report returned after processing a statement."""
    upload_id: str
    transactions: List[Dict[str, Any]]
    analysis: Analysis
    model_config = {"arbitrary_types_allowed": True}

class ChatQuery(BaseModel):
    """The request model for the chat endpoint."""
    query: str
    chat_history: Optional[List[Dict[str, str]]] = None # To support session-based state
    page: int = 1  
    page_size: int = 50 

class ChatResponse(BaseModel):
    """The response model for the chat endpoint."""
    answer: str

class SingleStatementReport(BaseModel):
    """A report for a single statement within a batch."""
    filename: str
    upload_id: str
    transactions: List[Dict[str, Any]]
    analysis: Analysis
    model_config = {"arbitrary_types_allowed": True}

class BatchProcessRequest(BaseModel):
    """Model for the incoming batch request."""
    statements: List[Dict[str, str]] # Expects [{"filename": "doc1.pdf", "password": "pwd1"}, ...]

class BatchReport(BaseModel):
    """The final aggregated report for the entire batch."""
    total_statements_processed: int
    total_transactions_recorded: int
    statement_reports: List[SingleStatementReport]
    overall_analysis_summary: Dict[str, Any] # Aggregated summary from all analyses
    model_config = {"arbitrary_types_allowed": True}




# Add these new models to app/models.py

class MultiStatementRequest(BaseModel):
    """Request model for initiating multi-statement upload"""
    statement_count: int = Field(..., ge=1, le=10, description="Number of statements to process (1-10)")

class StatementFile(BaseModel):
    """Individual statement file info"""
    filename: str
    upload_id: str
    transaction_count: int
    status: str

class MultiStatementResponse(BaseModel):
    """Response for multi-statement processing"""
    total_statements: int
    processed_successfully: int
    failed_statements: int
    statements: List[StatementFile]
    combined_analysis: Analysis
    total_transactions: int
    message: str

# --- Authentication Models ---

class UserSignup(BaseModel):
    """Model for user signup request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str = Field(..., min_length=2, description="Full name is required")

class UserLogin(BaseModel):
    """Model for user login request"""
    email: EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    """Model for Google OAuth login"""
    token: str  # Google ID token

class TokenResponse(BaseModel):
    """Model for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserResponse(BaseModel):
    """Model for user data response"""
    user_id: str
    email: str
    full_name: str
    profile_picture: Optional[str] = None
    is_verified: bool
    created_at: datetime.datetime