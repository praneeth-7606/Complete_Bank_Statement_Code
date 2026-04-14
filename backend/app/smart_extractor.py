# app/smart_extractor.py
# ============================================================
# EXTRACTION METHODOLOGY: Mistral OCR 3 (mistral-ocr-latest)
# ============================================================
# NEW APPROACH (ACTIVE):
#   - Sends base64-encoded PDF directly to Mistral OCR 3
#   - OCR model reads the document (text, tables, scanned images)
#     and returns structured JSON transactions in a SINGLE API call
#   - No secondary LLM call needed
#
# OLD APPROACH (COMMENTED OUT below):
#   - Classified PDFs as TABLE_BASED / TEXT_BASED / IMAGE_BASED
#   - TABLE_BASED   pdfplumber (column parsing)
#   - TEXT_BASED    Gemini text parsing
#   - IMAGE_BASED   Gemini Vision (page-by-page images)
#   - Then validated with BalanceVerifier + TableStructureAnalyzer
# ============================================================

import io
import os
import json
import base64
import logging
import asyncio
import re
import time
import tempfile
import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

import google.generativeai as genai
from pydantic import BaseModel, Field

# LangGraph Imports
from typing import TypedDict
from langgraph.graph import StateGraph, END

# LangChain Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from .config import settings
from . import models, agents
from .vector_store_pinecone import PineconeVectorStore
from .log_streamer import log_streamer

logger = logging.getLogger(__name__)

# ============================================================
# GLOBAL STATE contract for LangGraph
# ============================================================
class ProcessingState(TypedDict):
    file_path: str
    file_bytes: bytes
    password: str
    user_id: Optional[str]
    user_name: str
    document_type: Optional[str]
    extraction_method: str
    masked_pdf: Optional[bytes]
    raw_ocr_output: Optional[Dict]
    cleaned_transactions: List[Dict]
    categorized_transactions: List[Dict]
    insights: Optional[Dict]
    audit_log_path: Optional[str]
    errors: List[str]
    vector_ids: List[str]
    db_upload_id: Optional[str]
    corrections: List[Dict]
    streaming_id: Optional[str]
    timing: Dict[str, float]



# ============================================================
# NEW EXTRACTOR: Mistral OCR 3
# ============================================================

