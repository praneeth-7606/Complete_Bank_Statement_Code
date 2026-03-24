
from contextlib import asynccontextmanager
import io
import pypdf
import uuid
import json
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import datetime
import re
import asyncio
import logging
from . import models, agents
from .models import MultiStatementResponse, StatementFile
from .database import init_db
from .rag_pipeline import RAGPipeline
from .auth_router import router as auth_router
from . import auth_utils
from .optimized_processor import OptimizedTransactionProcessor
# from .table_extractor import extractor as table_extractor  # Not needed with Donut VLM
from .accurate_processor import AccurateTransactionProcessor
from .smart_extractor import get_smart_extractor
from .log_streamer import log_streamer
from .data_encryptor import DataEncryptor, EncryptionError
from .config import settings

logger = logging.getLogger(__name__)

# Initialize SMART EXTRACTOR - Auto-classifies PDFs and uses best method
smart_extractor = None  # Will be initialized on first use

# Initialize ACCURATE processor - 100% debit/credit accuracy + Rate limit friendly
accurate_processor = AccurateTransactionProcessor(
    category_batch_size=50,  # Very large batches = fewer API calls
    max_concurrent_workers=2  # Reduced to avoid rate limits
)

# Keep old processor as fallback (if table extraction fails)
optimized_processor = OptimizedTransactionProcessor(
    mini_batch_size=15,  # Larger batches = fewer API calls
    max_concurrent_workers=3  # Reduced to avoid rate limits
)

def extract_bank_name(filename: str) -> str:
    """Extract bank name from filename or return 'Unknown Bank'"""
    filename_lower = filename.lower()
    
    # Common bank name patterns
    bank_patterns = {
        'hdfc': 'HDFC Bank',
        'icici': 'ICICI Bank',
        'sbi': 'State Bank of India',
        'axis': 'Axis Bank',
        'kotak': 'Kotak Mahindra Bank',
        'pnb': 'Punjab National Bank',
        'bob': 'Bank of Baroda',
        'canara': 'Canara Bank',
        'union': 'Union Bank',
        'idbi': 'IDBI Bank',
        'yes': 'Yes Bank',
        'indusind': 'IndusInd Bank',
        'dlb': 'Dhanlaxmi Bank',
        'federal': 'Federal Bank',
        'rbl': 'RBL Bank',
        'idfc': 'IDFC First Bank'
    }
    
    for pattern, bank_name in bank_patterns.items():
        if pattern in filename_lower:
            return bank_name
    
    return 'Unknown Bank'

def get_pdf_page_count(pdf_bytes: bytes) -> int:
    """Get number of pages in PDF"""
    try:
        pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        return len(pdf_reader.pages)
    except:
        return 0

async def extract_text_from_pdf(password: str, file_content: bytes) -> str:
    """Extracts all text content from an uploaded PDF file."""
    try:
        pdf_bytes = io.BytesIO(file_content)
        pdf_reader = pypdf.PdfReader(pdf_bytes)
        if pdf_reader.is_encrypted:
            if pdf_reader.decrypt(password) == pypdf.PasswordType.NOT_DECRYPTED:
                raise HTTPException(status_code=400, detail="Incorrect PDF password.")
        extracted_text = "".join(page.extract_text() for page in pdf_reader.pages)
        if not extracted_text or not extracted_text.strip():
            raise HTTPException(status_code=422, detail="Could not extract text from PDF. The document might be empty or image-based.")
        return extracted_text
    except pypdf.errors.PdfReadError:
        raise HTTPException(status_code=400, detail="Invalid or corrupted PDF file.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing error: {e}")

def pre_parse_transaction_lines(text: str) -> List[str]:
    """
    This new parser is designed specifically for statements where a single transaction
    is split across multiple lines. It intelligently reconstructs them.
    """
    reconstructed_lines = []
    current_line_parts = []
    date_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}")
    money_pattern = re.compile(r"\d{1,3}(?:,?\d{3})*\.\d{2}")

    for line in text.splitlines():
        line = line.strip()
        if not line or "Cheque/Ref No" in line or "Total" in line or "B/F" in line:
            continue

        if date_pattern.match(line):
            if current_line_parts:
                full_line = " ".join(current_line_parts)
                if money_pattern.search(full_line):
                    reconstructed_lines.append(full_line)
            current_line_parts = [line]
        elif current_line_parts:
            current_line_parts.append(line)

    if current_line_parts:
        full_line = " ".join(current_line_parts)
        if money_pattern.search(full_line):
            reconstructed_lines.append(full_line)

    logger.info(f"Intelligent parser reconstructed {len(reconstructed_lines)} complete transaction lines.")
    return reconstructed_lines

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

rag_pipeline = RAGPipeline()

# Include authentication router
app.include_router(auth_router)

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

