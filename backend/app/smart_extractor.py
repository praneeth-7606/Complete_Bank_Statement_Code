# app/smart_extractor.py
# ============================================================
# EXTRACTION METHODOLOGY: Configured Mistral OCR model
# ============================================================
# NEW APPROACH (ACTIVE):
#   - Sends base64-encoded PDF directly to the configured Mistral OCR model
#   - Mistral Document AI reads every page and returns structured transactions
#     in bounded, overlapping page groups. Annotations use provider-side models.
#   - Decimal validation preserves source values and blocks inconsistent output
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
import uuid
import hashlib
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
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from .config import settings
from .finance import money
from .extraction_validation import normalize_ocr_rows, validate_extraction, ExtractionNeedsReview
from .observability import observe_external_llm, observed_stage
from . import models, agents
from .vector_store_pinecone import PineconeVectorStore
from .log_streamer import log_streamer

logger = logging.getLogger(__name__)


def _is_quota_error(message) -> bool:
    """True when an exception/message indicates provider quota / rate limits."""
    if not message:
        return False
    lowered = str(message).lower()
    markers = (
        "429",
        "rate limit",
        "rate_limit",
        "quota",
        "resourceexhausted",
        "resource exhausted",
        "too many requests",
        "gemini_quota",
        "resource has been exhausted",
    )
    return any(marker in lowered for marker in markers)


def _repair_common_json_issues(text: str) -> str:
    """Best-effort repair for common LLM JSON mistakes (trailing commas etc.)."""
    repaired = text.strip()
    # Remove trailing commas before } or ]
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    # Normalize smart quotes that models sometimes emit
    repaired = repaired.replace("\u201c", '"').replace("\u201d", '"')
    repaired = repaired.replace("\u2018", "'").replace("\u2019", "'")
    return repaired

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
    validation_report: Optional[Dict]



# ============================================================
# NEW EXTRACTOR: Mistral OCR
# ============================================================