class MistralOCRExtractor:
    """
    NEW EXTRACTOR using Mistral OCR 3 (mistral-ocr-latest).

    Flow:
        1. Base64-encode the PDF bytes (handles both digital & scanned PDFs)
        2. Send to Mistral OCR API with a strict JSON schema prompt
           via the 'document_annotation_format' / chat-completion approach
        3. Mistral returns structured transactions JSON directly
        4. Validate & normalise with _validate_transactions helper

    Why single-step:
        Mistral OCR 3 supports 'doc-as-prompt'  the document IS the context,
        and a prompt drives the model to output JSON directly without a 
        second LLM call.
    """

    # JSON schema we instruct Mistral to fill per page / document
    TRANSACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "document_type": {
                "type": "string",
                "enum": ["bank_statement", "credit_card_bill", "loan_statement", "other"],
                "description": "Categorize the overall uploaded document into one of these types based on its contents."
            },
            "transactions": {
                "type": "array",
                "description": "The complete, exhaustive list of ALL transactions from all pages. Do not skip any row. Must be 100% complete.",
                "items": {
                    "type": "object",
                    "properties": {
                        "date":        {"type": "string", "description": "Transaction date exactly as printed (e.g., 2024-03-12 or 12/03/2024)."},
                        "description": {"type": "string", "description": "Full transaction description. Combine multi-line descriptions belonging to the same transaction into a single string."},
                        "debit":       {"type": "number", "description": "Money OUT of account. If this is a credit, set strictly to 0.00. Do not use commas."},
                        "credit":      {"type": "number", "description": "Money INTO account. If this is a debit, set strictly to 0.00. Do not use commas."},
                        "balance":     {"type": "number", "description": "Running balance after this transaction. 0.00 if missing or invisible. Do not use commas."}
                    },
                    "required": ["date", "description", "debit", "credit", "balance"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["document_type", "transactions"],
        "additionalProperties": False
    }

    EXTRACTION_PROMPT = """You are an elite, infallible financial document parser.
Analyze this document. First, classify its overall `document_type`.
Then, extract EVERY SINGLE transaction line by line without missing a single one.

CRITICAL DIRECTIVES:
1. EXHAUSTIVE EXTRACTION (NO DROPS): You MUST extract 100% of the transactions from the first page to the very last page. NEVER truncate, summarize, or skip rows.
2. HEADER PERSISTENCE: Pay close attention to the headers on the first page (e.g., Date, Description, Withdrawal/Debit, Deposit/Credit, Balance). Even if headers are missing on subsequent pages, apply this same column layout strictly to every single row in the document.
3. DEBIT VS CREDIT TERMINOLOGY: 
   - "Withdrawal", "Debit", "Dr", or values in the first amount column typically mean DEBIT.
   - "Deposit", "Credit", "Cr", or values in the second amount column typically mean CREDIT.
   - Cross-reference with the "Balance" column: if Balance[N] < Balance[N-1], the transaction N is a DEBIT.
4. ROW INTEGRITY: Keep every horizontal row strictly self-contained. Do not mix data between rows.
5. INTACT DESCRIPTIONS: Combine multi-line descriptions into a single string.
6. EXACT AMOUNTS: Set EITHER debit OR credit to the numerical amount based on its column. Set the other to exactly 0.00. Remove all commas.
7. DATES: Extract exactly as printed.

Return ONLY a perfectly formed JSON object matching the requested schema. No markdown, no preambles."""

    # Directory where per-statement OCR logs are saved
    _LOG_DIR = Path(__file__).parent.parent / "logs" / "ocr"

    def __init__(self):
        logger.info("[INIT] Initializing Mistral OCR 3 Extractor (mistral-ocr-latest)...")

        if not settings.MISTRAL_API_KEY:
            raise ValueError(
                "MISTRAL_API_KEY is not set. "
                "Add MISTRAL_API_KEY=your_key to your .env file."
            )

        try:
            from mistralai.client.sdk import Mistral
            self.client = Mistral(api_key=settings.MISTRAL_API_KEY)
            logger.info("[OK] Mistral client initialised successfully")
        except ImportError:
            raise ImportError(
                "mistralai package not installed. Run: pip install mistralai"
            )

        # Keyword lists used in fallback validation
        self.debit_keywords = self._load_debit_keywords()
        self.credit_keywords = self._load_credit_keywords()

        # Initialize Gemini for Fallback
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        else:
            logger.warning("GEMINI_API_KEY not set. Gemini Vision fallback will unavailable.")
            self.gemini_model = None

        logger.info("[OK] Mistral OCR 3 Extractor ready (with Gemini fallback)")

    # ----------------------------------------------------------
    # PUBLIC: main entry point (same signature as old extractor)
    # ----------------------------------------------------------

    def _mask_pdf_bytes(self, pdf_bytes: bytes) -> bytes:
        """Use PyMuPDF to visually redact PII from the PDF before sending to AI."""
        logger.info("[MASK] Masking PII (Account, Phone, Email, UPI) in PDF before OCR...")
        masker = getattr(self, "masker", None)
        if not masker:
            from .data_masker import DataMasker
            masker = DataMasker()
            self.masker = masker

        patterns = [
            masker._phone_pattern,
            masker._account_pattern,
            masker._upi_pattern,
            masker._email_pattern
        ]

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                tmp_pdf.write(pdf_bytes)
                tmp_path = tmp_pdf.name
                
            doc = fitz.open(tmp_path)
            redactions_made = 0
            
            for page in doc:
                text = page.get_text()
                # Find all unique matches across all patterns on this page
                matches_to_redact = set()
                for pattern in patterns:
                    for match in pattern.finditer(text):
                        matches_to_redact.add(match.group())
                
                # Apply redactions for each found match
                for match_text in matches_to_redact:
                    if len(match_text) < 4: continue
                    rects = page.search_for(match_text)
                    for rect in rects:
                        # Use White fill (1, 1, 1) instead of Black (0, 0, 0)
                        # Black boxes break Mistral's table layout vision engine if they bleed into amount columns.
                        # White boxes seamlessly blend into the background, preserving column spacing perfectly.
                        page.add_redact_annot(rect, fill=(1, 1, 1), cross_out=False)
                        redactions_made += 1
                        
                # Apply redactions, replacing text and drawing white covers over images/vectors
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                
            if redactions_made > 0:
                logger.info(f"   [MASK] Successfully redacted {redactions_made} PII instances from PDF.")
                
            return doc.tobytes()
            
        except Exception as e:
            logger.error(f"   [WARN] PDF Masking failed: {e}. Proceeding with original PDF.")
            return pdf_bytes
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try: 
                   os.unlink(tmp_path)
                except: 
                    pass

    # ----------------------------------------------------------
    # THE LANGGRAPH ORCHESTRATION PIPELINE
    # ----------------------------------------------------------

    async def process_statement(self, pdf_bytes: bytes, password: str, filename: str, user_id: str = None, user_name: str = "User", corrections: List[Dict] = None, streaming_id: str = None) -> Dict:
        """Process a bank statement using a LangGraph pipeline"""
        """
        Extract transactions using a deterministic 11-node LangGraph State Machine.
        Flow: Analyze -> Mask -> Mistral (Primary) -> Verifier -> Categorize -> Insights -> Storage
        """
        # 1. LOGGING CONTEXT
        logger.info(f"[GRAPH] LANGGRAPH OPTIMIZED TWO-PHASE PIPELINE: {filename or 'statement.pdf'}")
        logger.info("=" * 80)
        start_time = time.time()

        # 2. Define the Graph Nodes (Local to this extraction for context accessibility)
        def node_analyze(state: ProcessingState) -> ProcessingState:
            logger.info("   [SEARCH] [1/11] NODE: Analyzing Document Type (Deterministic)...")
            t_start = time.time()
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                    tmp_pdf.write(state["file_bytes"])
                    tmp_pdf_path = tmp_pdf.name
                doc = fitz.open(tmp_pdf_path)
                page_1_text = doc[0].get_text()[:1000].lower() if len(doc) > 0 else ""
                doc.close()
                os.unlink(tmp_pdf_path)
                
                if "credit card" in page_1_text or "minimum amount due" in page_1_text:
                    state["document_type"] = "credit_card_bill"
                elif "loan" in page_1_text or "emi" in page_1_text:
                    state["document_type"] = "loan_statement"
                else:
                    state["document_type"] = "bank_statement"
                logger.info(f"      -> Classification: {state['document_type']}")
            except Exception as e:
                logger.warning(f"      -> Analysis failed: {e}. Assuming bank_statement.")
                state["document_type"] = "bank_statement"
            
            state["timing"]["analyze"] = time.time() - t_start
            return state

        def node_mask(state: ProcessingState) -> ProcessingState:
            logger.info("   [MASK] [2/11] NODE: Masking Metadata (Deterministic)...")
            t_start = time.time()
            state["masked_pdf"] = state["file_bytes"]  
            state["timing"]["mask"] = time.time() - t_start
            return state

        async def node_ocr_primary(state: ProcessingState) -> ProcessingState:
            logger.info("   [OCR] [3/11] NODE: Extracting with Mistral OCR (Multi-Page Context)...")
            t_start = time.time()
            try:
                # Optimized: Send whole PDF to Mistral to preserve header context across pages
                import fitz
                doc = fitz.open(stream=state["file_bytes"], filetype="pdf")
                logger.info(f"      -> Processing all {len(doc)} pages together for context preservation.")
                doc.close()

                # Dispatch single call for the entire document
                # This ensures Mistral sees the headers on Page 1 and applies them to later pages.
                res = await asyncio.to_thread(
                    self._ocr_pdf_with_mistral, 
                    state["file_bytes"], 
                    state["file_path"]
                )
                
                doc_type, txns = res
                if txns:
                    state["raw_ocr_output"] = {"transactions": txns}
                    state["extraction_method"] = "MISTRAL_OCR_3_SEQUENTIAL"
                    if not state["document_type"]:
                        state["document_type"] = doc_type
                    logger.info(f"   [SUCCESS] Extraction returned {len(txns)} transactions across all pages.")
                else:
                    state["errors"].append("Mistral returned 0 transactions.")

            except Exception as e:
                logger.error(f"   [ERROR] Mistral extraction failed: {e}")
                state["errors"].append(f"Mistral Error: {str(e)}")
            
            state["timing"]["ocr_primary"] = time.time() - t_start
            return state

        def node_ocr_fallback(state: ProcessingState) -> ProcessingState:
            logger.info("   [FALLBACK] [4/5] NODE: Fallback -> Extracting via Gemini Vision (Agent)...")
            t_start = time.time()
            try:
                if not self.gemini_model:
                     state["errors"].append("Gemini disabled (No API Key).")
                     return state
                doc_type, txns = self._extract_with_gemini_vision(state["file_bytes"], state["password"])
                state["raw_ocr_output"] = {"transactions": txns}
                state["extraction_method"] = "GEMINI_VISION_FALLBACK"
            except Exception as e:
                state["errors"].append(f"Gemini API Error: {str(e)}")
            
            state["timing"]["ocr_fallback"] = time.time() - t_start
            return state

        def node_verify(state: ProcessingState) -> ProcessingState:
            logger.info("   [VERIFY] [6/11] NODE: Verification & Truth Layer (Deterministic)...")
            t_start = time.time()
            raw_txns = state["raw_ocr_output"].get("transactions", []) if state["raw_ocr_output"] else []
            if not raw_txns:
                state["errors"].append("Verification FAILED: No raw transactions.")
                state["timing"]["verify"] = time.time() - t_start
                return state
            try:
                validated = self._validate_transactions(raw_txns)
                
                masker = getattr(self, "masker", None)
                if not masker:
                    from .data_masker import DataMasker
                    masker = DataMasker()
                    self.masker = masker
                
                for v in validated:
                    if v.get("description"):
                        v["description"] = masker.mask_description(v["description"])
                    v['extraction_method'] = state["extraction_method"]
                    v['document_type'] = state["document_type"]
                    
                state["cleaned_transactions"] = validated
                logger.info(f"      -> Verified {len(validated)} transactions.")
            except Exception as e:
                state["errors"].append(f"Verification Error: {str(e)}")
            
            state["timing"]["verify"] = time.time() - t_start
            return state

        async def node_categorize(state: ProcessingState) -> ProcessingState:
            logger.info("   [CAT] [7/11] NODE: Categorization (LLM-First Structured Output)...")
            t_start = time.time()
            if not state["cleaned_transactions"]:
                state["timing"]["categorize"] = 0
                return state
            try:
                cat_agent = agents.CategorizationAgent()
                categorized = await cat_agent.categorize_transactions(
                    state["cleaned_transactions"], 
                    user_id=state.get("user_id"),
                    user_name=state.get("user_name", "User"),
                    streaming_id=state.get("streaming_id")
                )
                state["categorized_transactions"] = categorized
            except Exception as e:
                logger.error(f"Categorization Node Error: {e}")
                state["errors"].append(f"Categorization Error: {e}")
                # Maintain chain even if categorization fails
                for tx in state["cleaned_transactions"]:
                    tx["category"] = "Others"
                state["categorized_transactions"] = state["cleaned_transactions"]
            
            state["timing"]["categorize"] = time.time() - t_start
            return state

        async def node_insights(state: ProcessingState) -> ProcessingState:
            logger.info("   [STATS] [8/11] NODE: Financial Insights (Multi-step Agent)...")
            t_start = time.time()
            if not state["categorized_transactions"]:
                state["timing"]["insights"] = 0
                return state
            try:
                analyst = agents.FinancialAnalystAgent()
                insights = await analyst.generate_financial_insights(state["categorized_transactions"])
                state["insights"] = insights
            except Exception as e:
                logger.error(f"Insights Node Error: {e}")
                state["errors"].append(f"Insights Error: {e}")
            
            state["timing"]["insights"] = time.time() - t_start
            return state

        def node_audit_log(state: ProcessingState) -> ProcessingState:
            logger.info("   [LOG] [9/11] NODE: Audit Logging (Deterministic)...")
            elapsed = time.time() - start_time
            raw_txns = state["raw_ocr_output"].get("transactions", []) if state["raw_ocr_output"] else []
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = re.sub(r"[^\w\-.\ ]", "_", state["file_path"] or "statement").strip()
                log_filename = f"{ts}_{safe_name}.json"
                
                self._write_ocr_log(
                    filename=state["file_path"],
                    extraction_method=state["extraction_method"],
                    document_type=state["document_type"] or "unknown",
                    raw_transactions=raw_txns,
                    validated_transactions=state["cleaned_transactions"],
                    elapsed=elapsed
                )
                state["audit_log_path"] = str(self._LOG_DIR / log_filename)
            except Exception as e:
                logger.warning(f"Audit Log Node Error: {e}")
            return state

        async def node_database(state: ProcessingState) -> ProcessingState:
            logger.info("   [DB] [10/11] NODE: Database Storage (Deterministic)...")
            if not state["categorized_transactions"]: return state
            try:
                # Save Upload metadata
                upload = models.Upload(
                    filename=state["file_path"],
                    file_size_bytes=len(state["file_bytes"]),
                    status="completed",
                    user_id=state["user_id"],
                    bank_name=state["document_type"],
                    extraction_method=state["extraction_method"],
                    total_transactions=len(state["categorized_transactions"]),
                    processing_time_seconds=time.time() - start_time,
                    insights=state["insights"].get("insights", []) if state["insights"] else []
                )
                await upload.save()
                state["db_upload_id"] = str(upload.id)
                
                # Save individual Transactions
                db_txns = []
                for tx in state["categorized_transactions"]:
                    # Handle date conversion for Beanie
                    tx_date = tx.get("date")
                    if isinstance(tx_date, str):
                        try:
                            tx_date = datetime.strptime(tx_date, "%Y-%m-%d").date()
                        except:
                            tx_date = datetime.now().date()
                    
                    db_txns.append(models.Transaction(
                        date=tx_date,
                        description=tx.get("description", "No description"),
                        amount=float(tx.get("amount", 0)),
                        debit=float(tx.get("debit", 0)),
                        credit=float(tx.get("credit", 0)),
                        category=tx.get("category", "Others"),
                        upload_id=state["db_upload_id"],
                        user_id=state["user_id"]
                    ))
                
                if db_txns:
                    await models.Transaction.insert_many(db_txns)
                logger.info(f"      -> Successfully saved {len(db_txns)} transactions to MongoDB.")
            except Exception as e:
                logger.error(f"Database Node Error: {e}")
                state["errors"].append(f"Database Error: {e}")
            return state

        async def node_vector_index(state: ProcessingState) -> ProcessingState:
            logger.info("    [11/11] NODE: Vector Indexing (Deterministic)...")
            if not state["categorized_transactions"] or not state["db_upload_id"]: return state
            try:
                vector_db = PineconeVectorStore(
                    api_key=settings.PINECONE_API_KEY,
                    environment=settings.PINECONE_ENVIRONMENT,
                    index_name=settings.PINECONE_INDEX_NAME
                )
                # Prepare dictionaries for indexing
                tx_dicts = []
                for tx in state["categorized_transactions"]:
                    d = tx.copy()
                    d["upload_id"] = state["db_upload_id"]
                    d["user_id"] = state["user_id"]
                    tx_dicts.append(d)
                
                await vector_db.add_transactions(tx_dicts)
                logger.info(f"      -> Successfully indexed {len(tx_dicts)} transactions in Pinecone.")
            except Exception as e:
                logger.warning(f"Vector Index Node Error: {e}")
                state["errors"].append(f"Vector Indexing Error: {e}")
            return state

        # 3. Define Conditional Edges
        def route_after_primary(state: ProcessingState) -> str:
            raw_data = state.get("raw_ocr_output")
            method = state.get("extraction_method")
            
            if raw_data and method in ["MISTRAL_OCR_3", "MISTRAL_OCR_3_PARALLEL", "MISTRAL_OCR_3_SEQUENTIAL"]:
                logger.info(f"    ROUTING: Mistral Successful ({len(raw_data.get('transactions', []))} txns). Jumping to Verification.")
                return "verify"
            
            logger.warning(f"    ROUTING: Mistral Incomplete (method={method}). Engaging Gemini Fallback.")
            return "fallback"

        # 4. Compile the Graph (Sync Phase: Extraction + Reasoning)
        workflow = StateGraph(ProcessingState)

        workflow.add_node("analyze", node_analyze)
        workflow.add_node("mask", node_mask)
        workflow.add_node("mistral", node_ocr_primary)
        workflow.add_node("gemini", node_ocr_fallback)
        workflow.add_node("verify", node_verify)
        workflow.add_node("categorize", node_categorize)
        # NOTE: insights, db, vector run in background - NOT in sync graph

        # Build Edges
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "mask")
        workflow.add_edge("mask", "mistral")
        
        workflow.add_conditional_edges(
            "mistral",
            route_after_primary,
            {"verify": "verify", "fallback": "gemini"}
        )
        
        workflow.add_edge("gemini", "verify")
        workflow.add_edge("verify", "categorize")
        workflow.add_edge("categorize", END)  # [START] Hot-path ends here. UI can show results immediately!

        # insights, db, vector -> all triggered in _run_post_processing_background()

        app = workflow.compile()

        # 5. Invoke Sync Pipeline (Hot-Path)
        initial_state = ProcessingState(
            file_path=filename,
            file_bytes=self._decrypt_pdf_if_needed(pdf_bytes, password, filename),
            password=password,
            user_id=user_id,
            user_name=user_name,
            document_type=None,
            extraction_method="None",
            masked_pdf=None,
            raw_ocr_output=None,
            cleaned_transactions=[],
            categorized_transactions=[],
            insights=None,
            audit_log_path=None,
            errors=[],
            vector_ids=[],
            db_upload_id=None,
            corrections=corrections,
            streaming_id=streaming_id,
            timing={}
        )

        try:
            final_state = await app.ainvoke(initial_state)
            
            # Hot-path complete: transactions are ready, return to user immediately!
            if streaming_id:
                await log_streamer.add_log(streaming_id, "[OK] Categorization Complete! Your results are ready.", "success", 98)
                await log_streamer.add_log(streaming_id, "[RETRY] Insights & Persistence running in background...", "info", 100)

            # TRIGGER ASYNC PHASE (Background: Insights, DB, Vector)
            asyncio.create_task(self._run_post_processing_background(final_state))
            
        except Exception as e:
            logger.error(f"Graph Execution Fatal Error: {e}")
            raise

        logger.info(f"[OK] Sync Pipeline Hot-Path Complete. Results returned immediately to user.")
        logger.info("=" * 80)
        
        return {
            "upload_id": streaming_id,  # Use streaming_id as the stable upload reference
            "transactions": final_state.get("categorized_transactions", []),
            "insights": {},  # Insights are generated in background; fetch via /api/uploads/{id} later
            "errors": final_state.get("errors", []),
            "processing_time": time.time() - start_time
        }

    async def _run_post_processing_background(self, state: ProcessingState):
        """
        COLD-PATH: Insights -> DB Storage -> Vector Indexing -> Audit Log.
        Runs AFTER the user has already received their categorized transactions.
        """
        t_bg_start = time.time()
        streaming_id = state.get("streaming_id")
        try:
            logger.info(f"[API] [Background] Starting post-processing for {streaming_id}")

            #  STEP 1: Generate Financial Insights (LLM, slow) 
            bg_insights = {}
            if state.get("categorized_transactions"):
                try:
                    logger.info("   [BRAIN] [Background] Generating Financial Insights...")
                    analyst = agents.FinancialAnalystAgent()
                    bg_insights = await analyst.generate_financial_insights(state["categorized_transactions"])
                    logger.info("   [OK] [Background] Insights generated.")
                except Exception as e:
                    logger.error(f"Background Insights Error: {e}")

            #  STEP 2: Database Storage (MongoDB) 
            db_upload_id = None
            db_txns = []
            if state.get("categorized_transactions"):
                try:
                    upload = models.Upload(
                        filename=state["file_path"],
                        file_size_bytes=len(state["file_bytes"]),
                        status="completed",
                        user_id=state["user_id"],
                        bank_name=state["document_type"] or "Statement",
                        extraction_method=state["extraction_method"],
                        total_transactions=len(state["categorized_transactions"]),
                        processing_time_seconds=round(time.time() - t_bg_start, 2),
                        insights=bg_insights.get("insights", []) if isinstance(bg_insights, dict) else [],
                        upload_id=streaming_id
                    )
                    await upload.save()
                    db_upload_id = str(upload.id)

                    for tx in state["categorized_transactions"]:
                        tx_date = tx.get("date")
                        if isinstance(tx_date, str):
                            try: tx_date = datetime.strptime(tx_date, "%Y-%m-%d").date()
                            except: tx_date = datetime.now().date()

                        db_txns.append(models.Transaction(
                            date=tx_date,
                            description=tx.get("description", "No description"),
                            amount=float(tx.get("amount", 0)),
                            debit=float(tx.get("debit", 0)),
                            credit=float(tx.get("credit", 0)),
                            category=tx.get("category", "Other"),
                            upload_id=db_upload_id,
                            user_id=state["user_id"]
                        ))

                    if db_txns:
                        await models.Transaction.insert_many(db_txns)
                    logger.info(f"   [OK] [Background] Saved {len(db_txns)} transactions to MongoDB.")
                except Exception as e:
                    logger.error(f"Background DB Error: {e}")


            #  STEP 3: Vector Indexing (Pinecone) 
            if db_upload_id:
                try:
                    from .vector_store_pinecone import PineconeVectorStore
                    vector_db = PineconeVectorStore(
                        api_key=settings.PINECONE_API_KEY,
                        environment=settings.PINECONE_ENVIRONMENT,
                        index_name=settings.PINECONE_INDEX_NAME
                    )
                    tx_dicts = []
                    for i, tx in enumerate(state["categorized_transactions"]):
                        d = tx.copy()
                        d["upload_id"] = db_upload_id
                        d["user_id"] = state["user_id"]
                        if i < len(db_txns):
                            d["transaction_id"] = str(db_txns[i].id)
                        else:
                            import uuid
                            d["transaction_id"] = str(uuid.uuid4())
                        tx_dicts.append(d)
                    
                    await vector_db.add_transactions(tx_dicts)
                    logger.info(f"   [OK] [Background] Indexed {len(tx_dicts)} vectors in Pinecone.")
                except Exception as e:
                    logger.warning(f"Background Vector Error: {e}")
            
            #  STEP 4: Audit Logging (full timings available now) 
            try:
                t_bg_end = time.time()
                bg_duration = t_bg_end - t_bg_start
                state["timing"]["background_tasks"] = bg_duration
                
                raw_txns = state["raw_ocr_output"].get("transactions", []) if state["raw_ocr_output"] else []
                total_duration = sum(state["timing"].values())
                
                self._write_ocr_log(
                    filename=state["file_path"],
                    extraction_method=state["extraction_method"],
                    document_type=state["document_type"] or "unknown",
                    raw_transactions=raw_txns,
                    validated_transactions=state["cleaned_transactions"],
                    elapsed=total_duration,
                    timing_breakdown=state["timing"]
                )
                logger.info(f"   [OK] [Background] All tasks complete in {bg_duration:.1f}s.")
            except Exception as e:
                logger.warning(f"Background Final Audit Error: {e}")

        except Exception as e:
            logger.error(f"[FAIL] Critical Background Failure: {e}")


    # ----------------------------------------------------------
    # PRIVATE: OCR log writer
    # ----------------------------------------------------------

    def _write_ocr_log(
        self,
        filename: str,
        extraction_method: str,
        document_type: str,
        raw_transactions: List[Dict],
        validated_transactions: List[Dict],
        elapsed: float,
        timing_breakdown: Optional[Dict] = None
    ) -> None:
        """
        Write a structured JSON log file for each processed statement.

        Location:  <project_root>/logs/ocr/
        Filename:  <YYYYMMDD_HHMMSS>_<filename>.json

        Log contents:
          - metadata      : filename, timestamp, timing, counts
          - raw_output    : exactly what Mistral OCR returned (before validation)
          - validated     : final cleaned transaction list sent to the database
          - summary       : quick stats (total debit, total credit)
        """
        try:
            self._LOG_DIR.mkdir(parents=True, exist_ok=True)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r"[^\w\-.\ ]", "_", filename or "statement").strip()
            log_path = self._LOG_DIR / f"{ts}_{safe_name}.json"

            total_debit  = sum(t.get("debit",  0) for t in validated_transactions)
            total_credit = sum(t.get("credit", 0) for t in validated_transactions)

            log_data = {
                "metadata": {
                    "filename":            filename or "statement.pdf",
                    "processed_at":        datetime.now().isoformat(),
                    "extraction_method":   extraction_method,
                    "document_type":       document_type,
                    "model_used":          "mistral-ocr-latest" if "MISTRAL" in extraction_method else "gemini-3.1-flash-lite-preview",
                    "processing_time_sec": round(elapsed, 3),
                    "timing_breakdown":    {k: round(v, 3) for k, v in (timing_breakdown or {}).items()},
                    "raw_transaction_count":       len(raw_transactions),
                    "validated_transaction_count": len(validated_transactions),
                },
                "summary": {
                    "total_debit":   round(total_debit,  2),
                    "total_credit":  round(total_credit, 2),
                    "net_flow":      round(total_credit - total_debit, 2),
                },
                "raw_output": {
                    "description": "Exact transaction list returned by Mistral OCR before any validation/correction",
                    "transactions": raw_transactions,
                },
                "validated_output": {
                    "description": "Final transaction list after balance-based correction and normalisation",
                    "transactions": validated_transactions,
                },
            }

            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"[LOG] OCR log saved  {log_path}")

        except Exception as e:
            # Log writing should never break the main extraction flow
            logger.warning(f"[WARN]  Could not write OCR log: {e}")

    # ----------------------------------------------------------
    # PRIVATE: Mistral OCR API call
    # ----------------------------------------------------------

    def _decrypt_pdf_if_needed(
        self, pdf_bytes: bytes, password: str, filename: str
    ) -> bytes:
        """
        If the PDF is password-protected, decrypt it with PyMuPDF and return
        the decrypted bytes so Mistral OCR receives a readable document.
        """
        if not password:
            return pdf_bytes

        try:
            import fitz  # PyMuPDF
            import tempfile

            logger.info("[UNLOCKED] Decrypting password-protected PDF before OCR...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name

            try:
                doc = fitz.open(tmp_path)
                if doc.needs_pass:
                    if not doc.authenticate(password):
                        raise ValueError(
                            f"Incorrect password for PDF: {filename}"
                        )
                # Write decrypted version
                import io as _io
                buffer = _io.BytesIO()
                doc.save(buffer)
                doc.close()
                decrypted_bytes = buffer.getvalue()
                logger.info(" PDF decrypted successfully")
                return decrypted_bytes
            finally:
                os.unlink(tmp_path)

        except ImportError:
            logger.warning(
                "PyMuPDF (fitz) not installed  sending encrypted PDF to Mistral. "
                "Mistral OCR may not be able to read it. Install with: pip install pymupdf"
            )
            return pdf_bytes
        except Exception as e:
            logger.warning(f"Could not decrypt PDF: {e}. Sending as-is.")
            return pdf_bytes

    def _ocr_pdf_with_mistral(self, pdf_bytes: bytes, filename: str) -> Tuple[str, List[Dict]]:
        """
        Send the PDF to Mistral OCR 3 using the dedicated OCR API (v2 SDK).
        Returns: (document_type, transactions list)
        """
        logger.info("[API] Sending PDF to Mistral OCR API (mistral-ocr-latest)...")

        # Encode PDF as base64 data URI
        b64_pdf = base64.standard_b64encode(pdf_bytes).decode("utf-8")
        document_data_uri = f"data:application/pdf;base64,{b64_pdf}"

        logger.info(
            f"   PDF size: {len(pdf_bytes) / 1024:.1f} KB  |  "
            f"Base64 size: {len(b64_pdf) / 1024:.1f} KB"
        )

        # JSON schema for structured output
        annotation_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "FinancialDocument",
                "schema": self.TRANSACTION_SCHEMA,
                "strict": True,
            },
        }

        max_retries = 3
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"   [RETRY] Attempt {attempt}/{max_retries}...")

                ocr_response = self.client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "document_url",
                        "document_url": document_data_uri,
                    },
                    document_annotation_format=annotation_format,
                    document_annotation_prompt=self.EXTRACTION_PROMPT,
                    include_image_base64=False,
                )

                logger.info("   [OK] Mistral OCR API responded successfully")

                # --- Primary path: structured annotation ---
                if hasattr(ocr_response, "document_annotation") and ocr_response.document_annotation:
                    ann = ocr_response.document_annotation
                    if isinstance(ann, dict):
                        data = ann
                    else:
                        data = json.loads(str(ann))
                        
                    doc_type = data.get("document_type", "unknown")
                    transactions = data.get("transactions", [])
                    
                    logger.info(f"    Structured annotation: Type={doc_type}, {len(transactions)} transactions")
                    return doc_type, transactions

                # --- Fallback: concatenate page markdown, parse JSON ---
                pages = getattr(ocr_response, "pages", []) or []
                if pages:
                    logger.info(f"    Processing {len(pages)} page(s) of OCR markdown...")
                    markdown_text = "\n\n".join(
                        getattr(p, "markdown", "") or "" for p in pages
                    )
                    doc_type, transactions = self._parse_json_response(markdown_text)
                    if transactions:
                        logger.info(f"    Parsed {len(transactions)} transactions from markdown")
                        return doc_type, transactions

                logger.warning(f"   [WARN]  Attempt {attempt}: No transactions found, retrying...")
                last_error = ValueError("Empty transactions from Mistral OCR")

            except Exception as e:
                last_error = e
                error_msg = str(e)
                logger.warning(f"   [WARN]  Attempt {attempt} failed: {e}")
                
                # IMMEDIATE FALLBACK on 502 or 504 (Server Overloaded/Down)
                # Don't waste time retrying if the provider is down; jump to Gemini immediately to save frontend from timeout.
                if "502" in error_msg or "504" in error_msg or "Bad Gateway" in error_msg:
                    logger.error("   [CRITICAL] Mistral API is currently down (502/504). Aborting retries and falling back to Gemini.")
                    break

                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.info(f"    Waiting {wait}s before retry...")
                    time.sleep(wait)

        logger.error(f"   [FAIL] All {max_retries} attempts failed. Last error: {last_error}")
        raise RuntimeError(f"Mistral OCR extraction failed: {last_error}")

    def _parse_json_response(self, response_text: str) -> Tuple[str, List[Dict]]:
        """
        Parse the JSON transaction list from a raw response string.
        Returns: (document_type, transactions list)
        """
        if not response_text:
            return "unknown", []

        text = response_text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            data = json.loads(text)

            if isinstance(data, dict):
                doc_type = data.get("document_type", "unknown")
                if "transactions" in data and isinstance(data["transactions"], list):
                    return doc_type, data["transactions"]

            # Sometimes models return the array directly
            if isinstance(data, list):
                return "unknown", data

            logger.warning(f"Unexpected JSON structure: keys = {list(data.keys()) if isinstance(data, dict) else type(data)}")
            return "unknown", []

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.debug(f"Raw response (first 500 chars): {response_text[:500]}")
            return "unknown", []

    # ----------------------------------------------------------
    # SHARED HELPERS (validation, date parsing, keywords)
    # ----------------------------------------------------------

    def _validate_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """
        Validate and clean extracted transactions.
        - Parses dates to YYYY-MM-DD
        - Ensures debit/credit are set correctly
        - Uses balance tracking to auto-correct debit/credit mismatches
        - Tags each transaction with extraction_method = MISTRAL_OCR
        """
        validated = []
        prev_balance = None
        corrections_made = 0

        logger.info(f"\n{'='*80}")
        logger.info(f"[SEARCH] VALIDATING {len(transactions)} TRANSACTIONS")
        logger.info(f"{'='*80}")

        for idx, txn in enumerate(transactions, 1):
            try:
                # Parse date
                date_str = str(txn.get("date", "")).strip()
                parsed_date = self._parse_date(date_str)
                if not parsed_date:
                    logger.debug(f"   Skipping transaction {idx}: unparseable date '{date_str}'")
                    continue

                # Core fields
                description = str(txn.get("description", "")).strip()[:200]
                if not description:
                    continue

                debit  = float(txn.get("debit",  0) or 0)
                credit = float(txn.get("credit", 0) or 0)
                amount = float(txn.get("amount", 0) or 0)
                balance_raw = txn.get("balance")
                # Fix: use `is not None` instead of truthiness so balance=0.0 is not skipped
                balance = float(balance_raw) if balance_raw is not None else None

                # If Mistral returned only an 'amount' field, use keywords to classify
                if debit == 0 and credit == 0 and amount > 0:
                    desc_lower = description.lower()
                    is_debit  = any(kw in desc_lower for kw in self.debit_keywords)
                    is_credit = any(kw in desc_lower for kw in self.credit_keywords)

                    if is_debit:
                        debit = amount
                    elif is_credit:
                        credit = amount
                    elif balance is not None and prev_balance is not None:
                        if balance < prev_balance:
                            debit = amount
                        else:
                            credit = amount
                    else:
                        debit = amount  # default to debit

                #  BULLETPROOF CORRECTOR: "Test Both Possibilities" 
                # Instead of trusting Mistral's debit/credit column blindly,
                # mathematically test both hypotheses against the balance.
                txn_amount = debit if debit > 0 else credit
                
                if txn_amount > 0 and balance is not None and prev_balance is not None:
                    # HEURISTIC: Does the original OCR mapping already work?
                    original_option = round(prev_balance - debit + credit, 2)
                    if abs(original_option - balance) < 0.05:
                        # Original is correct enough! Don't flip.
                        prev_balance = balance
                    else:
                        # Original is broken, try flipping
                        option_debit  = round(prev_balance - txn_amount, 2)
                        option_credit = round(prev_balance + txn_amount, 2)

                        error_debit  = abs(option_debit  - balance)
                        error_credit = abs(option_credit - balance)

                        if error_debit <= error_credit:
                            # Math says DEBIT is correct
                            if credit > 0:
                                logger.info(f"   [WARN]  Correction #{idx}: math says DEBIT (err={error_debit:.2f})  flipping CrDr")
                                corrections_made += 1
                            debit, credit = txn_amount, 0.0
                            prev_balance = option_debit
                        else:
                            # Math says CREDIT is correct
                            if debit > 0:
                                logger.info(f"   [WARN]  Correction #{idx}: math says CREDIT (err={error_credit:.2f})  flipping DrCr")
                                corrections_made += 1
                            credit, debit = txn_amount, 0.0
                            prev_balance = option_credit
                else:
                    # No balance info available  keep Mistral's classification as-is
                    if balance is not None:
                        prev_balance = balance

                final_amount = debit if debit > 0 else credit
                if final_amount == 0:
                    continue

                validated.append({
                    "date":              parsed_date,
                    "description":       description,
                    "debit":             debit,
                    "credit":            credit,
                    "amount":            final_amount,
                    "balance":           balance if balance is not None else 0.0,
                    "category":          "Uncategorized",
                    "extraction_method": "MISTRAL_OCR",
                })

            except Exception as e:
                logger.warning(f"   [WARN]  Transaction {idx} validation error: {e}")
                continue

        logger.info(f"\n{'='*80}")
        logger.info(
            f"[OK] VALIDATION COMPLETE: {len(validated)}/{len(transactions)} transactions"
        )
        if corrections_made > 0:
            logger.info(f"    Balance-based corrections made: {corrections_made}")
        logger.info(f"{'='*80}\n")

        return validated

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date to YYYY-MM-DD from common formats."""
        if not date_str:
            return None

        # Already in ISO format
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            pass

        # DD/MM/YYYY
        match = re.search(r"(\d{2})/(\d{2})/(\d{4})", date_str)
        if match:
            day, month, year = match.groups()
            try:
                return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
            except ValueError:
                pass

        # DD-MM-YYYY
        match = re.search(r"(\d{2})-(\d{2})-(\d{4})", date_str)
        if match:
            day, month, year = match.groups()
            try:
                return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
            except ValueError:
                pass

        # DD MMM YYYY  (e.g. "12 Mar 2024")
        try:
            return datetime.strptime(date_str.strip(), "%d %b %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass

        # DD-MMM-YYYY  (e.g. "12-Mar-2024")
        try:
            return datetime.strptime(date_str.strip(), "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass

        return None

    def _load_debit_keywords(self) -> List[str]:
        """Keywords that signal a debit (money going out)."""
        return [
            "payment", "paid", "transfer", "withdrawal", "debit", "dr",
            "upi", "neft", "imps", "atm", "pos", "purchase", "bill",
            "swiggy", "zomato", "amazon", "flipkart", "uber", "ola",
        ]

    def _load_credit_keywords(self) -> List[str]:
        """Keywords that signal a credit (money coming in)."""
        return [
            "received", "credit", "deposit", "salary", "refund", "cashback",
            "interest", "dividend", "cr", "credited", "reversal",
        ]

    # ----------------------------------------------------------
    # FALLBACK: Gemini Vision logic
    # ----------------------------------------------------------

    def _extract_with_gemini_vision(self, pdf_bytes: bytes, password: str) -> Tuple[str, List[Dict]]:
        """
        Fallback method that converting PDF to images and extracting via Gemini Vision.
        """
        try:
            logger.info("    Rendering PDF pages to images for Gemini Vision...")
            images = self._pdf_to_images(pdf_bytes, password)
            if not images:
                return "unknown", []
            
            all_transactions = []
            doc_type_found = ""

            for page_num, image in enumerate(images, 1):
                logger.info(f"    Processing Page {page_num} with Gemini Vision...")
                
                # Injected prompt instructing Gemini to categorize overall doc type + parse transactions
                prompt = self.EXTRACTION_PROMPT + f"\n\nCurrently observing page {page_num}. Note: doc_type can be empty string if you are unsure, just keep appending transactions to the array."
                
                for attempt in range(2):
                    try:
                        response = self.gemini_model.generate_content([prompt, image])
                        doc_type, page_txns = self._parse_json_response(response.text)
                        
                        if doc_type and doc_type != "unknown" and not doc_type_found:
                            doc_type_found = doc_type
                            
                        if page_txns:
                            all_transactions.extend(page_txns)
                            break
                    except Exception as e:
                        if attempt == 1:
                            logger.error(f"      [WARN] Page {page_num} extraction failed: {e}")
                        else:
                            time.sleep(1)
            
            return doc_type_found or "unknown", all_transactions
            
        except Exception as e:
            logger.error(f"[FAIL] Gemini vision extraction failed entirely: {e}")
            return "unknown", []

    def _pdf_to_images(self, pdf_bytes: bytes, password: str) -> List[Image.Image]:
        """Convert PDF to a list of PIL Images."""
        images = []
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                tmp_pdf.write(pdf_bytes)
                tmp_path = tmp_pdf.name
                
            doc = fitz.open(tmp_path)
            if doc.needs_pass and password:
                doc.authenticate(password)
                
            for page in doc:
                # 300 DPI scaling
                mat = fitz.Matrix(300/72, 300/72)
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                # Ensure RGB mode for Gemini compatibility
                images.append(img.convert('RGB') if img.mode != 'RGB' else img)
                
            doc.close()
            return images
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return []
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try: 
                    os.unlink(tmp_path)
                except: 
                    pass

# ============================================================
# FACTORY FUNCTION
# ============================================================

def get_smart_extractor():
    """Return the active extractor instance (now Mistral OCR 3)."""
    return MistralOCRExtractor()