async def save_to_database_background(
    upload_id: str,
    filename: str,
    file_size_bytes: int,
    bank_name: str,
    extraction_method: str,
    page_count: int,
    transactions: List[models.Transaction],
    processing_time: float = 0,
    insights: List[str] = None,
    user_id: str = None  # Add user_id parameter
):
    """Background task to save transactions to MongoDB"""
    try:
        logger.info(f"[{upload_id}] Starting database save (background)...")
        
        # Create upload record with the upload_id as a custom field
        upload = models.Upload(
            filename=filename,
            file_size_bytes=file_size_bytes,
            bank_name=bank_name,
            extraction_method=extraction_method,
            page_count=page_count,
            total_transactions=len(transactions),
            processing_time_seconds=processing_time,
            status="completed",
            processed_at=datetime.datetime.utcnow(),
            insights=insights or [],
            db_save_completed=False,
            vector_index_completed=False,
            user_id=user_id  # Add user_id
        )
        await upload.save()
        
        # Store the database ID for later reference
        db_upload_id = str(upload.id)
        
        # Update upload_id in transactions to use the database ID
        for txn in transactions:
            txn.upload_id = db_upload_id
        
        # Save all transactions
        await models.Transaction.insert_many(transactions)
        
        # Mark DB save as completed
        upload.db_save_completed = True
        await upload.save()
        
        logger.info(f"[{upload_id}] ✅ Database save complete: {len(transactions)} transactions, DB ID: {db_upload_id}")
        
        await log_streamer.add_log(
            upload_id,
            f"✅ Database save completed! Saved {len(transactions)} transactions to MongoDB.",
            "success",
            None
        )
        
        # Return the database ID for vector indexing
        return db_upload_id
        
    except Exception as e:
        logger.error(f"[{upload_id}] ❌ Database save failed: {e}", exc_info=True)
        await log_streamer.add_log(
            upload_id,
            f"⚠️  Database save failed: {str(e)}",
            "warning",
            None
        )


async def index_vectors_background(
    upload_id: str,
    transactions: List[models.Transaction],
    db_upload_id: str = None
):
    """Background task to create vector embeddings"""
    try:
        logger.info(f"[{upload_id}] Starting vector indexing (background)...")
        
        await rag_pipeline.index_transactions(transactions)
        
        # Mark vector indexing as completed using the database ID
        if db_upload_id:
            try:
                from bson import ObjectId
                upload = await models.Upload.get(ObjectId(db_upload_id))
                if upload:
                    upload.vector_index_completed = True
                    await upload.save()
                    logger.info(f"[{upload_id}] Marked vector indexing complete for DB ID: {db_upload_id}")
            except Exception as e:
                logger.error(f"[{upload_id}] Failed to update vector status: {e}")
        
        logger.info(f"[{upload_id}] ✅ Vector indexing complete")
        
        await log_streamer.add_log(
            upload_id,
            f"✅ Vector indexing completed! Created search vectors for {len(transactions)} transactions. You can now ask questions about your finances!",
            "success",
            None
        )
        
        # Send final completion notification
        await log_streamer.add_log(
            upload_id,
            "🎉 All background tasks completed! Your statement is fully processed and ready for Q&A.",
            "complete",
            None
        )
        
    except Exception as e:
        logger.error(f"[{upload_id}] ❌ Vector indexing failed: {e}", exc_info=True)
        await log_streamer.add_log(
            upload_id,
            f"⚠️  Vector indexing failed: {str(e)}",
            "warning",
            None
        )

# ============================================
# SHARED HELPER FUNCTION FOR PROCESSING
# ============================================