class MistralOCRExtractor:
    """
    NEW EXTRACTOR using the configured Mistral OCR model.

    Flow:
        1. Base64-encode the PDF bytes (handles both digital & scanned PDFs)
        2. Send to Mistral OCR API with a strict JSON schema prompt
           via the 'document_annotation_format' / chat-completion approach
        3. Mistral returns structured transactions JSON directly
        4. Validate & normalise with _validate_transactions helper

    Why single-step:
        Mistral OCR supports 'doc-as-prompt'  the document IS the context,
        and a prompt drives the model to output JSON directly without a 
        second LLM call.
    """

    # ============================================================
    # SPECIALIZED SCHEMAS FOR DIFFERENT DOCUMENT TYPES
    # ============================================================
    
    # Schema for Credit Card Bills
    CREDIT_CARD_SCHEMA = {
        "type": "object",
        "properties": {
            "document_type": {"type": "string", "enum": ["credit_card_bill"]},
            "card_details": {
                "type": "object",
                "properties": {
                    "card_number_last4": {"type": "string", "description": "Last 4 digits of card number"},
                    "credit_limit": {"type": "number", "description": "Total credit limit"},
                    "available_credit": {"type": "number", "description": "Available credit"},
                    "statement_date": {"type": "string", "description": "Statement generation date"},
                    "due_date": {"type": "string", "description": "Payment due date"},
                    "minimum_due": {"type": "number", "description": "Minimum amount due"},
                    "total_due": {"type": "number", "description": "Total outstanding amount"}
                }
            },
            "transactions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "description": {"type": "string", "description": "Merchant name and transaction details"},
                        "debit": {"type": "number", "description": "Amount charged (purchases, fees, interest)"},
                        "credit": {"type": "number", "description": "Payments, refunds, cashback"},
                        "balance": {"type": "number"}
                    },
                    "required": ["date", "description", "debit", "credit", "balance"]
                }
            }
        },
        "required": ["document_type", "card_details", "transactions"]
    }

    # Schema for Loan Statements
    LOAN_SCHEMA = {
        "type": "object",
        "properties": {
            "document_type": {"type": "string", "enum": ["loan_statement"]},
            "loan_details": {
                "type": "object",
                "properties": {
                    "loan_account_number": {"type": "string"},
                    "loan_type": {"type": "string", "description": "Home Loan, Personal Loan, Auto Loan, etc."},
                    "principal_amount": {"type": "number", "description": "Original loan amount"},
                    "outstanding_principal": {"type": "number", "description": "Remaining principal"},
                    "interest_rate": {"type": "number", "description": "Annual interest rate percentage"},
                    "tenure_months": {"type": "number", "description": "Total loan tenure in months"},
                    "emi_amount": {"type": "number", "description": "Monthly EMI amount"},
                    "next_due_date": {"type": "string"}
                }
            },
            "transactions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "description": {"type": "string", "description": "EMI payment, principal, interest breakdown"},
                        "principal_paid": {"type": "number", "description": "Principal component of EMI"},
                        "interest_paid": {"type": "number", "description": "Interest component of EMI"},
                        "debit": {"type": "number", "description": "Total EMI deducted"},
                        "credit": {"type": "number", "description": "Prepayments or refunds"},
                        "balance": {"type": "number", "description": "Outstanding principal after payment"}
                    },
                    "required": ["date", "description", "debit", "credit", "balance"]
                }
            }
        },
        "required": ["document_type", "loan_details", "transactions"]
    }

    # Schema for EMI/Installment Statements
    EMI_SCHEMA = {
        "type": "object",
        "properties": {
            "document_type": {"type": "string", "enum": ["emi_statement"]},
            "emi_details": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "Product purchased on EMI"},
                    "total_amount": {"type": "number", "description": "Total product cost"},
                    "down_payment": {"type": "number", "description": "Initial down payment"},
                    "emi_amount": {"type": "number", "description": "Monthly installment amount"},
                    "tenure_months": {"type": "number", "description": "Total EMI tenure"},
                    "interest_rate": {"type": "number", "description": "Interest rate if applicable"},
                    "outstanding_amount": {"type": "number"}
                }
            },
            "transactions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "description": {"type": "string", "description": "EMI installment number and details"},
                        "debit": {"type": "number", "description": "EMI amount paid"},
                        "credit": {"type": "number", "description": "Refunds or adjustments"},
                        "balance": {"type": "number", "description": "Remaining amount to be paid"}
                    },
                    "required": ["date", "description", "debit", "credit", "balance"]
                }
            }
        },
        "required": ["document_type", "emi_details", "transactions"]
    }

    # JSON schema we instruct Mistral to fill per page / document (BANK STATEMENTS - DEFAULT)
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
                        "balance":     {"type": ["number", "null"], "description": "Running balance after this transaction; null if missing or unreadable. Preserve the decimal point; remove grouping commas only."}
                    },
                    "required": ["date", "description", "debit", "credit", "balance"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["document_type", "transactions"],
        "additionalProperties": False
    }

    # ============================================================
    # SPECIALIZED PROMPTS FOR DIFFERENT DOCUMENT TYPES
    # ============================================================
    
    CREDIT_CARD_PROMPT = """You are an expert Credit Card Statement analyzer.
Extract ALL transactions from this credit card bill with 100% accuracy.

CRITICAL INSTRUCTIONS:
1. CARD DETAILS: Extract card number (last 4 digits), credit limit, available credit, statement date, due date, minimum due, and total due from the summary section.
2. TRANSACTION TYPES: Identify purchases, cash advances, fees, interest charges, payments, and refunds.
3. MERCHANT DETAILS: Capture full merchant names and transaction descriptions.
4. DEBIT = Charges (purchases, fees, interest). CREDIT = Payments, refunds, cashback.
5. INTERNATIONAL TRANSACTIONS: Note currency conversions if present.
6. EXHAUSTIVE: Extract every single transaction from all pages.
7. BALANCE: Running balance after each transaction.

Return ONLY valid JSON matching the credit_card_bill schema. No markdown."""

    LOAN_PROMPT = """You are an expert Loan Statement analyzer.
Extract ALL loan payment details with complete accuracy.

CRITICAL INSTRUCTIONS:
1. LOAN DETAILS: Extract loan account number, loan type (Home/Personal/Auto), principal amount, outstanding principal, interest rate, tenure, EMI amount, next due date.
2. EMI BREAKDOWN: For each payment, extract principal component and interest component separately.
3. PREPAYMENTS: Identify any prepayments or part-payments separately from regular EMIs.
4. DEBIT = EMI payments, processing fees. CREDIT = Refunds, interest rebates.
5. BALANCE = Outstanding principal after each payment.
6. EXHAUSTIVE: Extract every payment record from all pages.
7. DATES: Capture exact payment dates and due dates.

Return ONLY valid JSON matching the loan_statement schema. No markdown."""

    EMI_PROMPT = """You are an expert EMI/Installment Statement analyzer.
Extract ALL EMI payment records with complete accuracy.

CRITICAL INSTRUCTIONS:
1. EMI DETAILS: Extract product name, total cost, down payment, EMI amount, tenure, interest rate, outstanding amount.
2. INSTALLMENT TRACKING: Number each EMI payment (EMI 1/12, EMI 2/12, etc.).
3. PAYMENT STATUS: Mark each installment as paid/pending/overdue if indicated.
4. DEBIT = EMI installments paid, late fees. CREDIT = Refunds, cancellations.
5. BALANCE = Remaining amount to be paid after each installment.
6. EXHAUSTIVE: Extract every installment record from all pages.
7. ZERO-COST EMI: If zero-cost EMI, note interest rate as 0%.

Return ONLY valid JSON matching the emi_statement schema. No markdown."""

    # Default prompt for Bank Statements
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
        logger.info(f"[INIT] Initializing Mistral OCR Extractor ({settings.MISTRAL_OCR_MODEL})...")

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
            self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
        else:
            logger.warning("GEMINI_API_KEY not set. Gemini Vision fallback will unavailable.")
            self.gemini_model = None

        if settings.ZAI_API_KEY:
            self.zai_vision_model = ChatOpenAI(
                model=settings.ZAI_VISION_MODEL,
                api_key=settings.ZAI_API_KEY,
                base_url=settings.ZAI_BASE_URL,
                temperature=0,
                max_retries=0,
            )
        else:
            self.zai_vision_model = None

        logger.info("[OK] Mistral OCR extractor ready (Gemini Vision -> Z.AI Vision fallback)")

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
            # Open from memory - decrypted PDFs are already unrestricted.
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            redactions_made = 0
            extractable_characters = 0
            
            for page in doc:
                text = page.get_text()
                extractable_characters += len(text.strip())
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
                
            if extractable_characters == 0 and not settings.ALLOW_UNREDACTED_OCR:
                doc.close()
                raise ValueError(
                    "This image-only PDF cannot be safely redacted before hosted OCR. "
                    "Set ALLOW_UNREDACTED_OCR=true only after approving the provider data policy."
                )
            if redactions_made > 0:
                logger.info(f"[MASK] Successfully redacted {redactions_made} PII instances from PDF.")
            else:
                logger.info("[MASK] No PII patterns found to redact; PDF forwarded as-is.")
            masked_bytes = doc.tobytes()
            doc.close()
            return masked_bytes
            
        except Exception as e:
            if settings.ALLOW_UNREDACTED_OCR:
                logger.warning("[MASK] PDF masking failed; explicit unredacted OCR opt-in is enabled: %s", e)
                return pdf_bytes
            logger.error("[MASK] PDF masking failed closed: %s", e)
            raise RuntimeError(f"PDF could not be safely redacted before hosted OCR: {e}") from e
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

        async def node_mask(state: ProcessingState) -> ProcessingState:
            logger.info("   [MASK] [2/11] NODE: PII redaction gate (Deterministic)...")
            t_start = time.time()
            # Provider data policy: by default the ORIGINAL decrypted PDF goes
            # to OCR (redaction would strip counterparty names from UPI lines
            # and hurt extraction). Descriptions sent to every LLM stage are
            # still masked in node_verify. Set OCR_MASK_PII_BEFORE_SEND=true
            # to visually redact phone/account/UPI/email spans pre-OCR instead.
            if settings.OCR_MASK_PII_BEFORE_SEND:
                state["masked_pdf"] = await asyncio.to_thread(
                    self._mask_pdf_bytes, state["file_bytes"]
                )
                logger.info("   [MASK] PII redaction applied before OCR (policy: redact).")
            else:
                state["masked_pdf"] = state["file_bytes"]
                logger.info("   [MASK] Sending original PDF to OCR (policy: accuracy-first; LLM stages get masked text).")
            state["timing"]["mask"] = time.time() - t_start
            return state

        async def node_ocr_primary(state: ProcessingState) -> ProcessingState:
            logger.info("   [OCR] [3/11] NODE: Extracting with Mistral OCR (Multi-Page Context)...")
            t_start = time.time()
            try:
                # Optimized: Send whole PDF to Mistral to preserve header context across pages
                import fitz
                ocr_bytes = state.get("masked_pdf") or state["file_bytes"]
                doc = fitz.open(stream=ocr_bytes, filetype="pdf")
                logger.info(f"      -> Processing all {len(doc)} pages together for context preservation.")
                doc.close()

                # ROUTING LOGIC: Use specialized extraction for non-bank statements
                doc_type = state.get("document_type", "bank_statement")
                
                if doc_type in ["credit_card_bill", "loan_statement", "emi_statement"]:
                    logger.info(f"   [ROUTER] Detected {doc_type} - Using SPECIALIZED extraction agent")
                    res = await asyncio.to_thread(
                        self._ocr_pdf_with_mistral_specialized,
                        ocr_bytes,
                        state["file_path"],
                        doc_type
                    )
                    state["extraction_method"] = f"MISTRAL_OCR_3_SPECIALIZED_{doc_type.upper()}"
                else:
                    logger.info(f"   [ROUTER] Detected {doc_type} - Using STANDARD bank statement extraction")
                    res = await asyncio.to_thread(
                        self._ocr_pdf_with_mistral,
                        ocr_bytes,
                        state["file_path"]
                    )
                    state["extraction_method"] = "MISTRAL_OCR_3_SEQUENTIAL"
                
                doc_type, txns = res
                if txns:
                    state["raw_ocr_output"] = {"transactions": txns}
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

        async def node_ocr_fallback(state: ProcessingState) -> ProcessingState:
            logger.info("   [FALLBACK] Vision fallback chain (Gemini quota-skip -> Z.AI -> deterministic text)...")
            t_start = time.time()
            fallback_chain = [
                ("GEMINI_VISION_FALLBACK", self._extract_with_gemini_vision, bool(self.gemini_model)),
                ("ZAI_GLM_VISION_FALLBACK", self._extract_with_zai_vision, bool(self.zai_vision_model)),
                ("DETERMINISTIC_PDF_TEXT", self._extract_with_deterministic_pdf_text, True),
            ]
            skip_gemini = False
            for method, extractor, enabled in fallback_chain:
                if not enabled:
                    continue
                if method == "GEMINI_VISION_FALLBACK" and skip_gemini:
                    continue
                try:
                    logger.info("   [FALLBACK] Trying %s...", method)
                    password = state.get("password") or ""
                    doc_type, txns = await asyncio.to_thread(extractor,
                        state.get("masked_pdf") or state["file_bytes"],
                        password,
                    )
                    if txns:
                        state["raw_ocr_output"] = {"transactions": txns}
                        state["extraction_method"] = method
                        logger.info("   [SUCCESS] %s returned %d transactions", method, len(txns))
                        break
                    logger.warning("   [FALLBACK] %s returned 0 transactions", method)
                    state["errors"].append(f"{method} returned 0 transactions.")
                except Exception as e:
                    err = str(e)
                    state["errors"].append(f"{method} Error: {err}")
                    if method == "GEMINI_VISION_FALLBACK" and _is_quota_error(err):
                        skip_gemini = True
                        logger.warning(
                            "   [FALLBACK] Gemini quota/rate limit exhausted - "
                            "skipping Gemini, going straight to Z.AI."
                        )
                    else:
                        logger.warning("   [FALLBACK] %s failed: %s", method, err)
            else:
                state["errors"].append("All OCR fallbacks returned no transactions.")
                logger.error("   [FAIL] All OCR fallbacks exhausted with no transactions.")
            
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
                summary = getattr(raw_txns, "summary", None)
                normalized_txns, corrections = normalize_ocr_rows(raw_txns)
                report = validate_extraction(normalized_txns, self._parse_date, summary)
                report["normalization_corrections"] = corrections
                report['evidence'] = getattr(raw_txns, 'evidence', {})
                report["issues"].extend(getattr(raw_txns, "coverage", []))
                if report["issues"]:
                    report["status"] = "needs_review"
                try:
                    from .observability import current_trace
                    trace = current_trace()
                    if trace:
                        balance_checks = int(report.get("balance_checks", 0) or 0)
                        balance_matches = int(report.get("balance_matches", 0) or 0)
                        trace.record_evaluation(
                            "extraction_consistency",
                            1.0 if report["status"] == "checks_passed" else 0.0,
                            report["status"] == "checks_passed",
                            {"retained_count": report.get("retained_count", 0), "issues": len(report.get("issues", []))},
                        )
                        if balance_checks:
                            trace.record_evaluation(
                                "running_balance_consistency",
                                balance_matches / balance_checks,
                                balance_matches == balance_checks,
                                {"matches": balance_matches, "checks": balance_checks},
                            )
                except Exception:
                    logger.debug("Unable to record extraction evaluation", exc_info=True)
                validated = report["transactions"]
                
                masker = getattr(self, "masker", None)
                if not masker:
                    from .data_masker import DataMasker
                    masker = DataMasker()
                    self.masker = masker
                
                for v in validated:
                    # ``mask_transaction`` extracts only allow-listed public
                    # merchant labels locally, then redacts the narration.
                    # It never retains personal UPI IDs or free-form names.
                    v.update(masker.mask_transaction(v))
                    v['extraction_method'] = state["extraction_method"]
                    v['document_type'] = state["document_type"]
                    
                state["cleaned_transactions"] = validated
                state["validation_report"] = report
                if report["status"] == "needs_review":
                    raise ExtractionNeedsReview(report)
                logger.info(f"      -> Verified {len(validated)} transactions.")
            except ExtractionNeedsReview:
                raise
            except Exception as e:
                state["errors"].append(f"Verification Error: {str(e)}")
                raise
            
            state["timing"]["verify"] = time.time() - t_start
            return state

        async def node_categorize(state: ProcessingState) -> ProcessingState:
            logger.info("   [CAT] [7/11] NODE: Categorization (LLM-First Structured Output)...")
            t_start = time.time()
            from copy import deepcopy
            from .evaluation import categorization_integrity, publish
            original = deepcopy(state["cleaned_transactions"])
            if not state["cleaned_transactions"]:
                state["timing"]["categorize"] = 0
                return state
            try:
                cat_agent = agents.CategorizationAgent()
                categorized = await cat_agent.categorize_transactions(
                    state["cleaned_transactions"], 
                    user_id=state.get("user_id"),
                    user_name=state.get("user_name", "User"),
                    streaming_id=state.get("streaming_id"),
                    corrections=state.get("corrections") or [],
                )
                state["categorized_transactions"] = categorized
            except Exception as e:
                logger.error(f"Categorization Node Error: {e}")
                state["errors"].append(f"Categorization Error: {e}")
                # Maintain chain even if categorization fails
                for tx in state["cleaned_transactions"]:
                    tx["category"] = "Others"
                state["categorized_transactions"] = state["cleaned_transactions"]
            
            checks = categorization_integrity(original, state["categorized_transactions"])
            publish(checks)
            if not checks[0]["passed"]:
                raise RuntimeError("Categorization changed financial fields; persistence blocked")
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
                        amount=money(tx.get("amount", 0)),
                        debit=money(tx.get("debit", 0)),
                        credit=money(tx.get("credit", 0)),
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
            
            if raw_data and raw_data.get("transactions"):
                logger.info(f"    ROUTING: Mistral Successful ({len(raw_data.get('transactions', []))} txns). Jumping to Verification.")
                return "verify"
            
            logger.warning(f"    ROUTING: Mistral Incomplete (method={method}). Engaging Gemini Fallback.")
            return "fallback"

        # 4. Compile the Graph (Sync Phase: Extraction + Reasoning)
        workflow = StateGraph(ProcessingState)

        workflow.add_node("analyze", observed_stage("document_analysis")(node_analyze))
        workflow.add_node("mask", observed_stage("masking")(node_mask))
        workflow.add_node("mistral", observed_stage("ocr_primary")(node_ocr_primary))
        workflow.add_node("gemini", observed_stage("ocr_fallback")(node_ocr_fallback))
        workflow.add_node("verify", observed_stage("extraction_validation")(node_verify))
        workflow.add_node("categorize", observed_stage("categorization")(node_categorize))
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

        # insights, db, vector -> durable worker via post_processing.persist_statement_and_enqueue()

        app = workflow.compile()

        # 5. Invoke Sync Pipeline (Hot-Path)
        # Hosted OCR is non-deterministic: the same statement can parse cleanly
        # on one call and return broken tables on the next. On validation
        # failure, retry the whole extraction with fresh state (bounded).
        # The gate below is unchanged: only checks_passed data can proceed.
        def _fresh_state():
            return ProcessingState(
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
                validation_report=None,
                timing={}
            )

        best_report, best_error = None, None
        final_state = None
        max_attempts = 1 + 2  # first try + 2 bounded retries
        for attempt in range(1, max_attempts + 1):
            try:
                final_state = await app.ainvoke(_fresh_state())
                best_report = None
                break
            except Exception as e:
                from .extraction_validation import ExtractionNeedsReview as _ENR
                if not isinstance(e, _ENR):
                    raise
                report = getattr(e, "report", {}) or {}
                n_issues = len(report.get("issues", []))
                logger.warning(
                    f"   [RETRY] Extraction attempt {attempt}/{max_attempts} needs review "
                    f"({n_issues} issues).{' Retrying OCR...' if attempt < max_attempts else ' No attempts left.'}"
                )
                if best_report is None or n_issues < len(best_report.get("issues", [])):
                    best_report, best_error = report, e
                if attempt >= max_attempts:
                    raise best_error
                if streaming_id:
                    await log_streamer.add_log(
                        streaming_id,
                        f"[RETRY] OCR output failed validation ({n_issues} issues). "
                        f"Re-reading document (attempt {attempt + 1}/{max_attempts})...",
                        "warning", 60)

        try:
            assert final_state is not None
            
            # Verified transactions are durable before the API reports success.
            from .post_processing import persist_statement_and_enqueue
            await persist_statement_and_enqueue(final_state)

            if streaming_id:
                await log_streamer.add_log(streaming_id, "[OK] Transactions verified and saved.", "success", 85)
                await log_streamer.add_log(streaming_id, "[QUEUE] Insights and vector indexing queued safely.", "info", 90)
                # Terminal success marker so SSE clients close cleanly.
                await log_streamer.add_log(
                    streaming_id,
                    "[COMPLETE] Extraction pipeline finished successfully.",
                    "complete",
                    100,
                )
            
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
            "validation_report": final_state.get("validation_report"),
            "processing_time": time.time() - start_time
        }

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
                    "model_used":          settings.MISTRAL_OCR_MODEL if "MISTRAL" in extraction_method else settings.GEMINI_MODEL,
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
            password = ""

        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning(
                "PyMuPDF (fitz) not installed - cannot decrypt PDF. "
                "Install with: pip install pymupdf"
            )
            return pdf_bytes

        logger.info(f"[DECRYPT] Checking PDF encryption for: {filename}")
        try:
            # Prefer stream open (no temp file). Fall back to temp file only
            # if stream open fails for exotic PDFs.
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            except Exception:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = tmp.name
                try:
                    doc = fitz.open(tmp_path)
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

            try:
                if doc.needs_pass:
                    if not password or not doc.authenticate(password):
                        # Fail loudly: returning encrypted bytes causes masking
                        # to crash later with a confusing PyMuPDF error.
                        raise ValueError(f"Incorrect password for PDF: {filename}")
                    logger.info(f"[DECRYPT] Password accepted for {filename}")

                import io as _io
                buffer = _io.BytesIO()
                # Always write a fully unrestricted copy so downstream
                # open()/mask/OCR steps never re-hit encryption checks.
                try:
                    doc.save(buffer, encryption=fitz.PDF_ENCRYPT_NONE, garbage=4, deflate=True)
                except TypeError:
                    # Older PyMuPDF without encryption kwarg
                    doc.save(buffer)
                decrypted_bytes = buffer.getvalue()
                logger.info(f"[DECRYPT] PDF decrypted successfully ({len(decrypted_bytes)} bytes)")
                return decrypted_bytes
            finally:
                doc.close()

        except ValueError:
            # Incorrect password - re-raise so the user gets a clear error.
            raise
        except Exception as e:
            logger.error(f"[DECRYPT] Failed to decrypt PDF {filename}: {e}")
            raise RuntimeError(
                f"Could not decrypt PDF '{filename}'. "
                f"Check that the password is correct and the file is not corrupt."
            ) from e

    def _ocr_pdf_with_mistral_specialized(self, pdf_bytes: bytes, filename: str, document_type: str) -> Tuple[str, List[Dict]]:
        """
        SPECIALIZED EXTRACTION AGENT: Routes to type-specific Mistral OCR prompts.
        
        This method is called ONLY for non-bank-statement documents (credit cards, loans, EMIs).
        It uses specialized JSON schemas and prompts optimized for each document type.
        
        Args:
            pdf_bytes: PDF file bytes
            filename: Original filename
            document_type: One of: credit_card_bill, loan_statement, emi_statement
            
        Returns:
            (document_type, transactions_with_metadata)
        """
        logger.info(f"[SPECIALIZED] Using type-specific extraction for: {document_type}")
        
        # Select schema and prompt based on document type
        schema_map = {
            "credit_card_bill": (self.CREDIT_CARD_SCHEMA, self.CREDIT_CARD_PROMPT, "CreditCardBill"),
            "loan_statement": (self.LOAN_SCHEMA, self.LOAN_PROMPT, "LoanStatement"),
            "emi_statement": (self.EMI_SCHEMA, self.EMI_PROMPT, "EMIStatement")
        }
        
        if document_type not in schema_map:
            logger.warning(f"Unknown document type: {document_type}. Falling back to generic extraction.")
            return self._ocr_pdf_with_mistral(pdf_bytes, filename)
        
        schema, prompt, schema_name = schema_map[document_type]
        
        # Encode PDF as base64
        b64_pdf = base64.standard_b64encode(pdf_bytes).decode("utf-8")
        document_data_uri = f"data:application/pdf;base64,{b64_pdf}"
        
        logger.info(f"   Using {schema_name} schema with specialized prompt")
        logger.info(f"   PDF size: {len(pdf_bytes) / 1024:.1f} KB")
        
        # Build annotation format with specialized schema
        annotation_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "schema": schema,
                "strict": True,
            },
        }
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"   [ATTEMPT] {attempt}/{max_retries} - Specialized extraction...")
                
                ocr_response = self.client.ocr.process(
                    model=settings.MISTRAL_OCR_MODEL,
                    document={
                        "type": "document_url",
                        "document_url": document_data_uri,
                    },
                    document_annotation_format=annotation_format,
                    document_annotation_prompt=prompt,
                    include_image_base64=False,
                )
                
                logger.info("   [OK] Specialized extraction successful")
                
                # Parse response
                if hasattr(ocr_response, "document_annotation") and ocr_response.document_annotation:
                    ann = ocr_response.document_annotation
                    data = ann if isinstance(ann, dict) else json.loads(ann)
                    
                    # Extract metadata and transactions
                    transactions = data.get("transactions", [])
                    
                    # Enrich transactions with document-specific metadata
                    if document_type == "credit_card_bill" and "card_details" in data:
                        card_details = data["card_details"]
                        for txn in transactions:
                            txn["card_last4"] = card_details.get("card_number_last4")
                            txn["statement_date"] = card_details.get("statement_date")
                            txn["document_metadata"] = card_details
                    
                    elif document_type == "loan_statement" and "loan_details" in data:
                        loan_details = data["loan_details"]
                        for txn in transactions:
                            txn["loan_account"] = loan_details.get("loan_account_number")
                            txn["loan_type"] = loan_details.get("loan_type")
                            txn["emi_amount"] = loan_details.get("emi_amount")
                            txn["document_metadata"] = loan_details
                    
                    elif document_type == "emi_statement" and "emi_details" in data:
                        emi_details = data["emi_details"]
                        for txn in transactions:
                            txn["product_name"] = emi_details.get("product_name")
                            txn["emi_amount"] = emi_details.get("emi_amount")
                            txn["tenure_months"] = emi_details.get("tenure_months")
                            txn["document_metadata"] = emi_details
                    
                    logger.info(f"   [SUCCESS] Extracted {len(transactions)} transactions with metadata")
                    return (document_type, transactions)
                
                else:
                    logger.warning("   [WARN] No structured annotation in response")
                    
            except Exception as e:
                logger.error(f"   [ERROR] Attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return (document_type, [])

    def _ocr_pdf_with_mistral(self, pdf_bytes: bytes, filename: str) -> Tuple[str, List[Dict]]:
        from .mistral_table_extractor import extract_tables
        return extract_tables(
            self.client, pdf_bytes, settings.MISTRAL_OCR_MODEL,
            timeout_ms=int(settings.OCR_TIMEOUT_SECONDS * 1000),
            concurrency=settings.OCR_MAX_CONCURRENCY,
            page_limit=settings.OCR_TABLE_PAGE_LIMIT,
            max_retries=settings.OCR_MAX_RETRIES,
        )

    def _parse_json_response(self, response_text: str) -> Tuple[str, List[Dict]]:
        """
        Parse the JSON transaction list from a raw response string.
        Returns: (document_type, transactions list)

        Raises ValueError when the payload is non-empty but unparseable so the
        caller can fall through to the next OCR provider instead of treating a
        broken response as "0 transactions".
        """
        if not response_text or not response_text.strip():
            return "unknown", []

        text = response_text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        candidates = [text]
        # Extract first balanced {...} or [...] if prose wraps the JSON.
        for open_ch, close_ch in (("{", "}"), ("[", "]")):
            start = text.find(open_ch)
            end = text.rfind(close_ch)
            if start != -1 and end > start:
                candidates.append(text[start:end + 1])

        last_error: Optional[json.JSONDecodeError] = None
        for candidate in candidates:
            for variant in (candidate, _repair_common_json_issues(candidate)):
                try:
                    data = json.loads(variant)
                except json.JSONDecodeError as e:
                    last_error = e
                    continue

                if isinstance(data, dict):
                    doc_type = data.get("document_type", "unknown")
                    if "transactions" in data and isinstance(data["transactions"], list):
                        return doc_type, data["transactions"]
                    # Some models nest under "data"
                    nested = data.get("data")
                    if isinstance(nested, dict) and isinstance(nested.get("transactions"), list):
                        return nested.get("document_type", doc_type), nested["transactions"]

                # Sometimes models return the array directly
                if isinstance(data, list):
                    return "unknown", data

                logger.warning(
                    "[PARSE] Unexpected JSON structure: keys = %s",
                    list(data.keys()) if isinstance(data, dict) else type(data),
                )
                return "unknown", []

        # Non-empty response that we could not parse - fail loudly so fallbacks run.
        snippet = response_text[:300].replace("\n", " ")
        logger.error(
            "[PARSE] JSON decode failed: %s | raw[:300]=%r",
            last_error, snippet,
        )
        if last_error:
            raise ValueError(f"JSON decode error: {last_error}") from last_error
        raise ValueError("Model response was not valid JSON")

    # ----------------------------------------------------------
    # SHARED HELPERS (validation, date parsing, keywords)
    # ----------------------------------------------------------

    def _validate_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Normalize without dropping rows or repairing financial evidence."""
        from .extraction_validation import validate_extraction
        return validate_extraction(transactions, self._parse_date)["transactions"]

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date to YYYY-MM-DD from common formats."""
        if not date_str:
            return None
        for pattern in ("%d/%m/%y", "%d-%m-%y", "%d %b %y", "%d-%b-%y", "%d %B %Y"):
            try:
                return datetime.strptime(date_str.strip(), pattern).strftime("%Y-%m-%d")
            except ValueError:
                pass

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
                        with observe_external_llm("gemini", settings.GEMINI_MODEL, kind="ocr_vision") as span:
                            response = self.gemini_model.generate_content([prompt, image])
                            span.response = response
                        doc_type, page_txns = self._parse_json_response(response.text)
                        
                        if doc_type and doc_type != "unknown" and not doc_type_found:
                            doc_type_found = doc_type
                            
                        if page_txns:
                            all_transactions.extend(page_txns)
                            break
                    except Exception as e:
                        err = str(e)
                        # Free-tier Gemini is often permanently quota-blocked.
                        # Do not burn retries - skip straight to Z.AI.
                        if _is_quota_error(err):
                            logger.warning(
                                "      [FALLBACK] Gemini quota/rate limit hit on page "
                                f"{page_num}: {err}. Skipping Gemini entirely."
                            )
                            raise RuntimeError(
                                f"GEMINI_QUOTA_EXHAUSTED: {err}"
                            ) from e
                        if attempt == 1:
                            logger.error(f"      [WARN] Page {page_num} extraction failed: {e}")
                        else:
                            time.sleep(1)
            
            return doc_type_found or "unknown", all_transactions
            
        except Exception as e:
            if _is_quota_error(str(e)):
                logger.warning(f"[FALLBACK] Gemini vision skipped (quota): {e}")
            else:
                logger.error(f"[FAIL] Gemini vision extraction failed entirely: {e}")
            return "unknown", []

    def _extract_with_zai_vision(self, pdf_bytes: bytes, password: str) -> Tuple[str, List[Dict]]:
        """Extract page images through Z.AI's OpenAI-compatible vision endpoint."""
        if not self.zai_vision_model:
            return "unknown", []
        images = self._pdf_to_images(pdf_bytes, password)
        all_transactions: List[Dict] = []
        doc_type_found = ""
        for page_num, image in enumerate(images, 1):
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85, optimize=True)
            image_uri = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
            base_prompt = self.EXTRACTION_PROMPT + f"\n\nThis is page {page_num}. Return only JSON."
            last_parse_error: Optional[Exception] = None
            for attempt in range(2):
                prompt = base_prompt if attempt == 0 else (
                    base_prompt + "\nCRITICAL: Respond with STRICT valid JSON only. "
                    "No markdown, no commentary, no trailing text."
                )
                try:
                    with observe_external_llm("zai", settings.ZAI_VISION_MODEL, kind="ocr_vision") as span:
                        response = self.zai_vision_model.invoke([
                            HumanMessage(content=[
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": image_uri}},
                            ])
                        ])
                        span.response = response
                    content = response.content
                    if isinstance(content, list):
                        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
                    doc_type, page_txns = self._parse_json_response(str(content))
                    last_parse_error = None
                    break
                except ValueError as e:
                    last_parse_error = e
                    logger.warning(
                        "[PARSE] Z.AI page %d attempt %d failed JSON parse: %s",
                        page_num, attempt + 1, e,
                    )
                except Exception as e:
                    last_parse_error = e
                    logger.warning(
                        "[FALLBACK] Z.AI vision page %d attempt %d error: %s",
                        page_num, attempt + 1, e,
                    )
                    break
            if last_parse_error is not None:
                raise RuntimeError(
                    f"ZAI_GLM_VISION_FALLBACK failed on page {page_num}: {last_parse_error}"
                ) from last_parse_error
            if doc_type and doc_type != "unknown" and not doc_type_found:
                doc_type_found = doc_type
            all_transactions.extend(page_txns)
        return doc_type_found or "unknown", all_transactions

    def _extract_with_deterministic_pdf_text(self, pdf_bytes: bytes, password: str) -> Tuple[str, List[Dict]]:
        """Conservative fallback for text-based statements when all vision APIs fail.

        Handles multi-line table rows where SI, date, description, amount and
        balance each appear on their own line (e.g. Union Bank statements).
        Debit/credit direction is inferred from running-balance deltas, with
        narration keywords as a tie-breaker for the first row.
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.needs_pass:
            if not password or not doc.authenticate(password):
                doc.close()
                raise ValueError("Incorrect password for PDF")

        date_only = re.compile(r"^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*$")
        money_only = re.compile(r"^\s*â‚¹?\s*([\d,]+\.\d{2})\s*(Cr|Dr)?\.?\s*$", re.IGNORECASE)
        si_only = re.compile(r"^\s*\d{1,4}\s*$")

        all_lines: List[str] = []
        for page in doc:
            all_lines.extend((page.get_text("text") or "").splitlines())
        doc.close()

        # A pure date line starts a row; collect until the balance (Cr/Dr)
        # suffix, the next date, or an SI index that follows money.
        parsed_rows: List[Dict] = []
        i = 0
        while i < len(all_lines):
            date_match = date_only.match(all_lines[i])
            if not date_match:
                i += 1
                continue
            raw_date = date_match.group(1)
            i += 1
            # Skip an SI index sitting between the prior row and the date.
            if i < len(all_lines) and si_only.match(all_lines[i]) and not date_only.match(all_lines[i]):
                # Only skip if this integer is not itself starting money context.
                # Dates are already consumed; bare integers before description are SI.
                if i + 1 >= len(all_lines) or not money_only.match(all_lines[i + 1] or ""):
                    # SI appears before the date in some layouts and after in others;
                    # here the date was just consumed, so a following integer is
                    # unlikely part of this row's description â€” leave it for desc
                    # collection below unless it clearly begins the next SI+date pair.
                    pass
            desc_parts: List[str] = []
            money_parts: List[Tuple[float, bool, str]] = []
            while i < len(all_lines):
                line = all_lines[i]
                if date_only.match(line):
                    break
                money_match = money_only.match(line)
                if money_match:
                    value = float(money_match.group(1).replace(",", ""))
                    has_suffix = bool(money_match.group(2))
                    money_parts.append((value, has_suffix, line.strip()))
                    i += 1
                    if has_suffix:
                        break
                    continue
                if money_parts and si_only.match(line):
                    break
                if not money_parts and not desc_parts and si_only.match(line):
                    i += 1
                    continue
                if line.strip():
                    desc_parts.append(line.strip())
                i += 1
            if not money_parts:
                continue

            balance_val: Optional[float] = None
            amount_vals: List[float] = []
            for idx, (val, has_suffix, _raw) in enumerate(money_parts):
                if has_suffix and idx == len(money_parts) - 1:
                    balance_val = val
                else:
                    amount_vals.append(val)
            if balance_val is None:
                balance_val = money_parts[-1][0]
                amount_vals = [m[0] for m in money_parts[:-1]]
            nonzero = [a for a in amount_vals if a > 0]
            if not nonzero:
                continue
            amount = nonzero[0] if len(nonzero) == 1 else sum(nonzero)

            parsed_date = self._parse_date(raw_date.replace("/", "-"))
            if not parsed_date:
                parts = re.split(r"[/-]", raw_date)
                if len(parts) == 3:
                    day, month, year = parts
                    if len(year) == 2:
                        year = "20" + year
                    parsed_date = self._parse_date(f"{day.zfill(2)}/{month.zfill(2)}/{year}")
            if not parsed_date:
                continue

            description = " ".join(desc_parts).strip(" -|\t")[:200] or "Transaction"
            parsed_rows.append({
                "date": parsed_date,
                "description": description,
                "amount": amount,
                "balance": balance_val,
            })

        transactions: List[Dict] = []
        prev_balance: Optional[float] = None
        for row in parsed_rows:
            amount = row["amount"]
            balance_val = row["balance"]
            description = row["description"]
            is_credit: Optional[bool] = None
            if prev_balance is not None and balance_val is not None:
                if abs(balance_val - prev_balance - amount) < 0.011:
                    is_credit = True
                elif abs(prev_balance - balance_val - amount) < 0.011:
                    is_credit = False
                elif balance_val > prev_balance:
                    is_credit = True
                elif balance_val < prev_balance:
                    is_credit = False
            if is_credit is None:
                lowered = description.lower()
                if "/cr/" in lowered or "credit" in lowered or "deposit" in lowered or "salary" in lowered:
                    is_credit = True
                elif "/dr/" in lowered or "debit" in lowered or "withdrawal" in lowered:
                    is_credit = False
                else:
                    is_credit = any(k in lowered for k in self.credit_keywords)
            transactions.append({
                "date": row["date"],
                "description": description,
                "debit": 0.0 if is_credit else amount,
                "credit": amount if is_credit else 0.0,
                "amount": amount,
                "balance": balance_val if balance_val is not None else 0.0,
            })
            prev_balance = balance_val if balance_val is not None else prev_balance

        logger.info(
            "[FALLBACK] DETERMINISTIC_PDF_TEXT extracted %d transactions from multi-line text",
            len(transactions),
        )
        return "bank_statement", transactions

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
    """Return the active Mistral OCR extractor instance."""
    return MistralOCRExtractor()
