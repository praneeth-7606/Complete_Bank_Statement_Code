
from contextlib import asynccontextmanager
import uuid
import json
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import datetime
import asyncio
import logging
from . import models, agents
from .models import MultiStatementResponse, StatementFile
from .database import init_db
from .agentic_rag import AgenticRAGPipeline
from .auth_router import router as auth_router
from . import auth_utils
from .smart_extractor import get_smart_extractor
from .log_streamer import log_streamer
from .logging_config import setup_logging
from .data_encryptor import DataEncryptor, EncryptionError
from .config import settings
from .investment.router import router as investment_router

# Initialize Logging for Terminal Visibility
setup_logging()

logger = logging.getLogger(__name__)

# Initialize SMART EXTRACTOR - Auto-classifies PDFs and uses best method
smart_extractor = None  # Will be initialized on first use

# Global in-memory session history (simple version)
# In production, this would be in Redis or MongoDB
SESSION_HISTORY: Dict[str, List[Dict[str, str]]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Agentic Financial System with MongoDB",
    description="An AI system that processes bank statements and learns from user feedback.",
    version="11.1.0", # Updated with consistent return formats
    lifespan=lifespan
)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:59206"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

rag_pipeline = AgenticRAGPipeline()

# Include routers
app.include_router(auth_router)
app.include_router(investment_router)

# Test endpoint to verify CORS
@app.get("/test-cors")
async def test_cors():
    return {"message": "CORS is working!", "status": "ok"}

# SSE endpoint for streaming logs
@app.get("/stream-logs/{upload_id}")
async def stream_logs(upload_id: str):
    """
    Server-Sent Events endpoint for streaming processing logs to frontend.
    
    Usage:
        const eventSource = new EventSource(`/stream-logs/${uploadId}`);
        eventSource.onmessage = (event) => {
            const log = JSON.parse(event.data);
            console.log(log.message);
        };
    """
    
    async def event_generator():
        try:
            async for log_entry in log_streamer.get_logs(upload_id):
                # Skip ping messages
                if log_entry.get("level") == "ping":
                    yield f": keepalive\n\n"
                    continue
                
                # Send log as SSE event
                yield f"data: {json.dumps(log_entry)}\n\n"
                
                # Close stream if complete
                if log_entry.get("level") == "complete":
                    break
                    
        except Exception as e:
            logger.error(f"Error streaming logs for {upload_id}: {e}")
            error_log = {
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                "message": f"Stream error: {str(e)}",
                "level": "error"
            }
            yield f"data: {json.dumps(error_log)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

# ============================================
# BACKGROUND TASK FUNCTIONS
# ============================================


# ============================================
# SHARED HELPER FUNCTION FOR PROCESSING
# ============================================

async def process_single_statement_core(
    pdf_file: UploadFile,
    password: str,
    corrections_list: List[Dict],
    user_id: str = None,
    user_name: str = "User",
    streaming_id: str = None
) -> Dict[str, Any]:
    """
    Core logic for processing a single statement using the optimized SmartExtractor.
    """
    try:
        pdf_content = await pdf_file.read()
        
        # Initialize SMART extractor
        global smart_extractor
        if smart_extractor is None:
            smart_extractor = get_smart_extractor()
        
        # Invoke optimized Hot-Path extraction
        result = await smart_extractor.process_statement(
            pdf_content, 
            password, 
            pdf_file.filename,
            user_id=user_id,
            user_name=user_name,
            corrections=corrections_list,
            streaming_id=streaming_id
        )
        
        if not result.get("transactions"):
             return {
                "success": False,
                "filename": pdf_file.filename,
                "error": result.get("errors", ["No transactions extracted"])[0]
            }

        return {
            "success": True,
            "filename": pdf_file.filename,
            "upload_id": streaming_id,
            "transactions": result["transactions"],
            "insights": result["insights"],
            "processing_time": result.get("processing_time", 0)
        }
        
    except Exception as e:
        logger.error(f"Error processing {pdf_file.filename}: {str(e)}")
        return {
            "success": False,
            "filename": pdf_file.filename,
            "error": str(e)
        }
        
    except HTTPException as he:
        return {
            "success": False,
            "filename": pdf_file.filename,
            "upload_id": "",
            "transactions": [],
            "transactions_to_index": [],
            "error": he.detail
        }
    except Exception as e:
        logger.error(f"Error processing {pdf_file.filename}: {str(e)}")
        return {
            "success": False,
            "filename": pdf_file.filename,
            "upload_id": "",
            "transactions": [],
            "transactions_to_index": [],
            "error": str(e)
        }