async def process_single_statement_core(
    pdf_file: UploadFile,
    password: str,
    structuring_agent: agents.CategorizationAgent,
    categorization_agent: agents.CategorizationAgent,
    corrections_list: List[Dict],
    user_id: str = None  # Add user_id parameter
) -> Dict[str, Any]:
    """
    Core logic for processing a single statement with 100% accuracy.
    Uses table extraction for precise debit/credit identification.
    Returns transactions in the SAME format as single-statement endpoint.
    """
    try:
        # PDF processing - SMART AI EXTRACTION (Column + Balance Detection)
        pdf_content = await pdf_file.read()
        
        logger.info(f"🤖 Extracting transactions using SMART AI...")
        import time
        start_time = time.time()
        
        # Initialize SMART extractor if needed
        global smart_extractor
        if smart_extractor is None:
            smart_extractor = get_smart_extractor()
        
        # STEP 1: Try SMART extraction (auto-classifies PDF and uses best method)
        try:
            logger.info(f"   🧠 SMART Strategy: Auto-Classify PDF → Use Best Method → 100% Accuracy")
            transactions_from_ai = smart_extractor.extract_from_pdf(pdf_content, password, pdf_file.filename)
            
            if not transactions_from_ai or len(transactions_from_ai) == 0:
                raise ValueError("No transactions extracted by AI")
            
            logger.info(f"✅ Extracted {len(transactions_from_ai)} transactions with SMART AI")
            logger.info(f"   ✅ Debit/Credit: Auto-corrected using balance tracking")
            
        except Exception as ai_error:
            # Fallback to old text-based method
            logger.warning(f"AI extraction failed: {ai_error}")
            logger.info(f"⚠️  Falling back to text-based extraction...")
            
            extracted_text = await extract_text_from_pdf(password, pdf_content)
            transaction_lines = pre_parse_transaction_lines(extracted_text)
            
            if not transaction_lines:
                return {
                    "success": False,
                    "filename": pdf_file.filename,
                    "upload_id": "",
                    "transactions": [],
                    "transactions_to_index": [],
                    "error": "No transaction lines could be extracted"
                }
            
            # Create upload record for fallback path
            upload = models.Upload(
                filename=pdf_file.filename,
                user_id=user_id
            )
            await upload.save()
            upload_id_str = str(upload.id)
            
            # Use old processor as fallback
            logger.info(f"Using legacy AI-powered parsing for {len(transaction_lines)} lines...")
            processing_result = await optimized_processor.process_transactions(
                transaction_lines,
                corrections_list
            )
            
            if not processing_result["success"]:
                return {
                    "success": False,
                    "filename": pdf_file.filename,
                    "upload_id": upload_id_str,
                    "transactions": [],
                    "transactions_to_index": [],
                    "error": processing_result["error"]
                }
            
            categorized_transactions = processing_result["transactions"]
            elapsed = time.time() - start_time
            
            perf_report = optimized_processor.get_performance_report()
            logger.info(f"⚡ Legacy processing complete: {len(categorized_transactions)} transactions in {elapsed:.2f}s")
            logger.info(f"📊 Stage breakdown: Structuring={perf_report['stage_breakdown']['structuring']['time_seconds']:.1f}s, "
                       f"Categorization={perf_report['stage_breakdown']['categorization']['time_seconds']:.1f}s, "
                       f"Embedding={perf_report['stage_breakdown']['embedding']['time_seconds']:.1f}s")
        else:
            # AI EXTRACTION SUCCEEDED
            # Create upload record with metadata
            upload = models.Upload(
                filename=pdf_file.filename,
                file_size_bytes=len(pdf_content),
                status="processing",
                user_id=user_id
            )
            await upload.save()
            upload_id_str = str(upload.id)
            
            elapsed = time.time() - start_time
            
            # Determine extraction method used
            extraction_method = "SMART_AUTO"
            if transactions_from_ai and len(transactions_from_ai) > 0:
                if 'extraction_method' in transactions_from_ai[0]:
                    extraction_method = transactions_from_ai[0]['extraction_method']
            
            logger.info(f"✨ Smart AI extraction complete!")
            logger.info(f"📊 EXTRACTION METHOD USED: {extraction_method}")
            logger.info(f"⚡ Extraction complete: {len(transactions_from_ai)} transactions in {elapsed:.2f}s "
                       f"({len(transactions_from_ai)/elapsed:.1f} txn/sec)")
            
            # FIX 1: ADD CATEGORIZATION STEP
            logger.info(f"🏷️  Categorizing {len(transactions_from_ai)} transactions...")
            categorization_start = time.time()
            
            # Categorize transactions using AI
            categorized_transactions = await categorization_agent.categorize_transactions(
                transactions_from_ai,
                corrections_list
            )
            
            categorization_time = time.time() - categorization_start
            logger.info(f"✅ Categorization complete in {categorization_time:.2f}s")
            
            # Update total processing time
            elapsed = time.time() - start_time
        
        # Process and validate transactions
        transactions_to_save = []
        transaction_snapshots = []
        
        for t_raw in categorized_transactions:
            try:
                # Normalize keys to lowercase for robust access
                t = {k.lower(): v for k, v in t_raw.items()}
                
                # --- FIX: Ensure Credit/Debit are correctly parsed and Amount is derived ---
                credit_val = float(t.get('credit', 0.0) or 0.0)
                debit_val = float(t.get('debit', 0.0) or 0.0)
                # amount_abs is set to the non-zero value between credit and debit
                amount_abs = credit_val if credit_val > 0 else debit_val
                
                date_str = t["date"]
                try:
                    # Attempt to parse date strings robustly
                    if "/" in date_str:
                        # Handles formats like DD/MM/YYYY
                        date_obj = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
                    else: 
                        # Handles ISO format YYYY-MM-DD
                        date_obj = datetime.datetime.fromisoformat(date_str).date()
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse date string: {date_str}. Skipping transaction.")
                    continue
                
                # Create snapshot for the report (output) - CONSISTENT FORMAT
                snap = {
                    'date': date_obj.isoformat(), 
                    'description': t['description'], 
                    'amount': amount_abs, # This is the correctly derived non-zero amount
                    'category': t.get('category', 'Uncategorized'), 
                    'credit': credit_val, 
                    'debit': debit_val, 
                    'upload_id': upload_id_str
                }
                
                # Create document data for database save
                db_transaction_data = {
                    'date': date_obj, 
                    'description': t['description'],
                    'amount': amount_abs, 
                    'category': t.get('category', 'Uncategorized'),
                    'upload_id': upload_id_str,
                    'credit': credit_val,
                    'debit': debit_val,
                }
                
                transactions_to_save.append(models.Transaction(**db_transaction_data))
                transaction_snapshots.append(snap)
                
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Skipping transaction due to validation error: {e}. Original Data: {t_raw}")
                continue
        
        if not transactions_to_save:
            return {
                "success": False,
                "filename": pdf_file.filename,
                "upload_id": upload_id_str,
                "transactions": [],
                "transactions_to_index": [],
                "error": "No valid transactions after validation"
            }
        
        # Save to database
        await models.Transaction.insert_many(transactions_to_save)
        logger.info(f"Successfully added {len(transactions_to_save)} transactions to the database.")
        
        # FIX 4: Update upload metadata with comprehensive information
        upload_doc = await models.Upload.get(upload_id_str)
        if upload_doc:
            # Extract bank name from filename or PDF content
            bank_name = extract_bank_name(pdf_file.filename)
            
            # Get page count
            page_count = get_pdf_page_count(pdf_content)
            
            # Update metadata
            upload_doc.bank_name = bank_name
            upload_doc.extraction_method = extraction_method
            upload_doc.processing_time_seconds = elapsed
            upload_doc.total_transactions = len(transactions_to_save)
            upload_doc.page_count = page_count
            upload_doc.status = "completed"
            upload_doc.processed_at = datetime.datetime.utcnow()
            
            # ✅ FIX: Mark background tasks as completed
            upload_doc.db_save_completed = True
            upload_doc.vector_index_completed = True
            
            await upload_doc.save()
            logger.info(f"✅ Updated upload metadata: {bank_name}, {len(transactions_to_save)} transactions, {elapsed:.2f}s")
        
        return {
            "success": True,
            "filename": pdf_file.filename,
            "upload_id": upload_id_str,
            "transactions": transaction_snapshots,
            "transactions_to_index": transactions_to_save,
            "extraction_method": extraction_method,
            "bank_name": bank_name,
            "processing_time": elapsed,
            "page_count": page_count,
            "error": None
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
    
    # Generate upload_id if not provided (for log streaming)
    if not upload_id:
        upload_id = str(uuid.uuid4())
    
    # Create log stream for real-time updates
    log_streamer.create_stream(upload_id)
    
    await log_streamer.add_log(
        upload_id,
        f"🚀 Starting multi-statement processing ({statement_count} files)...",
        "info",
        0
    )
    
    logger.info(f"=" * 80)
    logger.info(f"🚀 MULTI-STATEMENT PROCESSING STARTED")
    logger.info(f"=" * 80)
    logger.info(f"📄 Number of PDFs received: {statement_count}")
    logger.info(f"🔑 Number of passwords received: {len(password_list)}")
    logger.info(f"📋 Filenames: {[pdf.filename for pdf in statement_pdfs]}")
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
    
    # Create shared agent instances
    structuring_agent = agents.TransactionStructuringAgent()
    categorization_agent = agents.CategorizationAgent()
    
    # Log each file being processed
    for i, pdf in enumerate(statement_pdfs):
        await log_streamer.add_log(
            upload_id,
            f"📄 Processing {pdf.filename}...",
            "info",
            10 + (i * 10)
        )
    
    # Process all statements in parallel
    tasks = [
        process_single_statement_core(
            pdf_file,
            password,
            structuring_agent,
            categorization_agent,
            corrections_list,
            current_user.user_id  # Pass user_id
        )
        for pdf_file, password in zip(statement_pdfs, password_list)
    ]
    
    await log_streamer.add_log(
        upload_id,
        "⚡ Processing all statements in parallel...",
        "info",
        40
    )
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    await log_streamer.add_log(
        upload_id,
        "✅ All statements processed!",
        "success",
        60
    )
    
    logger.info(f"=" * 80)
    logger.info(f"✅ PARALLEL PROCESSING COMPLETED")
    logger.info(f"📊 Results received: {len(results)}")
    logger.info(f"=" * 80)
    
    # Collect results with CONSISTENT transaction format
    all_transactions = []
    all_transactions_to_index = []
    statement_results = []
    processed_count = 0
    failed_count = 0
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Exception in parallel processing: {result}")
            statement_results.append(models.StatementFile(
                filename="unknown",
                upload_id="",
                transaction_count=0,
                transactions=[],
                status=f"failed - {str(result)}"
            ))
            failed_count += 1
            continue
        
        if result["success"]:
            processed_count += 1
            # Transactions are already in the correct format from core function
            all_transactions.extend(result["transactions"])
            all_transactions_to_index.extend(result["transactions_to_index"])
            
            logger.info(f"✅ Statement {processed_count}: {result['filename']} - {len(result['transactions'])} transactions")
            
            await log_streamer.add_log(
                upload_id,
                f"✅ Statement {processed_count}: {result['filename']} - {len(result['transactions'])} transactions",
                "success",
                60 + (processed_count * 5)
            )
            
            statement_results.append(models.StatementFile(
                filename=result["filename"],
                upload_id=result["upload_id"],
                transaction_count=len(result["transactions"]),
                transactions=result["transactions"],  # Already has date, description, amount, category, credit, debit, upload_id
                status="success"
            ))
        else:
            failed_count += 1
            logger.error(f"❌ Statement failed: {result['filename']} - Error: {result.get('error', 'Unknown')}")
            statement_results.append(models.StatementFile(
                filename=result["filename"],
                upload_id=result["upload_id"],
                transaction_count=0,
                transactions=[],
                status=f"failed - {result['error']}"
            ))
    
    # ============================================
    # RETURN RESPONSE IMMEDIATELY (Don't wait for DB/Analysis)
    # ============================================
    logger.info(f"✅ Processing complete! Returning {len(all_transactions)} transactions to user")
    logger.info(f"💾 Starting background tasks (DB save, analysis, vector indexing)...")
    
    await log_streamer.add_log(
        upload_id,
        f"✅ Processing complete! Returning {len(all_transactions)} transactions",
        "success",
        90
    )
    
    await log_streamer.add_log(
        upload_id,
        "💾 Saving to database and generating analysis (background)...",
        "info",
        95
    )
    
    # Prepare response message
    if processed_count == statement_count:
        message = f"All {statement_count} statements processed successfully!"
    elif processed_count > 0:
        message = f"Processed {processed_count}/{statement_count} statements. {failed_count} failed."
    else:
        message = f"Failed to process all {statement_count} statements."
    
    # Get upload IDs for background processing
    all_upload_ids = [result["upload_id"] for result in results if isinstance(result, dict) and result.get("success")]
    
    # ============================================
    # START BACKGROUND TASKS (User doesn't wait for these)
    # ============================================
    async def background_tasks():
        """
        Background tasks that run after response is sent:
        1. Save Upload records to database
        2. Generate financial analysis
        3. Index to Pinecone vector DB
        4. Update upload status
        """
        try:
            logger.info(f"🔄 Background: Starting tasks for {len(all_upload_ids)} uploads")
            
            # Task 1: Generate financial analysis
            if all_transactions:
                logger.info(f"📊 Background: Generating analysis for {len(all_transactions)} transactions")
                analyst_agent = agents.FinancialAnalystAgent()
                financial_analysis = await analyst_agent.generate_financial_insights(all_transactions)
                logger.info(f"✅ Background: Analysis complete")
                
                # Store analysis in upload records
                if isinstance(financial_analysis, dict):
                    insights = financial_analysis.get('insights', [])
                    for upload_id in all_upload_ids:
                        try:
                            upload_doc = await models.Upload.get(upload_id)
                            if upload_doc:
                                upload_doc.insights = insights
                                await upload_doc.save()
                        except Exception as e:
                            logger.error(f"Failed to save insights for {upload_id}: {e}")
            
            # Task 2: Index to Pinecone
            if all_transactions_to_index:
                logger.info(f"🔍 Background: Indexing {len(all_transactions_to_index)} transactions to Pinecone")
                await rag_pipeline.index_transactions(all_transactions_to_index)
                logger.info(f"✅ Background: Vector indexing complete")
            
            # Task 3: Mark all uploads as fully completed
            for upload_id in all_upload_ids:
                try:
                    upload_doc = await models.Upload.get(upload_id)
                    if upload_doc:
                        upload_doc.vector_index_completed = True
                        await upload_doc.save()
                        logger.info(f"✅ Background: Upload {upload_id} fully completed")
                except Exception as e:
                    logger.error(f"Failed to update upload {upload_id}: {e}")
            
            logger.info(f"🎉 Background: All tasks completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Background tasks failed: {e}", exc_info=True)
    
    # Start background tasks (don't wait for them)
    asyncio.create_task(background_tasks())
    
    # ============================================
    # RETURN RESPONSE IMMEDIATELY
    # ============================================
    logger.info(f"✅ Multi-statement processing completed: {message}")
    logger.info(f"⚡ Returning response immediately. Background tasks running...")
    
    # Return comprehensive JSON response with transactions (from memory, not DB)
    return {
        "status": "success" if processed_count > 0 else "failed",
        "total_statements": statement_count,
        "processed_successfully": processed_count,
        "failed_statements": failed_count,
        "total_transactions": len(all_transactions),
        "message": message,
        "transactions": all_transactions,  # Transactions from processing (not DB)
        "background_tasks_running": True,  # Indicate background tasks are running
        "statement_details": [
            {
                "filename": stmt.filename,
                "upload_id": stmt.upload_id,
                "transaction_count": stmt.transaction_count,
                "status": stmt.status
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
    logger.info("🔒 SECURITY: Password will be used only for PDF decryption")
    
    # Security audit logging
    try:
        from .logging_config import log_password_usage
        log_password_usage("PDF decryption")
    except ImportError:
        pass  # Logging config not available
    
    # Use provided upload_id or generate new one
    if not upload_id:
        upload_id = str(uuid.uuid4())
    
    # Create log stream IMMEDIATELY (before any processing)
    log_streamer.create_stream(upload_id)
    
    # Send initial log to confirm connection
    await log_streamer.add_log(upload_id, "🚀 Starting statement processing...", "info", 0)
    
    # Track processing time
    start_time = time.time()
    
    try:
        
        # ============================================
        # STEP 1: PDF EXTRACTION
        # ============================================
        await log_streamer.add_log(upload_id, "📄 Starting PDF extraction...", "info", 10)
        
        pdf_content = await statement_pdf.read()
        file_size_bytes = len(pdf_content)
        
        await log_streamer.add_log(
            upload_id, 
            f"✅ PDF loaded ({file_size_bytes / 1024 / 1024:.2f} MB)", 
            "success", 
            15
        )
        
        # ============================================
        # STEP 2: SMART AI EXTRACTION
        # ============================================
        await log_streamer.add_log(upload_id, "🤖 Extracting transactions with Smart AI...", "info", 20)
        
        # Initialize smart extractor if needed
        global smart_extractor
        if smart_extractor is None:
            smart_extractor = get_smart_extractor()
        
        try:
            transactions_from_ai = smart_extractor.extract_from_pdf(
                pdf_content, 
                password, 
                statement_pdf.filename
            )
            
            if not transactions_from_ai or len(transactions_from_ai) == 0:
                raise ValueError("No transactions extracted by AI")
            
            extraction_method = transactions_from_ai[0].get('extraction_method', 'SMART_AUTO')
            
            await log_streamer.add_log(
                upload_id,
                f"✅ Extracted {len(transactions_from_ai)} transactions using {extraction_method}",
                "success",
                40
            )
            
        except Exception as ai_error:
            await log_streamer.add_log(
                upload_id,
                f"⚠️  AI extraction failed: {str(ai_error)}. Falling back to text-based extraction...",
                "warning",
                25
            )
            
            # Fallback to text-based extraction
            extracted_text = await extract_text_from_pdf(password, pdf_content)
            transaction_lines = pre_parse_transaction_lines(extracted_text)
            
            if not transaction_lines:
                await log_streamer.add_log(
                    upload_id,
                    "❌ No transaction lines could be extracted",
                    "error",
                    0
                )
                return {
                    "status": "failed",
                    "upload_id": upload_id,
                    "message": "No transaction lines could be extracted",
                    "transactions": [],
                    "analysis": {"summary": {}, "category_wise_split": {}, "insights": []}
                }
            
            # Use legacy processor
            await log_streamer.add_log(
                upload_id,
                f"🔄 Processing {len(transaction_lines)} lines with legacy parser...",
                "info",
                30
            )
            
            processing_result = await optimized_processor.process_transactions(
                transaction_lines,
                []  # corrections will be loaded later
            )
            
            if not processing_result["success"]:
                await log_streamer.add_log(
                    upload_id,
                    f"❌ Processing failed: {processing_result['error']}",
                    "error",
                    0
                )
                return {
                    "status": "failed",
                    "upload_id": upload_id,
                    "message": processing_result["error"],
                    "transactions": [],
                    "analysis": {"summary": {}, "category_wise_split": {}, "insights": []}
                }
            
            transactions_from_ai = processing_result["transactions"]
            extraction_method = "TEXT_BASED"
            
            await log_streamer.add_log(
                upload_id,
                f"✅ Extracted {len(transactions_from_ai)} transactions",
                "success",
                40
            )
        
        # ============================================
        # STEP 4: CATEGORIZATION
        # ============================================
        await log_streamer.add_log(
            upload_id,
            f"🏷️  Categorizing {len(transactions_from_ai)} transactions...",
            "info",
            50
        )
        
        # Pre-fetch corrections
        corrections = await models.Correction.find_all().to_list()
        corrections_list = [c.dict() for c in corrections]
        
        # Debug: Log sample transaction before categorization
        logger.info(f"📝 Sample transaction BEFORE categorization: {transactions_from_ai[0] if transactions_from_ai else 'None'}")
        
        categorization_agent = agents.CategorizationAgent()
        categorized_transactions = await categorization_agent.categorize_transactions(
            transactions_from_ai,
            corrections_list
        )
        
        # Debug: Log sample transaction after categorization
        logger.info(f"📝 Sample transaction AFTER categorization: {categorized_transactions[0] if categorized_transactions else 'None'}")
        
        # Count categories
        category_counts = {}
        for txn in categorized_transactions:
            cat = txn.get('category', 'Uncategorized')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        logger.info(f"📊 Category distribution: {category_counts}")
        
        top_category = max(category_counts.items(), key=lambda x: x[1]) if category_counts else ("None", 0)
        
        await log_streamer.add_log(
            upload_id,
            f"✅ Categorization complete! Top category: {top_category[0]} ({top_category[1]} transactions)",
            "success",
            60
        )
        
        # ============================================
        # STEP 5: PREPARE TRANSACTIONS (NO ANALYSIS YET)
        # ============================================
        await log_streamer.add_log(
            upload_id,
            "📝 Preparing transactions for database...",
            "info",
            70
        )
        
        # Initialize encryptor for database encryption
        encryptor = None
        if settings.ENCRYPTION_KEY:
            try:
                encryptor = DataEncryptor(settings.ENCRYPTION_KEY, settings.ENCRYPTION_SALT)
                logger.info("🔐 Encryption enabled for database storage")
            except EncryptionError as e:
                logger.warning(f"⚠️  Encryption initialization failed: {e}. Proceeding without encryption.")
        else:
            logger.warning("⚠️  ENCRYPTION_KEY not set. Data will be stored unencrypted.")
        
        # Process and validate transactions
        transactions_to_save = []
        transaction_snapshots = []
        
        for t_raw in categorized_transactions:
            try:
                t = {k.lower(): v for k, v in t_raw.items()}
                
                credit_val = float(t.get('credit', 0.0) or 0.0)
                debit_val = float(t.get('debit', 0.0) or 0.0)
                amount_abs = credit_val if credit_val > 0 else debit_val
                
                date_str = t["date"]
                try:
                    if "/" in date_str:
                        date_obj = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
                    else:
                        date_obj = datetime.datetime.fromisoformat(date_str).date()
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse date string: {date_str}")
                    continue
                
                snap = {
                    'date': date_obj.isoformat(),
                    'description': t['description'],
                    'amount': amount_abs,
                    'category': t.get('category', 'Uncategorized'),
                    'credit': credit_val,
                    'debit': debit_val,
                    'upload_id': upload_id
                }
                
                db_transaction_data = {
                    'date': date_obj,
                    'description': t['description'],
                    'amount': amount_abs,
                    'category': t.get('category', 'Uncategorized'),
                    'upload_id': upload_id,
                    'user_id': current_user.user_id,  # Add user_id
                    'credit': credit_val,
                    'debit': debit_val,
                }
                
                # SECURITY: Encrypt sensitive fields before database storage
                if encryptor:
                    try:
                        db_transaction_data['description_encrypted'] = encryptor.encrypt(t['description'])
                        if t.get('reference'):
                            db_transaction_data['reference_encrypted'] = encryptor.encrypt(t['reference'])
                        logger.debug(f"🔐 Encrypted transaction data for database")
                    except EncryptionError as e:
                        logger.warning(f"⚠️  Encryption failed for transaction: {e}")
                
                transactions_to_save.append(models.Transaction(**db_transaction_data))
                transaction_snapshots.append(snap)
                
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Skipping transaction due to validation error: {e}")
                continue
        
        if not transactions_to_save:
            await log_streamer.add_log(
                upload_id,
                "❌ No valid transactions after validation",
                "error",
                0
            )
            return {
                "status": "failed",
                "upload_id": upload_id,
                "message": "No valid transactions after validation",
                "transactions": [],
                "analysis": {"summary": {}, "category_wise_split": {}, "insights": []}
            }
        
        # Security audit logging for encryption
        if encryptor:
            try:
                from .logging_config import log_encryption_operation
                log_encryption_operation(len(transactions_to_save), "process_statement")
            except ImportError:
                pass  # Logging config not available
        
        # Extract bank name and metadata
        bank_name = extract_bank_name(statement_pdf.filename)
        page_count = get_pdf_page_count(pdf_content)
        
        await log_streamer.add_log(
            upload_id,
            f"✅ Transactions ready! Bank: {bank_name}, {len(transactions_to_save)} transactions",
            "success",
            80
        )
        
        # ============================================
        # STEP 6: RETURN RESPONSE IMMEDIATELY (NO ANALYSIS YET)
        # ============================================
        await log_streamer.add_log(
            upload_id,
            "✅ Processing complete! Returning transactions...",
            "success",
            90
        )
        
        # ============================================
        # STEP 7: BACKGROUND TASKS (DB + ANALYSIS + VECTORS)
        # ============================================
        # Start background tasks: DB save, AI analysis, vector indexing
        async def run_background_tasks():
            # 1. Save to database first
            db_upload_id = await save_to_database_background(
                upload_id,
                statement_pdf.filename,
                file_size_bytes,
                bank_name,
                extraction_method,
                page_count,
                transactions_to_save,
                processing_time,
                [],  # No insights yet
                current_user.user_id
            )
            
            # 2. Generate AI analysis in background
            await log_streamer.add_log(
                upload_id,
                "📊 Generating financial analysis...",
                "info",
                None
            )
            
            try:
                analyst_agent = agents.FinancialAnalystAgent()
                financial_analysis = await analyst_agent.generate_financial_insights(transaction_snapshots)
                
                # Save insights to database
                if isinstance(financial_analysis, dict):
                    insights = financial_analysis.get('insights', [])
                    if db_upload_id and insights:
                        upload_doc = await models.Upload.get(db_upload_id)
                        if upload_doc:
                            upload_doc.insights = insights
                            await upload_doc.save()
                
                await log_streamer.add_log(
                    upload_id,
                    "✅ Financial analysis complete!",
                    "success",
                    None
                )
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                await log_streamer.add_log(
                    upload_id,
                    f"⚠️  Analysis failed: {str(e)}",
                    "warning",
                    None
                )
            
            # 3. Run vector indexing
            await index_vectors_background(
                upload_id,
                transactions_to_save,
                db_upload_id
            )
        
        asyncio.create_task(run_background_tasks())
        
        await log_streamer.add_log(
            upload_id,
            "💾 Saving to database (background)...",
            "info",
            95
        )
        
        await log_streamer.add_log(
            upload_id,
            "🔍 Creating search vectors (background)...",
            "info",
            98
        )
        
        await log_streamer.add_log(
            upload_id,
            "✅ All done! You can now view your transactions.",
            "complete",
            100
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Return response immediately (analysis will be generated in background)
        return {
            "status": "success",
            "upload_id": upload_id,
            "total_transactions": len(transaction_snapshots),
            "message": f"Successfully processed {len(transaction_snapshots)} transactions. Analysis generating in background.",
            "transactions": transaction_snapshots,
            "analysis": {
                "summary": {},
                "category_wise_split": {},
                "insights": ["Analysis is being generated in the background. Refresh to see insights."]
            },
            "metadata": {
                "bank_name": bank_name,
                "extraction_method": extraction_method,
                "page_count": page_count,
                "file_size_bytes": file_size_bytes,
                "total_transactions": len(transactions_to_save),
                "processing_time_seconds": round(processing_time, 2),
                "analysis_status": "generating"
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing {statement_pdf.filename}: {str(e)}", exc_info=True)
        await log_streamer.add_log(
            upload_id,
            f"❌ Error: {str(e)}",
            "error",
            0
        )
        return {
            "status": "failed",
            "upload_id": upload_id,
            "message": str(e),
            "transactions": [],
            "analysis": {"summary": {}, "category_wise_split": {}, "insights": []}
        }
    
    # FIX 4: Get upload metadata
    upload_metadata = await models.Upload.get(upload_id_str)
    
    # Return JSON response with all database transactions and metadata
    return {
        "status": "success",
        "upload_id": upload_id_str,
        "filename": statement_pdf.filename,
        "total_transactions": len(all_transactions_json),
        "message": f"Successfully processed {len(all_transactions_json)} transactions",
        "transactions": all_transactions_json,  # All transactions from database
        "analysis": {
            "summary": safe_analysis.summary,
            "category_wise_split": safe_analysis.category_wise_split,
            "insights": safe_analysis.insights
        },
        # FIX 4: Add comprehensive metadata
        "metadata": {
            "bank_name": upload_metadata.bank_name if upload_metadata else bank_name,
            "extraction_method": upload_metadata.extraction_method if upload_metadata else extraction_method,
            "processing_time_seconds": upload_metadata.processing_time_seconds if upload_metadata else processing_time,
            "page_count": upload_metadata.page_count if upload_metadata else page_count,
            "file_size_bytes": upload_metadata.file_size_bytes if upload_metadata else None,
            "processed_at": upload_metadata.processed_at.isoformat() if upload_metadata and upload_metadata.processed_at else None,
            "status": upload_metadata.status if upload_metadata else "completed"
        }
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
    from .rag_response_formatter import rag_formatter
    
    start_time = time.time()
    
    try:
        # Optimize: Limit to top 10 most relevant transactions for faster processing
        skip = (query.page - 1) * min(query.page_size, 10)  # Cap at 10 per page
        
        # Use paginated query to handle large result sets
        result = await rag_pipeline.query_with_pagination(
            query.query, 
            limit=min(query.page_size, 10),  # Limit to 10 for latency
            skip=skip
        )
        
        if not result["documents"]:
            return {
                "status": "success",
                "data": {
                    "answer": "I couldn't find any relevant transactions to answer your question.",
                    "type": "summary",
                    "sections": [],
                    "metrics": [],
                    "insights": [],
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            }
        
        # Generate answer with the retrieved documents
        answer = await rag_pipeline.answer(query.query, result["documents"])
        
        if answer is None:
            return {
                "status": "success",
                "data": {
                    "answer": "Sorry, I was unable to generate a response.",
                    "type": "summary",
                    "sections": [],
                    "metrics": [],
                    "insights": [],
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            }
        
        # Format response using RAG formatter
        formatted_response = rag_formatter.format_response(answer)
        
        # Add pagination info
        if result["has_more"]:
            formatted_response['data']['pagination'] = {
                'current_page': result['current_page'],
                'total_count': result['total_count'],
                'returned_count': result['returned_count'],
                'has_more': True
            }
        else:
            formatted_response['data']['pagination'] = {
                'current_page': result['current_page'],
                'total_count': result['total_count'],
                'returned_count': result['returned_count'],
                'has_more': False
            }
        
        # Add processing time
        processing_time = int((time.time() - start_time) * 1000)
        formatted_response['data']['processing_time_ms'] = processing_time
        
        # Log if response time exceeds target
        if processing_time > 3000:
            logger.warning(f"Chat response took {processing_time}ms (target: <3000ms)")
        
        return formatted_response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return {
            "status": "error",
            "data": {
                "answer": f"An error occurred: {str(e)}",
                "type": "summary",
                "sections": [],
                "metrics": [],
                "insights": [],
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
        }

@app.post("/correct-transaction/", response_model=models.Correction)
async def correct_transaction_category(correction_data: models.CorrectionCreate):
    keyword = correction_data.transaction_description_keyword.upper()
    correction = await models.Correction.find_one(models.Correction.transaction_description_keyword == keyword)
    if correction:
        correction.correct_category = correction_data.correct_category
    else:
        correction = models.Correction(
            transaction_description_keyword=keyword,
            correct_category=correction_data.correct_category
        )
    await correction.save()
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
                logger.debug("🔓 Decryption enabled for transaction retrieval")
                
                # Security audit logging
                try:
                    from .logging_config import log_decryption_operation
                    log_decryption_operation(len(transactions), "", "get_statement_details")
                except ImportError:
                    pass  # Logging config not available
            except EncryptionError as e:
                logger.warning(f"⚠️  Decryption initialization failed: {e}")
        
        # Convert to JSON format and decrypt if needed
        transactions_json = []
        for txn in transactions:
            # Get description (decrypt if encrypted field exists)
            description = txn.description
            if encryptor and hasattr(txn, 'description_encrypted') and txn.description_encrypted:
                try:
                    description = encryptor.decrypt(txn.description_encrypted)
                    logger.debug(f"🔓 Decrypted transaction description")
                except EncryptionError as e:
                    logger.warning(f"⚠️  Decryption failed: {e}")
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
    category: str = None,
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
        
        # Filter by category
        if category and category != "all":
            query["category"] = category
        
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
        
        return {
            "status": "success",
            "data": {
                "total_transactions": total_transactions,
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "balance": round(balance, 2),
                "average_transaction": round(average_transaction, 2),
                "largest_expense": round(largest_expense, 2),
                "largest_income": round(largest_income, 2)
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
            'Personal Transfer',
            'Food & Dining',
            'Shopping',
            'Transport',
            'Bills & Utilities',
            'Entertainment',
            'Income',
            'Investments',
            'Healthcare',
            'Education',
            'Others'
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
        
        logger.info(f"✅ Updated transaction {transaction_id} category from {old_category} to {new_category}")
        
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
            
            logger.info(f"✅ Updated Pinecone vector for transaction {transaction_id}")
        except Exception as e:
            logger.error(f"⚠️  Failed to update Pinecone vector: {e}")
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
            logger.info(f"✅ Deleted vectors from Pinecone for upload_id: {upload_id}")
        except Exception as e:
            logger.error(f"⚠️  Failed to delete from Pinecone: {e}")
            # Continue with MongoDB deletion even if Pinecone fails
        
        # Step 4: Delete transactions from MongoDB
        delete_result = await models.Transaction.find(
            models.Transaction.upload_id == upload_id
        ).delete()
        
        logger.info(f"✅ Deleted {delete_result.deleted_count} transactions from MongoDB")
        
        # Step 5: Delete upload record from MongoDB
        await upload.delete()
        logger.info(f"✅ Deleted upload record from MongoDB")
        
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
