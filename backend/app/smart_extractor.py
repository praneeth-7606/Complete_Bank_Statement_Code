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
#   - TABLE_BASED  → pdfplumber (column parsing)
#   - TEXT_BASED   → Gemini text parsing
#   - IMAGE_BASED  → Gemini Vision (page-by-page images)
#   - Then validated with BalanceVerifier + TableStructureAnalyzer
# ============================================================

import io
import os
import json
import base64
import logging
import re
import time
import tempfile
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from .config import settings

logger = logging.getLogger(__name__)


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
        Mistral OCR 3 supports 'doc-as-prompt' — the document IS the context,
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
                "items": {
                    "type": "object",
                    "properties": {
                        "date":        {"type": "string", "description": "Transaction date in YYYY-MM-DD or DD/MM/YYYY format"},
                        "description": {"type": "string", "description": "Full transaction description / narration"},
                        "debit":       {"type": "number", "description": "Debit amount (money going OUT). 0 if credit."},
                        "credit":      {"type": "number", "description": "Credit amount (money coming IN). 0 if debit."},
                        "balance":     {"type": "number", "description": "Running balance after this transaction. 0 if not visible."}
                    },
                    "required": ["date", "description", "debit", "credit", "balance"]
                }
            }
        },
        "required": ["document_type", "transactions"]
    }

    EXTRACTION_PROMPT = """You are a financial document parser.
Analyze this document. First, classify its overall `document_type`.
Then, extract ALL transactions.

Rules:
1. Extract EVERY transaction — do not skip any.
2. CRITICAL - PAGE CARRYOVER: Statements often span multiple pages, but column headers (Date, Narration, Debit, Credit, Balance) may only exist on Page 1. You MUST remember the column structure from Page 1 and apply it to all subsequent pages, even if those pages have no visible headers.
3. For each transaction set EITHER debit OR credit to the transaction amount; set the other to 0.
   - DEBIT (money OUT): payments, withdrawals, ATM, UPI, purchases, transfers out, bill payments
   - CREDIT (money IN): salary, deposits, refunds, interest, cashback, transfers in, returns
4. Include the running balance if visible in the statement; otherwise set balance to 0.
5. Dates must be in YYYY-MM-DD or DD/MM/YYYY format — preserve exactly as printed.
6. Return ONLY a valid JSON object matching this schema — no markdown, no extra text:

{
  "document_type": "bank_statement | credit_card_bill | loan_statement | other",
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "Full transaction description",
      "debit": 0.00,
      "credit": 0.00,
      "balance": 0.00
    }
  ]
}"""

    # Directory where per-statement OCR logs are saved
    _LOG_DIR = Path(__file__).parent.parent / "logs" / "ocr"

    def __init__(self):
        logger.info("🔮 Initializing Mistral OCR 3 Extractor (mistral-ocr-latest)...")

        if not settings.MISTRAL_API_KEY:
            raise ValueError(
                "MISTRAL_API_KEY is not set. "
                "Add MISTRAL_API_KEY=your_key to your .env file."
            )

        try:
            from mistralai.client.sdk import Mistral
            self.client = Mistral(api_key=settings.MISTRAL_API_KEY)
            logger.info("✅ Mistral client initialised successfully")
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
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            logger.warning("GEMINI_API_KEY not set. Gemini Vision fallback will unavailable.")
            self.gemini_model = None

        logger.info("✅ Mistral OCR 3 Extractor ready (with Gemini fallback)")

    # ----------------------------------------------------------
    # PUBLIC: main entry point (same signature as old extractor)
    # ----------------------------------------------------------

    def extract_from_pdf(
        self,
        pdf_bytes: bytes,
        password: str = "",
        filename: str = "",
    ) -> List[Dict]:
        """
        Extract transactions from a PDF using Mistral OCR 3.

        Args:
            pdf_bytes: Raw PDF file bytes
            password:  PDF password if encrypted (used for pre-decryption)
            filename:  Original filename (for logging)

        Returns:
            List of validated transaction dicts with keys:
            date, description, debit, credit, amount, balance, category
        """
        try:
            logger.info("=" * 80)
            logger.info(f"🔮 MISTRAL OCR 3 WITH FAILOVER: {filename or 'statement.pdf'}")
            logger.info("=" * 80)

            start_time = time.time()

            # Step 1: Handle password-protected PDFs
            pdf_bytes = self._decrypt_pdf_if_needed(pdf_bytes, password, filename)

            # Step 2: Call Primary Method (Mistral OCR API)
            try:
                document_type, raw_transactions = self._ocr_pdf_with_mistral(pdf_bytes, filename)
                extraction_method = "MISTRAL_OCR_3"
            except Exception as e:
                logger.warning(f"⚠️ Mistral OCR extraction failed: {e}. Attempting Gemini Vision fallback...")
                raw_transactions = []
            
            # Step 2b: Fallback to Gemini Vision if Mistral failed or returned 0 transactions
            if not raw_transactions:
                logger.info("🔄 FALLBACK TRIGGERED: Using Gemini Vision for processing.")
                if not self.gemini_model:
                     raise RuntimeError("Mistral OCR failed, but no GEMINI_API_KEY is configured for fallback.")
                document_type, raw_transactions = self._extract_with_gemini_vision(pdf_bytes, password)
                extraction_method = "GEMINI_VISION_FALLBACK"

            elapsed = time.time() - start_time
            logger.info(
                f"✅ {extraction_method} returned {len(raw_transactions)} raw transactions "
                f"in {elapsed:.2f}s"
            )

            # Step 3: Validate and normalise
            validated = self._validate_transactions(raw_transactions)

            # Apply final extraction method tag
            for v in validated:
                v['extraction_method'] = extraction_method

            # Step 4: Write JSON log file for inspection
            self._write_ocr_log(
                filename=filename,
                extraction_method=extraction_method,
                document_type=document_type,
                raw_transactions=raw_transactions,
                validated_transactions=validated,
                elapsed=elapsed,
            )

            logger.info(f"✅ Extraction Complete: {len(validated)} valid transactions (Type: {document_type})")
            logger.info("=" * 80)
            return validated

        except Exception as e:
            logger.error(f"❌ Extraction failed on all attempts: {e}", exc_info=True)
            raise

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
                    "model_used":          "mistral-ocr-latest" if "MISTRAL" in extraction_method else "gemini-2.0-flash",
                    "processing_time_sec": round(elapsed, 3),
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

            logger.info(f"📝 OCR log saved → {log_path}")

        except Exception as e:
            # Log writing should never break the main extraction flow
            logger.warning(f"⚠️  Could not write OCR log: {e}")

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

            logger.info("🔓 Decrypting password-protected PDF before OCR...")
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
                logger.info("✅ PDF decrypted successfully")
                return decrypted_bytes
            finally:
                os.unlink(tmp_path)

        except ImportError:
            logger.warning(
                "PyMuPDF (fitz) not installed — sending encrypted PDF to Mistral. "
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
        logger.info("📡 Sending PDF to Mistral OCR API (mistral-ocr-latest)...")

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
                logger.info(f"   🔄 Attempt {attempt}/{max_retries}...")

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

                logger.info("   ✅ Mistral OCR API responded successfully")

                # --- Primary path: structured annotation ---
                if hasattr(ocr_response, "document_annotation") and ocr_response.document_annotation:
                    ann = ocr_response.document_annotation
                    if isinstance(ann, dict):
                        data = ann
                    else:
                        data = json.loads(str(ann))
                        
                    doc_type = data.get("document_type", "unknown")
                    transactions = data.get("transactions", [])
                    
                    logger.info(f"   📋 Structured annotation: Type={doc_type}, {len(transactions)} transactions")
                    return doc_type, transactions

                # --- Fallback: concatenate page markdown, parse JSON ---
                pages = getattr(ocr_response, "pages", []) or []
                if pages:
                    logger.info(f"   📄 Processing {len(pages)} page(s) of OCR markdown...")
                    markdown_text = "\n\n".join(
                        getattr(p, "markdown", "") or "" for p in pages
                    )
                    doc_type, transactions = self._parse_json_response(markdown_text)
                    if transactions:
                        logger.info(f"   📋 Parsed {len(transactions)} transactions from markdown")
                        return doc_type, transactions

                logger.warning(f"   ⚠️  Attempt {attempt}: No transactions found, retrying...")
                last_error = ValueError("Empty transactions from Mistral OCR")

            except Exception as e:
                last_error = e
                logger.warning(f"   ⚠️  Attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.info(f"   ⏳ Waiting {wait}s before retry...")
                    time.sleep(wait)

        logger.error(f"   ❌ All {max_retries} attempts failed. Last error: {last_error}")
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
        logger.info(f"🔍 VALIDATING {len(transactions)} TRANSACTIONS")
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
                balance = float(balance_raw) if balance_raw else None

                # If Mistral returned only an 'amount' field, use keywords to classify
                if debit == 0 and credit == 0 and amount > 0:
                    desc_lower = description.lower()
                    is_debit  = any(kw in desc_lower for kw in self.debit_keywords)
                    is_credit = any(kw in desc_lower for kw in self.credit_keywords)

                    if is_debit:
                        debit = amount
                    elif is_credit:
                        credit = amount
                    elif balance and prev_balance:
                        if balance < prev_balance:
                            debit = amount
                        else:
                            credit = amount
                    else:
                        debit = amount  # default to debit

                # Balance-based debit/credit correction
                if balance and prev_balance and (debit > 0 or credit > 0):
                    balance_change = balance - prev_balance

                    if balance_change < 0 and credit > 0:
                        logger.info(
                            f"   ⚠️  Correction #{idx}: balance ↓ but marked credit → switching to debit"
                        )
                        debit, credit = credit, 0.0
                        corrections_made += 1

                    elif balance_change > 0 and debit > 0:
                        logger.info(
                            f"   ⚠️  Correction #{idx}: balance ↑ but marked debit → switching to credit"
                        )
                        credit, debit = debit, 0.0
                        corrections_made += 1

                final_amount = debit if debit > 0 else credit
                if final_amount == 0:
                    continue

                validated.append({
                    "date":              parsed_date,
                    "description":       description,
                    "debit":             debit,
                    "credit":            credit,
                    "amount":            final_amount,
                    "balance":           balance if balance else 0.0,
                    "category":          "Uncategorized",
                    "extraction_method": "MISTRAL_OCR",
                })

                if balance:
                    prev_balance = balance

            except Exception as e:
                logger.warning(f"   ⚠️  Transaction {idx} validation error: {e}")
                continue

        logger.info(f"\n{'='*80}")
        logger.info(
            f"✅ VALIDATION COMPLETE: {len(validated)}/{len(transactions)} transactions"
        )
        if corrections_made > 0:
            logger.info(f"   🔧 Balance-based corrections made: {corrections_made}")
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
            logger.info("   📸 Rendering PDF pages to images for Gemini Vision...")
            images = self._pdf_to_images(pdf_bytes, password)
            if not images:
                return "unknown", []
            
            all_transactions = []
            doc_type_found = ""

            for page_num, image in enumerate(images, 1):
                logger.info(f"   🤖 Processing Page {page_num} with Gemini Vision...")
                
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
                            logger.error(f"      ⚠️ Page {page_num} extraction failed: {e}")
                        else:
                            time.sleep(1)
            
            return doc_type_found or "unknown", all_transactions
            
        except Exception as e:
            logger.error(f"❌ Gemini vision extraction failed entirely: {e}")
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


# ============================================================
# ============================================================
# OLD CODE — COMMENTED OUT FOR REFERENCE
# Methodology: Auto-classify PDF → pdfplumber / Gemini text / Gemini Vision
# ============================================================
# ============================================================

# import tempfile
# import fitz  # PyMuPDF
# import pdfplumber
# from PIL import Image
# import google.generativeai as genai
# from .table_structure_analyzer import TableStructureAnalyzer
# from .balance_verifier import BalanceVerifier
#
#
# class SmartBankStatementExtractor:
#     """
#     SMART EXTRACTOR - Automatically classifies PDFs and uses the best method:
#
#     PDF Types:
#     1. TABLE-BASED (DLB, etc.) → Use pdfplumber (100% accurate for tables)
#     2. TEXT-BASED (HDFC, ICICI) → Use Gemini text parsing
#     3. IMAGE-BASED (Scanned) → Use VLM/OCR
#
#     This ensures EVERY PDF type gets the best extraction method!
#     """
#
#     def __init__(self):
#         logger.info("🧠 Initializing SMART Extractor (Auto-Classification)...")
#         genai.configure(api_key=settings.GEMINI_API_KEY)
#         self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
#         self.debit_keywords = self._load_debit_keywords()
#         self.credit_keywords = self._load_credit_keywords()
#         self.table_analyzer = TableStructureAnalyzer()
#         self.balance_verifier = BalanceVerifier()
#         logger.info("✅ SMART Extractor initialized")
#
#     def _log_structure_analysis(self, structure_result):
#         logger.info(f"   📊 Table Detection Results:")
#         logger.info(f"      - Column Headers Found: {structure_result.column_headers}")
#         logger.info(f"      - Has Separate Debit Column: {'✅ YES' if structure_result.has_debit_column else '❌ NO'}")
#         logger.info(f"      - Has Separate Credit Column: {'✅ YES' if structure_result.has_credit_column else '❌ NO'}")
#         if not structure_result.is_complete_table:
#             logger.info(f"      - Has Balance Column: {'✅ YES' if structure_result.has_balance_column else '❌ NO'}")
#         logger.info(f"      - Table Structure: {'COMPLETE' if structure_result.is_complete_table else 'INCOMPLETE'}")
#
#     def _extract_opening_balance(self, pdf_bytes: bytes, password: str):
#         try:
#             text = self._extract_text(pdf_bytes, password)
#             patterns = [
#                 r'opening\s+balance[:\s]+[₹Rs.\s]*([0-9,]+\.?[0-9]*)',
#                 r'balance\s+brought\s+forward[:\s]+[₹Rs.\s]*([0-9,]+\.?[0-9]*)',
#                 r'previous\s+balance[:\s]+[₹Rs.\s]*([0-9,]+\.?[0-9]*)',
#             ]
#             text_lower = text.lower()
#             for pattern in patterns:
#                 match = re.search(pattern, text_lower)
#                 if match:
#                     return float(match.group(1).replace(',', ''))
#             return None
#         except Exception as e:
#             logger.debug(f"Could not extract opening balance: {e}")
#             return None
#
#     def _load_debit_keywords(self):
#         return ['payment', 'paid', 'transfer', 'withdrawal', 'debit', 'dr',
#                 'upi', 'neft', 'imps', 'atm', 'pos', 'purchase', 'bill',
#                 'swiggy', 'zomato', 'amazon', 'flipkart', 'uber', 'ola']
#
#     def _load_credit_keywords(self):
#         return ['received', 'credit', 'deposit', 'salary', 'refund', 'cashback',
#                 'interest', 'dividend', 'cr', 'credited', 'reversal']
#
#     def extract_from_pdf(self, pdf_bytes: bytes, password: str = "", filename: str = ""):
#         try:
#             logger.info("=" * 80)
#             logger.info(f"🔍 ANALYZING TABLE STRUCTURE: {filename if filename else 'statement.pdf'}")
#             logger.info("=" * 80)
#             structure_result = self.table_analyzer.analyze_structure(pdf_bytes, password)
#             self._log_structure_analysis(structure_result)
#
#             if structure_result.is_complete_table:
#                 method = "PDFPLUMBER"
#                 logger.info(f"\n   ✅ SELECTED METHOD: PDFPLUMBER")
#                 logger.info(f"      Reason: {structure_result.reason}")
#                 try:
#                     transactions = self._extract_with_pdfplumber(pdf_bytes, password)
#                     if not transactions:
#                         transactions = self._extract_with_gemini_text(pdf_bytes, password)
#                         method = "GEMINI_TEXT_FALLBACK"
#                         if not transactions:
#                             transactions = self._extract_with_gemini_vision(pdf_bytes, password)
#                             method = "GEMINI_VISION_FALLBACK"
#                 except Exception as e:
#                     logger.error(f"      ❌ PDFPlumber extraction failed: {e}")
#                     transactions = self._extract_with_gemini_text(pdf_bytes, password)
#                     method = "GEMINI_TEXT_FALLBACK"
#                     if not transactions:
#                         transactions = self._extract_with_gemini_vision(pdf_bytes, password)
#                         method = "GEMINI_VISION_FALLBACK"
#                 validated = self._validate_transactions(transactions)
#             else:
#                 method = "VLM"
#                 logger.info(f"\n   ✅ SELECTED METHOD: VLM (Gemini Vision)")
#                 transactions = self._extract_with_gemini_vision(pdf_bytes, password)
#                 if structure_result.has_balance_column and structure_result.requires_balance_verification:
#                     try:
#                         opening_balance = self._extract_opening_balance(pdf_bytes, password)
#                         corrected_transactions, verification_result = self.balance_verifier.verify_and_correct(
#                             transactions, opening_balance
#                         )
#                         transactions = corrected_transactions
#                     except Exception as e:
#                         logger.warning(f"      ⚠️ Balance verification failed: {e}")
#                 validated = self._validate_transactions(transactions)
#
#             logger.info(f"\n   ✅ Extraction Complete: {len(validated)} transactions")
#             logger.info("=" * 80)
#             return validated
#         except Exception as e:
#             logger.error(f"❌ Smart extraction failed: {e}", exc_info=True)
#             raise
#
#     def _classify_pdf(self, pdf_bytes: bytes, password: str) -> str:
#         tmp_path = None
#         try:
#             with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
#                 tmp_pdf.write(pdf_bytes)
#                 tmp_path = tmp_pdf.name
#             with pdfplumber.open(tmp_path, password=password) as pdf:
#                 first_page = pdf.pages[0]
#                 tables = first_page.extract_tables()
#                 if tables and len(tables) > 0:
#                     for table in tables:
#                         if len(table) > 3:
#                             header = str(table[0]).lower() if table[0] else ""
#                             if any(keyword in header for keyword in ['date', 'description', 'amount', 'debit', 'credit', 'balance']):
#                                 return "TABLE_BASED"
#                 text = first_page.extract_text()
#                 if text and len(text.strip()) > 100:
#                     if re.search(r'\d{2}/\d{2}/\d{4}', text):
#                         if re.search(r'\d+\.\d{2}', text):
#                             return "TEXT_BASED"
#             return "IMAGE_BASED"
#         except Exception as e:
#             logger.warning(f"   ⚠️ Classification failed: {e}, defaulting to TEXT_BASED")
#             return "TEXT_BASED"
#         finally:
#             if tmp_path and os.path.exists(tmp_path):
#                 try: os.unlink(tmp_path)
#                 except: pass
#
#     def _extract_with_pdfplumber(self, pdf_bytes: bytes, password: str):
#         transactions = []
#         tmp_path = None
#         try:
#             logger.info("   📊 PDFPLUMBER Extraction Starting...")
#             with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
#                 tmp_pdf.write(pdf_bytes)
#                 tmp_path = tmp_pdf.name
#             with pdfplumber.open(tmp_path, password=password) as pdf:
#                 for page_num, page in enumerate(pdf.pages, 1):
#                     tables = page.extract_tables()
#                     for table_idx, table in enumerate(tables):
#                         if not table or len(table) < 2:
#                             continue
#                         header_row = None
#                         data_start_idx = 0
#                         for idx, row in enumerate(table[:5]):
#                             row_str = ' '.join([str(cell).lower() if cell else '' for cell in row])
#                             if 'date' in row_str or 'description' in row_str:
#                                 header_row = [str(cell).lower().strip() if cell else '' for cell in row]
#                                 data_start_idx = idx + 1
#                                 break
#                         if not header_row:
#                             continue
#                         date_col    = self._find_column(header_row, ['date', 'txn date', 'transaction date'])
#                         desc_col    = self._find_column(header_row, ['description', 'particulars', 'narration', 'details'])
#                         debit_col   = self._find_column(header_row, ['debit', 'withdrawal', 'payment', 'dr'])
#                         credit_col  = self._find_column(header_row, ['credit', 'deposit', 'receipt', 'cr'])
#                         balance_col = self._find_column(header_row, ['balance', 'closing balance', 'bal'])
#                         amount_col  = self._find_column(header_row, ['amount', 'transaction amount'])
#                         for row in table[data_start_idx:]:
#                             try:
#                                 if not row or len(row) < 2:
#                                     continue
#                                 date_str = str(row[date_col]).strip() if date_col is not None and date_col < len(row) else ""
#                                 if not date_str or date_str == 'None' or 'total' in date_str.lower():
#                                     continue
#                                 desc = str(row[desc_col]).strip() if desc_col is not None and desc_col < len(row) else ""
#                                 if not desc or desc == 'None':
#                                     continue
#                                 debit = credit = amount = balance = 0.0
#                                 if debit_col is not None and debit_col < len(row):
#                                     s = str(row[debit_col]).strip()
#                                     if s and s not in ('None', '-'):
#                                         debit = float(s.replace(',','').replace('₹','').replace('Rs','').strip())
#                                 if credit_col is not None and credit_col < len(row):
#                                     s = str(row[credit_col]).strip()
#                                     if s and s not in ('None', '-'):
#                                         credit = float(s.replace(',','').replace('₹','').replace('Rs','').strip())
#                                 if amount_col is not None and amount_col < len(row):
#                                     s = str(row[amount_col]).strip()
#                                     if s and s not in ('None', '-'):
#                                         amount = float(s.replace(',','').replace('₹','').replace('Rs','').strip())
#                                 if balance_col is not None and balance_col < len(row):
#                                     s = str(row[balance_col]).strip()
#                                     if s and s not in ('None', '-'):
#                                         balance = float(s.replace(',','').replace('₹','').replace('Rs','').strip())
#                                 final_amount = debit if debit > 0 else (credit if credit > 0 else (amount if amount > 0 else 0))
#                                 if final_amount == 0:
#                                     continue
#                                 transactions.append({
#                                     'date': date_str, 'description': desc,
#                                     'debit': debit, 'credit': credit,
#                                     'amount': final_amount, 'balance': balance,
#                                     'extraction_method': 'PDFPLUMBER'
#                                 })
#                             except Exception as e:
#                                 logger.debug(f"         Skipping row: {e}")
#             logger.info(f"   ✅ PDFPLUMBER extracted {len(transactions)} transactions")
#             return transactions
#         except Exception as e:
#             logger.error(f"   ❌ PDFPLUMBER extraction failed: {e}")
#             return []
#         finally:
#             if tmp_path and os.path.exists(tmp_path):
#                 try: os.unlink(tmp_path)
#                 except: pass
#
#     def _find_column(self, header, keywords):
#         for idx, cell in enumerate(header):
#             cell_lower = cell.lower() if cell else ''
#             for keyword in keywords:
#                 if keyword in cell_lower:
#                     return idx
#         return None
#
#     def _extract_with_gemini_text(self, pdf_bytes: bytes, password: str):
#         try:
#             text = self._extract_text(pdf_bytes, password)
#             if not text or len(text.strip()) < 50:
#                 return []
#             max_chunk_size = 30000
#             all_transactions = []
#             if len(text) > max_chunk_size:
#                 chunks = self._split_text_intelligently(text, max_chunk_size)
#                 for chunk_num, chunk in enumerate(chunks, 1):
#                     all_transactions.extend(self._extract_transactions_from_text_chunk(chunk, chunk_num))
#             else:
#                 all_transactions = self._extract_transactions_from_text_chunk(text, 1)
#             for txn in all_transactions:
#                 txn['extraction_method'] = 'GEMINI_TEXT'
#             return all_transactions
#         except Exception as e:
#             logger.error(f"Gemini text extraction failed: {e}")
#             return []
#
#     def _split_text_intelligently(self, text: str, max_size: int):
#         chunks = []
#         current_chunk = ""
#         for line in text.split('\n'):
#             if len(current_chunk) + len(line) > max_size and current_chunk:
#                 chunks.append(current_chunk)
#                 current_chunk = line + '\n'
#             else:
#                 current_chunk += line + '\n'
#         if current_chunk:
#             chunks.append(current_chunk)
#         return chunks
#
#     def _extract_transactions_from_text_chunk(self, text_chunk: str, chunk_num: int):
#         try:
#             prompt = f"""Analyze this bank statement text (chunk {chunk_num}) and extract ALL transactions.
# Return ONLY valid JSON:
# {{"transactions": [{{"date": "YYYY-MM-DD","description": "...","debit": 0.00,"credit": 0.00,"balance": 0.00}}]}}
# **BANK STATEMENT TEXT:**
# {text_chunk[:30000]}
# **RETURN ONLY JSON:**"""
#             response = self.gemini_model.generate_content(prompt)
#             return self._extract_json(response.text) or []
#         except Exception as e:
#             logger.error(f"Error extracting from chunk {chunk_num}: {e}")
#             return []
#
#     def _extract_with_gemini_vision(self, pdf_bytes: bytes, password: str):
#         try:
#             images = self._pdf_to_images(pdf_bytes, password)
#             if not images:
#                 return []
#             all_transactions = []
#             for page_num, image in enumerate(images, 1):
#                 prompt = f"""Extract ALL transactions from page {page_num}.
# Return ONLY JSON: {{"transactions": [{{"date": "YYYY-MM-DD","description": "...","debit": 0.00,"credit": 0.00,"balance": 0.00}}]}}"""
#                 for attempt in range(2):
#                     try:
#                         response = self.gemini_model.generate_content([prompt, image])
#                         page_txns = self._extract_json(response.text)
#                         if page_txns:
#                             all_transactions.extend(page_txns)
#                             break
#                     except Exception as e:
#                         if attempt == 1:
#                             logger.error(f"Page {page_num} failed: {e}")
#             for txn in all_transactions:
#                 txn['extraction_method'] = 'GEMINI_VISION'
#             return all_transactions
#         except Exception as e:
#             logger.error(f"Gemini vision extraction failed: {e}")
#             return []
#
#     def _verify_transaction_completeness(self, transactions, total_pages):
#         avg = len(transactions) / total_pages if total_pages > 0 else 0
#         if avg < 3:
#             logger.warning("⚠️ LOW TRANSACTION COUNT — possible missing transactions")
#         elif avg > 50:
#             logger.warning("⚠️ HIGH TRANSACTION COUNT — possible duplicates")
#
#     def _extract_text(self, pdf_bytes: bytes, password: str) -> str:
#         tmp_path = None
#         try:
#             with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
#                 tmp_pdf.write(pdf_bytes)
#                 tmp_path = tmp_pdf.name
#             doc = fitz.open(tmp_path)
#             if doc.needs_pass:
#                 doc.authenticate(password)
#             text = "".join(page.get_text() for page in doc)
#             doc.close()
#             return text
#         finally:
#             if tmp_path and os.path.exists(tmp_path):
#                 try: os.unlink(tmp_path)
#                 except: pass
#
#     def _pdf_to_images(self, pdf_bytes: bytes, password: str):
#         images = []
#         tmp_path = None
#         try:
#             with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
#                 tmp_pdf.write(pdf_bytes)
#                 tmp_path = tmp_pdf.name
#             doc = fitz.open(tmp_path)
#             if doc.needs_pass:
#                 doc.authenticate(password)
#             for page in doc:
#                 mat = fitz.Matrix(300/72, 300/72)
#                 pix = page.get_pixmap(matrix=mat)
#                 img = Image.open(io.BytesIO(pix.tobytes("png")))
#                 images.append(img.convert('RGB') if img.mode != 'RGB' else img)
#             doc.close()
#             return images
#         finally:
#             if tmp_path and os.path.exists(tmp_path):
#                 try: os.unlink(tmp_path)
#                 except: pass
#
#     def _extract_json(self, response_text: str):
#         try:
#             text = response_text.strip()
#             if text.startswith('```'):
#                 lines = text.split('\n')[1:]
#                 if lines and lines[-1].strip() == '```':
#                     lines = lines[:-1]
#                 text = '\n'.join(lines)
#             data = json.loads(text)
#             if isinstance(data, dict) and 'transactions' in data:
#                 return data['transactions']
#             if isinstance(data, list):
#                 return data
#             return []
#         except json.JSONDecodeError:
#             return []
#
#     def _validate_transactions(self, transactions):
#         # (same logic as MistralOCRExtractor._validate_transactions above)
#         pass  # full implementation was identical — see new class above
#
#     def _parse_date(self, date_str: str):
#         # (same logic as MistralOCRExtractor._parse_date above)
#         pass  # full implementation was identical — see new class above
#
#
# # OLD factory function
# # def get_smart_extractor():
# #     return SmartBankStatementExtractor()