# ============================================
# OPTIMIZED MULTI-STATEMENT ENDPOINT
# ============================================

@app.post("/process-multiple-statements/")
async def process_multiple_statements(
    passwords: str = Form(..., description="Comma-separated passwords (e.g., 'pass1,pass2,pass3')"),
    statement_pdfs: List[UploadFile] = File(...),
    upload_id: str = Form(None, description="Optional upload ID for log streaming"),
    current_user: models.User = Depends(auth_utils.get_current_user)  # Add authentication
):
    """
    Process multiple bank statements in parallel and return all transactions from database.
    
    Args:
        passwords: Comma-separated passwords matching the order of PDFs
        statement_pdfs: List of PDF files to process
    
    Returns:
        JSON list of all transactions stored in the database with complete details
    """
    password_list = [p.strip() for p in passwords.split(',')]
    statement_count = len(statement_pdfs)
    
    # Generate streaming_id if not provided (for log streaming)
    streaming_id = upload_id or str(uuid.uuid4())
    
    # Create log stream for real-time updates
    log_streamer.create_stream(streaming_id)
    
    await log_streamer.add_log(
        streaming_id,
        f"[START] Starting multi-statement processing ({statement_count} files)...",
        "info",
        0
    )
    
    logger.info(f"=" * 80)
    logger.info(f"[START] MULTI-STATEMENT PROCESSING STARTED")
    logger.info(f"=" * 80)
    logger.info(f" Number of PDFs received: {statement_count}")
    logger.info(f" Number of passwords received: {len(password_list)}")
    logger.info(f" Filenames: {[pdf.filename for pdf in statement_pdfs]}")
    logger.info(f"=" * 80)
    
    # Validation
    if len(password_list) != statement_count:
        raise HTTPException(
            status_code=400,
            detail=f"Expected {statement_count} passwords, but received {len(password_list)}. "
                   f"Format: 'password1,password2,password3'"
        )
    
    # Pre-fetch corrections once (shared across all statements)
    corrections = await models.Correction.find_all().to_list()
    corrections_list = [c.dict() for c in corrections]
    
    # Log each file being processed
    for i, pdf in enumerate(statement_pdfs):
        await log_streamer.add_log(
            streaming_id,
            f" Processing {pdf.filename}...",
            "info",
            10 + (i * 10)
        )
    
    tasks = [
        process_single_statement_core(
            pdf_file,
            password,
            corrections_list,
            user_id=str(current_user.user_id),
            user_name=current_user.full_name,
            streaming_id=f"{streaming_id}_{i}" # Sub-ID for background logs
        )
        for i, (pdf_file, password) in enumerate(zip(statement_pdfs, password_list))
    ]
    
    await log_streamer.add_log(streaming_id, "[FAST] Processing all statements in parallel...", "info", 40)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    all_transactions = []
    statement_results = []
    processed_count = 0
    failed_count = 0
    
    for result in results:
        if isinstance(result, Exception) or not result.get("success"):
            failed_count += 1
            error_msg = str(result) if isinstance(result, Exception) else result.get("error", "Unknown")
            statement_results.append({
                "filename": result.get("filename", "unknown") if isinstance(result, dict) else "unknown",
                "status": "failed",
                "error": error_msg
            })
            continue
        
        processed_count += 1
        all_transactions.extend(result["transactions"])
        statement_results.append({
            "filename": result["filename"],
            "upload_id": result["upload_id"],
            "transaction_count": len(result["transactions"]),
            "transactions": result["transactions"],
            "insights": result["insights"],
            "status": "success"
        })
    
    # ============================================
    # RETURN RESPONSE IMMEDIATELY
    # ============================================
    logger.info(f"[FAST] Returning response immediately. Background tasks running...")
    
    summary_msg = f"Processed {processed_count} successfully, {failed_count} failed."
    
    # Return comprehensive JSON response with transactions (from memory, not DB)
    return {
        "status": "success" if processed_count > 0 else "failed",
        "total_statements": statement_count,
        "processed_successfully": processed_count,
        "failed_statements": failed_count,
        "total_transactions": len(all_transactions),
        "message": summary_msg,
        "transactions": all_transactions,
        "background_tasks_running": True,
        "statement_details": [
            {
                "filename": stmt["filename"],
                "upload_id": stmt.get("upload_id", ""),
                "transaction_count": stmt.get("transaction_count", 0),
                "status": stmt["status"]
            }
            for stmt in statement_results
        ]
    }


# ============================================
# OPTIMIZED SINGLE STATEMENT ENDPOINT
# ============================================

@app.post("/process-statement/")
async def process_statement(
    password: str = Form(...),
    statement_pdf: UploadFile = File(...),
    upload_id: str = Form(None),  # Optional upload_id from frontend
    current_user: models.User = Depends(auth_utils.get_current_user)  # Require authentication
):
    """
    IMPROVED: Process a single bank statement with real-time logging.
    
    SECURITY FEATURES:
    - PDF password used ONLY for decryption (never stored or sent to LLM)
    - Sensitive data masked before LLM categorization
    - Transaction data encrypted before database storage
    
    New Workflow:
    1. PDF Extraction (password used here only)
    2. Smart AI Extraction  
    3. Transaction Structuring
    4. Categorization (with masked data)
    5. Financial Analysis (with aggregated data)
    6. Return Response IMMEDIATELY
    7. Background: Database Storage (encrypted) + Vector Indexing
    """
    logger.info("Starting /process-statement endpoint with improved workflow.")
    logger.info("SECURITY: Password will be used only for PDF decryption")
    
    # Security audit logging
    try:
        from .logging_config import log_password_usage
        log_password_usage("PDF decryption")
    except ImportError:
        pass  # Logging config not available
    
    # Use provided upload_id or generate new one for LOG STREAMING
    streaming_id = upload_id or str(uuid.uuid4())
    log_streamer.create_stream(streaming_id)
    await log_streamer.add_log(streaming_id, "Starting statement processing...", "info", 0)
    
    start_time = time.time()
    user_id_str = str(current_user.user_id) if hasattr(current_user, 'user_id') else str(current_user.id)
    
    try:
        # ============================================
        # UNIFIED HOT-PATH: Extraction -> Categorization -> Insights
        # ============================================
        # We leverage the same core logic used for multi-statement processing.
        # This function returns in ~35s and starts background persistence.
        result = await process_single_statement_core(
            statement_pdf,
            password,
            [], # corrections handled inside core if needed
            user_id=user_id_str,
            user_name=current_user.full_name,
            streaming_id=streaming_id
        )
        
        if not result.get("success"):
            await log_streamer.add_log(streaming_id, f"[FAIL] Processing failed: {result.get('error')}", "error", 100)
            return {
                "status": "failed",
                "upload_id": streaming_id,
                "message": result.get("error"),
                "transactions": [],
                "analysis": {"summary": {}, "category_wise_split": {}, "insights": []}
            }

        # Calculate processing time
        processing_time = time.time() - start_time
        
        await log_streamer.add_log(
            streaming_id,
            f"[OK] Success! {len(result['transactions'])} transactions processed in {processing_time:.1f}s",
            "success",
            100
        )

        return {
            "status": "success",
            "upload_id": streaming_id,
            "total_transactions": len(result["transactions"]),
            "message": f"Successfully processed {len(result['transactions'])} transactions.",
            "transactions": result["transactions"],
            "analysis": result["insights"],
            "metadata": {
                "processing_time_seconds": round(processing_time, 2),
                "analysis_status": "complete"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in /process-statement/: {str(e)}", exc_info=True)
        await log_streamer.add_log(streaming_id, f"[FAIL] System Error: {str(e)}", "error", 0)
        return {
            "status": "failed",
            "upload_id": streaming_id,
            "message": str(e),
            "transactions": [],
            "analysis": {"summary": {}, "category_wise_split": {}, "insights": []}
        }
        
    except Exception as e:
        logger.error(f"Error processing {statement_pdf.filename}: {str(e)}", exc_info=True)
        await log_streamer.add_log(
            streaming_id,
            f"[FAIL] Error: {str(e)}",
            "error",
            0
        )
        return {
            "status": "failed",
            "upload_id": streaming_id,
            "message": str(e),
            "transactions": [],
            "analysis": {"summary": {}, "category_wise_split": {}, "insights": []}
        }


# ============================================
# OTHER ENDPOINTS
# ============================================

@app.post("/chat")
async def chat_with_transactions(query: models.ChatQuery, current_user: models.User = Depends(auth_utils.get_current_user)):
    """
    Chat endpoint with optimized RAG pipeline and structured response formatting.
    Targets < 3 second response time.
    """
    import time
    start_time = time.time()
    
    # Enhanced logging for debugging
    logger.info("="*80)
    logger.info(f"📨 CHAT REQUEST from user: {current_user.email}")
    logger.info(f"📝 Query: {query.query}")
    logger.info(f"🔑 User ID: {current_user.user_id}")
    
    try:
        user_id = str(current_user.user_id)
        
        # 1. Determine history (Favor frontend-passed history, fallback to server-side)
        history = query.chat_history
        if history is None:
            history = SESSION_HISTORY.get(user_id, [])
        
        logger.info(f"📚 Chat history length: {len(history)} messages")

        # 2. Run Pipeline
        logger.info("🚀 Starting RAG pipeline...")
        result = await rag_pipeline.run(
            user_query=query.query,
            user_id=user_id,
            chat_history=history
        )
        logger.info("✅ RAG pipeline completed")

        processing_time = int((time.time() - start_time) * 1000)
        
        # New structured format
        answer = result.get("answer", "I couldn't generate a response.")
        metrics = result.get("metrics", [])
        insights = result.get("insights", [])
        transactions = result.get("transactions", [])
        
        logger.info(f"📊 Response stats:")
        logger.info(f"   - Answer length: {len(answer)} chars")
        logger.info(f"   - Metrics: {len(metrics)}")
        logger.info(f"   - Insights: {len(insights)}")
        logger.info(f"   - Transactions: {len(transactions)}")
        logger.info(f"   - Processing time: {processing_time}ms")

        # 3. Update server-side history (Store only text to minimize tokens)
        new_history = history + [
            {"role": "user", "content": query.query},
            {"role": "assistant", "content": answer}
        ]
        SESSION_HISTORY[user_id] = new_history[-15:]
        
        logger.info("✅ Chat request completed successfully")
        logger.info("="*80)

        return {
            "status": "success",
            "data": {
                "answer": answer,
                "metrics": metrics,
                "insights": insights,
                "transactions": transactions,
                "plan": result.get("plan"),
                "metrics_raw": result.get("metrics_raw"),
                "processing_time_ms": processing_time
            }
        }

    except Exception as e:
        processing_time = int((time.time() - start_time) * 1000)
        logger.error("="*80)
        logger.error(f"❌ ERROR in chat endpoint after {processing_time}ms")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full traceback:", exc_info=True)
        logger.error("="*80)
        
        return {
            "status": "error",
            "data": {
                "answer": f"An error occurred: {str(e)}",
                "type": "summary",
                "sections": [],
                "metrics": [],
                "insights": [],
                "processing_time_ms": processing_time,
            },
        }

@app.post("/correct-transaction/", response_model=models.Correction)
async def correct_transaction_category(
    correction_data: models.CorrectionCreate,
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    from .agent_categorization import CategorizationAgent
    
    # Normalize the keyword to a "Merchant Identity" (e.g., extract the name from UPI string)
    raw_keyword = correction_data.transaction_description_keyword
    identity = CategorizationAgent._extract_merchant_identity(raw_keyword)
    user_id = str(current_user.user_id)
    
    logger.info(f" CORRECTION: Normalizing '{raw_keyword[:30]}...' -> '{identity}'")
    
    # 1. Store Correction (Persistent Learning) - Use the IDENTITY as the primary key
    correction = await models.Correction.find_one(
        models.Correction.transaction_description_keyword == identity,
        models.Correction.user_id == user_id
    )
    
    if correction:
        correction.correct_category = correction_data.correct_category
    else:
        correction = models.Correction(
            transaction_description_keyword=identity,
            correct_category=correction_data.correct_category,
            user_id=user_id
        )
    await correction.save()
    
    # 2. Trigger Propagation Engine (Self-Learning)
    # This updates all past similar transactions in MongoDB for this user
    await CategorizationAgent.propagate_category(
        user_id=user_id,
        pattern=identity, # Use the clean identity for propagation
        correct_category=correction_data.correct_category
    )
    
    return correction

@app.get("/")
def root():
    return {"message": "Welcome to the Agentic Financial Analysis System!"}

@app.get("/statements/")
async def get_all_statements(current_user: models.User = Depends(auth_utils.get_current_user)):
    """
    Get all processed statements with metadata for the current user
    """
    try:
        # Get only uploads for this user
        uploads = await models.Upload.find(models.Upload.user_id == current_user.user_id).to_list()
        
        statements = []
        for upload in uploads:
            # Get transaction count for this upload
            transaction_count = await models.Transaction.find(
                models.Transaction.upload_id == str(upload.id)
            ).count()
            
            statements.append({
                "upload_id": str(upload.id),
                "filename": upload.filename,
                "bank_name": upload.bank_name,
                "extraction_method": upload.extraction_method,
                "processing_time_seconds": upload.processing_time_seconds,
                "total_transactions": transaction_count,
                "page_count": upload.page_count,
                "file_size_bytes": upload.file_size_bytes,
                "status": upload.status,
                "uploaded_at": upload.timestamp.isoformat(),
                "processed_at": upload.processed_at.isoformat() if upload.processed_at else None,
                "insights": upload.insights or [],
                "db_save_completed": upload.db_save_completed if hasattr(upload, 'db_save_completed') else True,
                "vector_index_completed": upload.vector_index_completed if hasattr(upload, 'vector_index_completed') else True
            })
        
        return {
            "status": "success",
            "total_statements": len(statements),
            "statements": statements
        }
    except Exception as e:
        logger.error(f"Error fetching statements: {e}")
        return {
            "status": "error",
            "message": str(e),
            "statements": []
        }

@app.get("/statement/{upload_id}")
async def get_statement_details(upload_id: str):
    """
    Get detailed information for a specific statement
    
    SECURITY: Decrypts transaction data before returning to authenticated user
    """
    try:
        # Get upload metadata
        upload = await models.Upload.get(upload_id)
        if not upload:
            raise HTTPException(status_code=404, detail="Statement not found")
        
        # Get all transactions for this upload
        transactions = await models.Transaction.find(
            models.Transaction.upload_id == upload_id
        ).to_list()
        
        # Initialize decryptor if encryption is enabled
        encryptor = None
        if settings.ENCRYPTION_KEY:
            try:
                encryptor = DataEncryptor(settings.ENCRYPTION_KEY, settings.ENCRYPTION_SALT)
                logger.debug("[UNLOCKED] Decryption enabled for transaction retrieval")
                
                # Security audit logging
                try:
                    from .logging_config import log_decryption_operation
                    log_decryption_operation(len(transactions), "", "get_statement_details")
                except ImportError:
                    pass  # Logging config not available
            except EncryptionError as e:
                logger.warning(f"[WARN]  Decryption initialization failed: {e}")
        
        # Convert to JSON format and decrypt if needed
        transactions_json = []
        for txn in transactions:
            # Get description (decrypt if encrypted field exists)
            description = txn.description
            if encryptor and hasattr(txn, 'description_encrypted') and txn.description_encrypted:
                try:
                    description = encryptor.decrypt(txn.description_encrypted)
                    logger.debug(f"[UNLOCKED] Decrypted transaction description")
                except EncryptionError as e:
                    logger.warning(f"[WARN]  Decryption failed: {e}")
                    description = "[Decryption Failed]"
            
            transactions_json.append({
                "id": str(txn.id),
                "date": txn.date.isoformat(),
                "description": description,
                "amount": float(txn.amount),
                "category": txn.category,
                "credit": float(txn.credit),
                "debit": float(txn.debit),
                "upload_id": txn.upload_id
            })
        
        return {
            "status": "success",
            "statement": {
                "upload_id": str(upload.id),
                "filename": upload.filename,
                "bank_name": upload.bank_name,
                "extraction_method": upload.extraction_method,
                "processing_time_seconds": upload.processing_time_seconds,
                "total_transactions": len(transactions_json),
                "page_count": upload.page_count,
                "file_size_bytes": upload.file_size_bytes,
                "status": upload.status,
                "uploaded_at": upload.timestamp.isoformat(),
                "processed_at": upload.processed_at.isoformat() if upload.processed_at else None
            },
            "transactions": transactions_json
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching statement details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/background-status/{upload_id}")
async def get_background_status(upload_id: str):
    """
    Check the status of background tasks for a specific upload.
    Frontend can poll this endpoint to know when background tasks complete.
    
    Returns:
        - db_save_completed: bool
        - vector_index_completed: bool
        - status: "processing" | "completed" | "failed"
    """
    try:
        upload = await models.Upload.get(upload_id)
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        return {
            "upload_id": upload_id,
            "db_save_completed": upload.db_save_completed,
            "vector_index_completed": upload.vector_index_completed,
            "status": upload.status,
            "all_tasks_completed": upload.db_save_completed and upload.vector_index_completed
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking background status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions/filtered")
async def get_filtered_transactions(
    categories: List[str] = Query(None),
    type: str = None,
    search: str = None,
    page: int = 1,
    limit: int = 20,
    upload_id: str = None,
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """
    Get filtered transactions with pagination support.
    
    Args:
        category: Filter by category (e.g., 'Food & Dining', 'Shopping')
        type: Filter by transaction type ('income' or 'expense')
        search: Search by transaction description (case-insensitive)
        page: Page number (default 1)
        limit: Items per page (default 20, max 100)
        upload_id: Filter by specific upload (optional)
        
    Returns:
        Paginated list of transactions matching filters
    """
    try:
        # Validate pagination parameters
        page = max(1, page)
        limit = min(100, max(1, limit))
        
        # Build MongoDB query
        query = {}
        
        # Filter by user's uploads
        user_uploads = await models.Upload.find(
            models.Upload.user_id == current_user.user_id
        ).to_list()
        user_upload_ids = [str(u.id) for u in user_uploads]
        
        if upload_id:
            if upload_id not in user_upload_ids:
                raise HTTPException(status_code=403, detail="Access denied to this upload")
            query["upload_id"] = upload_id
        else:
            query["upload_id"] = {"$in": user_upload_ids}
        
        # Filter by category (supports multiple)
        if categories:
            # Handle both single string and list of strings
            if isinstance(categories, str):
                values = [c.strip() for c in categories.split(",") if c.strip() and c.strip().lower() != 'all']
            else:
                values = [c for c in categories if c.lower() != 'all']
            
            if values:
                query["category"] = {"$in": values}
        
        # Filter by transaction type
        if type and type != "all":
            if type.lower() == "income":
                query["credit"] = {"$gt": 0}
            elif type.lower() == "expense":
                query["debit"] = {"$gt": 0}
        
        # Filter by search term
        if search and search.strip():
            query["description"] = {"$regex": search.strip(), "$options": "i"}
        
        # Execute query with pagination
        skip = (page - 1) * limit
        transactions = await models.Transaction.find(query).skip(skip).limit(limit).to_list()
        total = await models.Transaction.find(query).count()
        
        # Format response
        transactions_json = []
        for txn in transactions:
            transactions_json.append({
                "id": str(txn.id),
                "date": txn.date.isoformat(),
                "description": txn.description,
                "amount": float(txn.amount),
                "category": txn.category,
                "credit": float(txn.credit),
                "debit": float(txn.debit),
                "upload_id": txn.upload_id
            })
        
        total_pages = (total + limit - 1) // limit
        
        return {
            "status": "success",
            "data": {
                "transactions": transactions_json,
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching filtered transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/stats")
async def get_dashboard_stats(
    upload_id: str = None,
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """
    Get aggregated dashboard statistics for the user.
    
    Args:
        upload_id: Filter stats by specific upload (optional)
        
    Returns:
        Aggregated financial statistics
    """
    try:
        # Build MongoDB query
        query = {}
        
        # Filter by user's uploads
        user_uploads = await models.Upload.find(
            models.Upload.user_id == current_user.user_id
        ).to_list()
        user_upload_ids = [str(u.id) for u in user_uploads]
        
        if upload_id:
            if upload_id not in user_upload_ids:
                raise HTTPException(status_code=403, detail="Access denied to this upload")
            query["upload_id"] = upload_id
        else:
            query["upload_id"] = {"$in": user_upload_ids}
        
        # Get all transactions matching query
        transactions = await models.Transaction.find(query).to_list()
        
        # Calculate statistics
        total_transactions = len(transactions)
        total_income = sum(float(t.credit) for t in transactions)
        total_expenses = sum(float(t.debit) for t in transactions)
        balance = total_income - total_expenses
        
        average_transaction = (total_income + total_expenses) / total_transactions if total_transactions > 0 else 0
        
        largest_expense = max((float(t.debit) for t in transactions), default=0)
        largest_income = max((float(t.credit) for t in transactions), default=0)
        
        # Get latest AI insights from the most recent upload
        latest_upload = await models.Upload.find(
            models.Upload.user_id == current_user.user_id
        ).sort("-timestamp").first_or_none()
        ai_insights = latest_upload.insights if latest_upload and latest_upload.insights else []
        
        return {
            "status": "success",
            "data": {
                "total_transactions": total_transactions,
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "balance": round(balance, 2),
                "average_transaction": round(average_transaction, 2),
                "largest_expense": round(largest_expense, 2),
                "largest_income": round(largest_income, 2),
                "ai_insights": ai_insights
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/by-category")
async def get_analytics_by_category(
    upload_id: str = None,
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """
    Get analytics data grouped by category.
    
    Args:
        upload_id: Filter analytics by specific upload (optional)
        
    Returns:
        Category breakdown with totals and percentages
    """
    try:
        # Build MongoDB query
        query = {}
        
        # Filter by user's uploads
        user_uploads = await models.Upload.find(
            models.Upload.user_id == current_user.user_id
        ).to_list()
        user_upload_ids = [str(u.id) for u in user_uploads]
        
        if upload_id:
            if upload_id not in user_upload_ids:
                raise HTTPException(status_code=403, detail="Access denied to this upload")
            query["upload_id"] = upload_id
        else:
            query["upload_id"] = {"$in": user_upload_ids}
        
        # Get all transactions matching query
        transactions = await models.Transaction.find(query).to_list()
        
        # Group by category
        category_data = {}
        total_expenses = 0
        
        for txn in transactions:
            category = txn.category or "Uncategorized"
            amount = float(txn.debit) if float(txn.debit) > 0 else float(txn.credit)
            
            if category not in category_data:
                category_data[category] = {
                    "total": 0,
                    "count": 0
                }
            
            category_data[category]["total"] += amount
            category_data[category]["count"] += 1
            total_expenses += amount
        
        # Calculate percentages and format response
        categories = []
        for category, data in sorted(category_data.items(), key=lambda x: x[1]["total"], reverse=True):
            percentage = (data["total"] / total_expenses * 100) if total_expenses > 0 else 0
            categories.append({
                "name": category,
                "total": round(data["total"], 2),
                "count": data["count"],
                "percentage": round(percentage, 2)
            })
        
        return {
            "status": "success",
            "data": {
                "categories": categories,
                "total_expenses": round(total_expenses, 2)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analytics by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/by-date")
async def get_analytics_by_date(
    period: str = "daily",
    upload_id: str = None,
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """
    Get analytics data grouped by date/time period.
    
    Args:
        period: Time period grouping ('daily', 'weekly', 'monthly')
        upload_id: Filter analytics by specific upload (optional)
        
    Returns:
        Time-series analytics with income, expenses, and balance
    """
    try:
        # Build MongoDB query
        query = {}
        
        # Filter by user's uploads
        user_uploads = await models.Upload.find(
            models.Upload.user_id == current_user.user_id
        ).to_list()
        user_upload_ids = [str(u.id) for u in user_uploads]
        
        if upload_id:
            if upload_id not in user_upload_ids:
                raise HTTPException(status_code=403, detail="Access denied to this upload")
            query["upload_id"] = upload_id
        else:
            query["upload_id"] = {"$in": user_upload_ids}
        
        # Get all transactions matching query
        transactions = await models.Transaction.find(query).to_list()
        
        # Group by date/period
        period_data = {}
        
        for txn in transactions:
            # Determine period key based on period parameter
            if period == "daily":
                period_key = txn.date.strftime("%Y-%m-%d")
            elif period == "weekly":
                # ISO week format
                period_key = txn.date.strftime("%Y-W%V")
            elif period == "monthly":
                period_key = txn.date.strftime("%Y-%m")
            else:
                period_key = txn.date.strftime("%Y-%m-%d")
            
            if period_key not in period_data:
                period_data[period_key] = {
                    "income": 0,
                    "expenses": 0
                }
            
            period_data[period_key]["income"] += float(txn.credit)
            period_data[period_key]["expenses"] += float(txn.debit)
        
        # Format response
        periods = []
        for period_key in sorted(period_data.keys()):
            data = period_data[period_key]
            balance = data["income"] - data["expenses"]
            periods.append({
                "date": period_key,
                "income": round(data["income"], 2),
                "expenses": round(data["expenses"], 2),
                "balance": round(balance, 2)
            })
        
        return {
            "status": "success",
            "data": {
                "periods": periods,
                "period_type": period
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analytics by date: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/transactions/{transaction_id}/category")
async def update_transaction_category(
    transaction_id: str,
    category_update: dict,
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """
    Update the category of a transaction and sync to both MongoDB and Pinecone.
    
    Args:
        transaction_id: The transaction ID to update
        category_update: Dict with 'new_category' key
        current_user: Current authenticated user
        
    Returns:
        Updated transaction data
    """
    try:
        # Extract new category from request
        new_category = category_update.get('new_category')
        if not new_category:
            raise HTTPException(status_code=400, detail="new_category is required")
        
        # Define allowed categories
        allowed_categories = [
            'Food & Dining', 'Transportation', 'Shopping', 'Entertainment', 
            'Bills & Utilities', 'Healthcare', 'Education', 'Travel', 
            'Investment', 'Dividend', 'Salary', 'Transfer', 
            'Personal Transfer', 'Other Transfers', 'Other'
        ]
        
        # Validate category
        if new_category not in allowed_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Allowed categories: {', '.join(allowed_categories)}"
            )
        
        # Get transaction from MongoDB
        transaction = await models.Transaction.get(transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Verify user owns this transaction (via upload_id)
        upload = await models.Upload.get(transaction.upload_id)
        if not upload or upload.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Access denied to this transaction")
        
        # Store old category for logging
        old_category = transaction.category
        
        # Update transaction in MongoDB
        transaction.category = new_category
        await transaction.save()
        
        logger.info(f"[OK] Updated transaction {transaction_id} category from {old_category} to {new_category}")
        
        # Update vector embedding in Pinecone
        try:
            # Regenerate embedding with new category
            transaction_text = f"{transaction.date} {transaction.description} {new_category} {transaction.amount}"
            
            # Delete old vector
            await rag_pipeline.delete_transaction_vector(transaction_id)
            
            # Create new vector with updated category
            embedding = await rag_pipeline.generate_embedding(transaction_text)
            await rag_pipeline.upsert_transaction_vector(
                transaction_id=transaction_id,
                embedding=embedding,
                metadata={
                    'date': transaction.date.isoformat(),
                    'description': transaction.description,
                    'category': new_category,
                    'amount': float(transaction.amount),
                    'upload_id': transaction.upload_id
                }
            )
            
            logger.info(f"[OK] Updated Pinecone vector for transaction {transaction_id}")
        except Exception as e:
            logger.error(f"[WARN]  Failed to update Pinecone vector: {e}")
            # Continue even if Pinecone update fails
        
        # Return updated transaction
        return {
            "status": "success",
            "data": {
                "transaction_id": str(transaction.id),
                "old_category": old_category,
                "new_category": new_category,
                "date": transaction.date.isoformat(),
                "description": transaction.description,
                "amount": float(transaction.amount),
                "updated_at": datetime.datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transaction category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update category: {str(e)}")


@app.delete("/statement/{upload_id}")
async def delete_statement(upload_id: str):
    """
    Delete a statement and all its associated data from MongoDB and Pinecone
    
    Args:
        upload_id: The upload ID to delete
        
    Returns:
        Success message with deletion details
    """
    try:
        logger.info(f"Starting deletion for upload_id: {upload_id}")
        
        # Step 1: Get upload metadata
        upload = await models.Upload.get(upload_id)
        if not upload:
            raise HTTPException(status_code=404, detail="Statement not found")
        
        filename = upload.filename
        
        # Step 2: Count transactions before deletion
        transaction_count = await models.Transaction.find(
            models.Transaction.upload_id == upload_id
        ).count()
        
        logger.info(f"Found {transaction_count} transactions to delete for {filename}")
        
        # Step 3: Delete from Pinecone vector DB
        try:
            await rag_pipeline.delete_transactions_by_upload_id(upload_id)
            logger.info(f"[OK] Deleted vectors from Pinecone for upload_id: {upload_id}")
        except Exception as e:
            logger.error(f"[WARN]  Failed to delete from Pinecone: {e}")
            # Continue with MongoDB deletion even if Pinecone fails
        
        # Step 4: Delete transactions from MongoDB
        delete_result = await models.Transaction.find(
            models.Transaction.upload_id == upload_id
        ).delete()
        
        logger.info(f"[OK] Deleted {delete_result.deleted_count} transactions from MongoDB")
        
        # Step 5: Delete upload record from MongoDB
        await upload.delete()
        logger.info(f"[OK] Deleted upload record from MongoDB")
        
        return {
            "status": "success",
            "message": f"Successfully deleted statement '{filename}' and all associated data",
            "deleted": {
                "upload_id": upload_id,
                "filename": filename,
                "transactions_count": transaction_count,
                "mongodb_deleted": True,
                "pinecone_deleted": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting statement {upload_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete statement: {str(e)}")
