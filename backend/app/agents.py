# app/agents.py - LangGraph Agentic Implementati

# app/agents.py (Updated with a more robust prompt for TransactionStructuringAgent)
import google.generativeai as genai
import json
import re
import datetime
import asyncio
from typing import List, Dict, Any
import logging
from .config import settings
from calendar import monthrange

logger = logging.getLogger(__name__)
genai.configure(api_key=settings.GEMINI_API_KEY)

def extract_json_from_response(text: str) -> Any:
    """Extracts a JSON object or array from a string, handling markdown code blocks."""
    match = re.search(r"```json\s*([\s\S]*?)\s*```|(\[.*\]|\{.*\})", text, re.DOTALL)
    if not match: return None
    json_str = match.group(1) or match.group(2)
    try: return json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning("Failed to decode JSON from response string: %s", json_str)
        return None

class BaseAgent:
    """A base class for generative AI agents with rate limiting and retry logic."""
    def __init__(self, model_name="gemini-2.5-flash"):
        # Use Gemini 2.5 Flash - Fastest text model with 4,000 RPM rate limits
        self.model = genai.GenerativeModel(model_name)
        self.max_retries = 3
        self.base_delay = 2  # seconds
    
    async def _get_json_response(self, prompt: str) -> Any:
        """Get JSON response with automatic retry on rate limit errors."""
        for attempt in range(self.max_retries):
            try:
                response = await self.model.generate_content_async(prompt)
                if response and hasattr(response, 'text') and response.text:
                    return extract_json_from_response(response.text)
                else:
                    logger.warning("Gemini API returned an empty response for the prompt.")
                    return None
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a rate limit error (429)
                if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                    # Extract retry delay from error message if available
                    import re
                    retry_match = re.search(r'retry in (\d+)', error_str, re.IGNORECASE)
                    if retry_match:
                        retry_delay = int(retry_match.group(1))
                    else:
                        # Exponential backoff
                        retry_delay = self.base_delay * (2 ** attempt)
                    
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Rate limit hit. Retrying in {retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded after {self.max_retries} attempts")
                        raise Exception(f"Gemini API rate limit exceeded. Please wait a few minutes and try again.")
                
                # Other errors
                logger.error(f"Gemini API Error for {self.__class__.__name__}: {e}", exc_info=True)
                return None
        
        return None

class TransactionStructuringAgent(BaseAgent):
    """Analyzes transaction lines with support for both mini-batch and full-batch processing."""
    
    async def structure_single_transaction(self, transaction_line: str) -> Dict:
        """
        Structure a single transaction (fallback for error cases).
        
        Args:
            transaction_line: Single transaction line text
            
        Returns:
            Structured transaction dictionary
        """
        result = await self.structure_transactions_in_batch([transaction_line])
        return result[0] if result else {}
    
    async def structure_mini_batch(self, transaction_lines: List[str]) -> List[Dict]:
        """
        Structure a mini-batch of 2-5 transactions for optimal accuracy/speed balance.
        
        This method is optimized for:
        - High accuracy (focused prompt, small context)
        - Better speed than individual processing
        - Lower hallucination risk than large batches
        
        Args:
            transaction_lines: List of 2-5 transaction lines (recommended)
            
        Returns:
            List of structured transaction dictionaries
        """
        return await self.structure_transactions_in_batch(transaction_lines)
    
    async def structure_transactions_in_batch(self, transaction_lines: List[str]) -> List[Dict]:
        all_lines_text = "\n".join(transaction_lines)
        
        # --- BALANCED PROMPT: Accuracy + Speed ---
        prompt = f"""You are an expert at parsing Indian bank transactions. Extract data from UPI/NEFT/IMPS statements.

**CRITICAL RULES:**
1. Output MUST be a valid JSON array with one object per transaction
2. NEVER skip any transaction - parse ALL {len(transaction_lines)} lines provided
3. For amounts: Payment OUT = debit field (credit=0), Payment IN = credit field (debit=0)
4. If you can't find amount, use 0.0 for both credit and debit
5. Extract date as YYYY-MM-DD format
6. Create clear description from transaction details

**JSON FORMAT (STRICT):**
```json
[
  {{
    "date": "YYYY-MM-DD",
    "description": "Clear description",
    "credit": 0.0,
    "debit": 0.0,
    "amount": 0.0,
    "category": "Category"
  }}
]
```

**EXAMPLES:**

Input: "01/02/2025 Upi Txn: /450473312079-Swiggy/Payment From Phonepe/Swiggystores@Icici 150.50 5000.00"
Output: {{"date":"2025-02-01","description":"Swiggy Food Order","credit":0.0,"debit":150.50,"amount":150.50,"category":"Food & Dining"}}

Input: "02/02/2025 Upi Txn: /079918416532-Ponnaluri Manorama/Payment From Phonepe/Rao.Vav@Ybl 500.00 5500.00"
Output: {{"date":"2025-02-02","description":"Received from Ponnaluri Manorama","credit":500.00,"debit":0.0,"amount":500.00,"category":"Personal Transfer"}}

**TRANSACTIONS TO PARSE ({len(transaction_lines)} total - parse ALL):**
{all_lines_text}

**YOUR JSON ARRAY (must have {len(transaction_lines)} objects):**"""
        structured_data = await self._get_json_response(prompt)
        if isinstance(structured_data, list): return structured_data
        logger.warning("TransactionStructuringAgent (Batch) failed to return a valid JSON array. Returning empty list.")
        return []

class CategorizationAgent(BaseAgent):
    """Adds a category to each transaction with support for mini-batch processing - OPTIMIZED FOR SPEED."""
    
    def __init__(self, model_name="gemini-2.5-flash"):
        # Use Gemini 2.5 Flash - Fastest categorization with 4,000 RPM rate limits
        super().__init__(model_name)
        # Initialize DataMasker for sensitive data protection
        from .data_masker import DataMasker
        self.masker = DataMasker()
    
    async def categorize_single_transaction(self, transaction: Dict, corrections: List[Dict]) -> Dict:
        """
        Categorize a single transaction (fallback for error cases).
        
        Args:
            transaction: Single transaction dictionary
            corrections: List of user corrections for learning
            
        Returns:
            Categorized transaction dictionary
        """
        result = await self.categorize_transactions([transaction], corrections)
        return result[0] if result else transaction
    
    async def categorize_mini_batch(self, transactions: List[Dict], corrections: List[Dict]) -> List[Dict]:
        """
        Categorize a mini-batch of 2-5 transactions for optimal accuracy/speed balance.
        
        Args:
            transactions: List of 2-5 transactions (recommended)
            corrections: List of user corrections for learning
            
        Returns:
            List of categorized transactions
        """
        return await self.categorize_transactions(transactions, corrections)
    
    async def categorize_transactions(self, transactions: List[Dict], corrections: List[Dict]) -> List[Dict]:
        """
        Categorize transactions using ONLY AI (Gemini 2.5 Flash).
        
        SECURITY: Masks sensitive data before sending to LLM.
        
        Args:
            transactions: List of transactions to categorize
            corrections: List of user corrections for learning
            
        Returns:
            List of categorized transactions (with original unmasked data)
        """
        # SECURITY LAYER: Mask sensitive data before sending to LLM
        logger.info(f"🔒 Masking {len(transactions)} transactions before LLM categorization...")
        masked_transactions = self.masker.mask_transactions_for_llm(transactions)
        logger.info(f"✅ Masking complete - sending masked data to LLM")
        
        # Analyze name frequency to help with Personal vs Other Transfer distinction
        name_frequency = {}
        for txn in masked_transactions:
            desc = txn.get('description', '')
            # Extract names from UPI transactions (between slashes)
            if 'UPI' in desc.upper():
                parts = desc.split('/')
                for part in parts:
                    part = part.strip()
                    # Look for name-like patterns (2-3 words, mostly letters)
                    if len(part) > 3 and any(c.isalpha() for c in part):
                        name_frequency[part] = name_frequency.get(part, 0) + 1
        
        # Identify recurring names (appear 2+ times)
        recurring_names = [name for name, count in name_frequency.items() if count >= 2]
        recurring_names_text = f"\n\n**RECURRING NAMES (likely Personal Transfer):**\n{', '.join(recurring_names[:10])}" if recurring_names else ""
        
        # Security audit logging
        try:
            from .logging_config import log_masking_operation, log_llm_request
            log_masking_operation(len(transactions), "categorization")
            log_llm_request(masked=True, data_type="transactions", context="categorization")
        except ImportError:
            pass  # Logging config not available
        
        corrections_text = f"\n\nPrevious user corrections to learn from:\n{json.dumps(corrections, indent=2)}" if corrections else ""
        
        prompt = f"""Categorize Indian bank transactions accurately. Return JSON array with category field added.

**Available Categories:**
- Food & Dining
- Travel
- Other Transfer
- Personal Transfer
- Dividends
- Shopping
- Bills & Utilities
- Entertainment
- Income
- Investments
- Healthcare
- Education
- Others

**CRITICAL CATEGORIZATION RULES:**

1. **Personal Transfer** (Money to/from YOUR OWN accounts or people you personally know):
   - Transfers with YOUR name or family member names
   - Transfers between your own bank accounts
   - Money sent to/from close family and friends
   - Look for familiar names that appear frequently
   - **Key indicators**: Same name appearing multiple times, family names, your own name
   - **Examples**:
     * "M BHARAD/HDFC/bharadwaj9674@" → Personal Transfer (your account/family)
     * Transfers with names that appear in multiple transactions → Personal Transfer

2. **Other Transfer** (Money to/from OTHER people - not you or your family):
   - UPI transactions to people you don't know personally
   - One-time transfers to unfamiliar names
   - Generic transfers to strangers or acquaintances
   - Names that appear only once or rarely
   - **Key indicators**: Unfamiliar names, one-time transactions, random people
   - **Examples**:
     * "VEDAGI RI/DLXB/630308760@yb" → Other Transfer (unknown person)
     * Transfers to names you don't recognize → Other Transfer

3. **Income** (Money received):
   - Salary credits
   - Refunds
   - Cashback
   - Any credit transaction that's not a transfer from a person

4. **Food & Dining**:
   - Restaurants, cafes, food delivery
   - Swiggy, Zomato, Uber Eats
   - Hotel dining, food courts

5. **Shopping**:
   - Online shopping (Amazon, Flipkart, etc.)
   - Retail stores
   - E-commerce platforms

6. **Bills & Utilities**:
   - Electricity, water, gas
   - Mobile recharge, DTH
   - Internet bills

7. **Travel**:
   - Taxi, bus, train, flight bookings
   - Fuel/petrol
   - Travel apps (Uber, Ola, etc.)

8. **Dividends**:
   - Stock dividends
   - "Net Txn with Achc:" transactions
   - Investment returns

9. **Others**:
   - Anything that doesn't fit above categories

**DECISION LOGIC FOR TRANSFERS:**
1. Check if the name appears multiple times in the transaction list → Personal Transfer (your contacts)
2. Check if it's a one-time/rare name → Other Transfer (stranger)
3. Check if it's a business name → appropriate business category

**SPECIFIC EXAMPLES TO FOLLOW:**
- "M BHARAD" (appears frequently) → Personal Transfer
- "VEDAGI RI" (appears once/rarely) → Other Transfer
- "Swiggy" → Food & Dining
- "Amazon" → Shopping

**REMEMBER:**
- Personal Transfer = YOUR people (family, friends, your own accounts)
- Other Transfer = OTHER people (strangers, one-time contacts)
- Look at frequency of names to determine familiarity{corrections_text}

**Transactions to categorize (sensitive data masked for security):**
{json.dumps(masked_transactions, indent=2)}{recurring_names_text}

**Return ONLY a valid JSON array with category added to each transaction:**"""
        
        try:
            logger.info(f"🏷️  Categorizing {len(transactions)} transactions with Gemini 2.5 Flash...")
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config={
                    'temperature': 0.1,
                    'top_p': 0.95,
                    'top_k': 40,
                    'max_output_tokens': 16384,  # Increased for large batches
                },
                request_options={'timeout': 300}  # 5 minute timeout (increased from 2)
            )
            
            # Extract text from response
            if response and hasattr(response, 'text') and response.text:
                logger.info(f"   Raw AI response length: {len(response.text)} characters")
                categorized_data = extract_json_from_response(response.text)
                
                if isinstance(categorized_data, list) and len(categorized_data) > 0:
                    logger.info(f"✅ Categorization successful: {len(categorized_data)} transactions categorized")
                    
                    # Log sample categories
                    sample_categories = [t.get('category', 'Unknown') for t in categorized_data[:5]]
                    logger.info(f"   Sample categories: {sample_categories}")
                    
                    # Apply categories to ORIGINAL unmasked transactions
                    for i, original_txn in enumerate(transactions):
                        if i < len(categorized_data):
                            original_txn['category'] = categorized_data[i].get('category', 'Others')
                        else:
                            original_txn['category'] = 'Others'
                    
                    logger.info(f"🔓 Categories applied to original unmasked transactions")
                    return transactions
                else:
                    logger.error(f" Invalid response format: {type(categorized_data)}")
                    logger.error(f"   Response text preview: {response.text[:500]}")
                    # Return transactions with Uncategorized instead of raising error
                    for txn in transactions:
                        txn['category'] = 'Uncategorized'
                    return transactions
            else:
                logger.error("AI returned empty response")
                # Return transactions with Uncategorized instead of raising error
                for txn in transactions:
                    txn['category'] = 'Uncategorized'
                return transactions
                
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ Categorization failed: {e}", exc_info=True)
            
            # Check if it's a timeout error
            if "504" in error_str or "Deadline Exceeded" in error_str or "timeout" in error_str.lower():
                logger.warning(f"⚠️  Gemini API timeout - this usually happens with large batches")
                logger.warning(f"   Suggestion: Try processing fewer statements at once")
                logger.warning(f"   Falling back to 'Uncategorized' for all transactions")
            
            # Return transactions with Uncategorized
            for txn in transactions:
                txn['category'] = 'Uncategorized'
            return transactions

class FinancialAnalystAgent(BaseAgent):
    """Generates financial insights from a list of transactions."""
    
    def _aggregate_by_category(self, transactions: List[Dict]) -> Dict[str, Dict[str, float]]:
        """
        Aggregate transactions by category.
        
        Returns:
            Dictionary mapping category to {amount, count}
        """
        category_totals = {}
        for txn in transactions:
            category = txn.get('category', 'Others')
            debit = float(txn.get('debit', 0))
            credit = float(txn.get('credit', 0))
            amount = debit if debit > 0 else credit
            
            if category not in category_totals:
                category_totals[category] = {'amount': 0.0, 'count': 0}
            
            category_totals[category]['amount'] += amount
            category_totals[category]['count'] += 1
        
        return category_totals
    
    def _get_date_range(self, transactions: List[Dict]) -> Dict[str, str]:
        """
        Get the date range of transactions.
        
        Returns:
            Dictionary with start_date and end_date
        """
        if not transactions:
            return {'start_date': '', 'end_date': ''}
        
        dates = []
        for txn in transactions:
            date_val = txn.get('date')
            if date_val:
                # Handle both string and date objects
                if isinstance(date_val, str):
                    dates.append(date_val)
                else:
                    dates.append(str(date_val))
        
        if not dates:
            return {'start_date': '', 'end_date': ''}
        
        dates.sort()
        return {'start_date': dates[0], 'end_date': dates[-1]}
    
    def _calculate_monthly_trends(self, transactions: List[Dict]) -> Dict[str, float]:
        """
        Calculate monthly spending trends.
        
        Returns:
            Dictionary mapping month to total spending
        """
        monthly_totals = {}
        for txn in transactions:
            date_val = txn.get('date')
            if date_val:
                # Extract month (YYYY-MM format)
                if isinstance(date_val, str):
                    month = date_val[:7] if len(date_val) >= 7 else date_val
                else:
                    month = str(date_val)[:7]
                
                debit = float(txn.get('debit', 0))
                if month not in monthly_totals:
                    monthly_totals[month] = 0.0
                monthly_totals[month] += debit
        
        return monthly_totals
    
    async def generate_financial_insights(self, transactions: List[Dict]) -> Dict:
        # SECURITY LAYER: Use only aggregated data (no individual transaction details)
        logger.info(f"📊 Aggregating {len(transactions)} transactions for analysis...")
        
        total_income = sum(float(t.get('credit', 0)) for t in transactions)
        total_expenses = sum(float(t.get('debit', 0)) for t in transactions)
        category_breakdown = self._aggregate_by_category(transactions)
        date_range = self._get_date_range(transactions)
        monthly_trends = self._calculate_monthly_trends(transactions)
        
        # Create aggregated data structure (NO individual transaction details)
        aggregated_data = {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_savings': total_income - total_expenses,
            'transaction_count': len(transactions),
            'date_range': f"{date_range.get('start_date', '')} to {date_range.get('end_date', '')}",
            'category_breakdown': category_breakdown,
            'monthly_trends': monthly_trends
        }
        
        logger.info(f"✅ Aggregation complete - sending only aggregated data to LLM")
        logger.info(f"   Total Income: Rs {total_income:,.2f}")
        logger.info(f"   Total Expenses: Rs {total_expenses:,.2f}")
        logger.info(f"   Categories: {len(category_breakdown)}")
        
        # Security audit logging
        try:
            from .logging_config import log_llm_request
            log_llm_request(masked=True, data_type="aggregated_data", context="financial_analysis")
        except ImportError:
            pass  # Logging config not available
        
        prompt = f"""You are a highly experienced financial advisor with 20+ years of expertise in personal finance management, investment analysis, and wealth planning. You have helped thousands of clients understand their spending patterns, optimize their budgets, and achieve financial goals.

Your task is to analyze the provided AGGREGATED financial data and deliver comprehensive, actionable financial insights that will help the user make better financial decisions.

**IMPORTANT: You are receiving ONLY aggregated statistics, NOT individual transaction details. This protects user privacy.**

**YOUR EXPERTISE:**
- Personal Finance Management (20+ years)
- Investment Portfolio Analysis
- Budget Optimization & Expense Tracking
- Cash Flow Management
- Financial Goal Planning
- Risk Assessment & Mitigation

**ANALYSIS FRAMEWORK:**

1. **FINANCIAL HEALTH OVERVIEW**
   - Calculate total income (all credit transactions + dividends)
   - Calculate total expenses (all debit transactions)
   - Calculate net savings (income - expenses)
   - Calculate savings rate (savings / income * 100)
   - Assess financial health: Excellent (>30%), Good (20-30%), Fair (10-20%), Poor (<10%)

2. **CATEGORY-WISE BREAKDOWN**
   - Group transactions by category
   - Calculate total spent in each category
   - Calculate percentage of total expenses for each category
   - Identify top 3 spending categories
   - Flag categories with unusually high spending

3. **SPENDING PATTERNS & TRENDS**
   - Identify recurring expenses (monthly bills, subscriptions)
   - Detect irregular large expenses
   - Analyze spending frequency (daily, weekly, monthly)
   - Compare weekday vs weekend spending
   - Identify spending spikes (dates with high expenses)

4. **INCOME ANALYSIS**
   - Identify primary income sources (salary, dividends, refunds)
   - Calculate income stability (regular vs irregular)
   - Analyze dividend income from investments
   - Identify other income streams

5. **INVESTMENT INSIGHTS**
   - Analyze dividend transactions (stock returns)
   - Calculate total dividend income
   - Identify investment-related expenses (SIPs, premiums)
   - Assess investment activity level

6. **ACTIONABLE RECOMMENDATIONS**
   Based on the analysis, provide 5-7 specific, personalized recommendations:
   - Budget optimization suggestions
   - Expense reduction opportunities
   - Savings improvement strategies
   - Investment diversification advice
   - Emergency fund recommendations
   - Debt management tips (if applicable)
   - Financial goal planning suggestions

7. **RED FLAGS & WARNINGS**
   - Overspending in specific categories (>30% of income)
   - Negative savings rate (expenses > income)
   - Lack of investment activity
   - High entertainment/dining expenses
   - Missing emergency fund indicators
   - Irregular income patterns

8. **POSITIVE HIGHLIGHTS**
   - Good savings habits
   - Diversified income sources
   - Regular investment activity
   - Controlled discretionary spending
   - Healthy financial ratios

**OUTPUT FORMAT (JSON):**
```json
{{
  "summary": {{
    "total_income": float,
    "total_expenses": float,
    "net_savings": float,
    "savings_rate": float,
    "financial_health": "Excellent/Good/Fair/Poor",
    "transaction_count": int,
    "date_range": "DD/MM/YYYY - DD/MM/YYYY"
  }},
  "category_wise_split": {{
    "Food & Dining": {{"amount": float, "percentage": float, "count": int}},
    "Travel": {{"amount": float, "percentage": float, "count": int}},
    "Other Transfer": {{"amount": float, "percentage": float, "count": int}},
    "Dividends": {{"amount": float, "percentage": float, "count": int}},
    "Shopping": {{"amount": float, "percentage": float, "count": int}},
    "Bills & Utilities": {{"amount": float, "percentage": float, "count": int}},
    "Entertainment": {{"amount": float, "percentage": float, "count": int}},
    "Income": {{"amount": float, "percentage": float, "count": int}},
    "Investments": {{"amount": float, "percentage": float, "count": int}},
    "Others": {{"amount": float, "percentage": float, "count": int}}
  }},
  "insights": [
    "💰 Financial Health: [Assessment with specific numbers]",
    "📊 Top Spending: [Top 3 categories with amounts and percentages]",
    "💸 Savings Rate: [Percentage with interpretation]",
    "🎯 Recommendation 1: [Specific, actionable advice]",
    "🎯 Recommendation 2: [Specific, actionable advice]",
    "🎯 Recommendation 3: [Specific, actionable advice]",
    "⚠️ Warning (if any): [Specific concern with numbers]",
    "✅ Positive Highlight: [Good financial behavior observed]"
  ],
  "spending_patterns": {{
    "highest_expense_day": "DD/MM/YYYY",
    "highest_expense_amount": float,
    "average_daily_expense": float,
    "recurring_expenses": ["List of recurring payments"],
    "top_merchants": ["Top 5 merchants by spending"]
  }},
  "income_breakdown": {{
    "salary": float,
    "dividends": float,
    "refunds": float,
    "other_income": float,
    "income_stability": "Stable/Variable"
  }}
}}
```

**ANALYSIS GUIDELINES:**
1. Be specific with numbers (use actual amounts, not vague terms)
2. Provide context (compare to typical spending patterns)
3. Be constructive (focus on improvement, not criticism)
4. Prioritize actionable advice (what user can do immediately)
5. Use emojis for visual clarity
6. Consider Indian financial context (Rupee amounts, UPI, dividends)
7. Identify both strengths and areas for improvement
8. Make recommendations realistic and achievable

**AGGREGATED DATA TO ANALYZE (privacy-protected):**
{json.dumps(aggregated_data, indent=2, default=str)}

**YOUR COMPREHENSIVE FINANCIAL ANALYSIS (JSON format):**"""
        analysis = await self._get_json_response(prompt)
        if not isinstance(analysis, dict): return {"error": "Failed to generate a valid analysis object."}
        return analysis

class FinancialChatAgent(BaseAgent):
    """Generates a natural language response for the chat API - OPTIMIZED FOR SPEED."""
    
    def __init__(self, model_name="gemini-2.5-flash"):
        # Use stable Gemini Flash model (better rate limits)
        super().__init__(model_name)
    
    async def generate_response(self, user_query: str, retrieved_data: List[Dict]) -> str:
        if not retrieved_data: return "I couldn't find any transactions that match your query."
        
        # OPTIMIZATION: Limit data sent to AI for faster responses
        transaction_count = len(retrieved_data)
        
        # If too many transactions, summarize instead of listing all
        if transaction_count > 50:
            # Send only summary data for large result sets
            total_debit = sum(float(t.get('debit', 0)) for t in retrieved_data)
            total_credit = sum(float(t.get('credit', 0)) for t in retrieved_data)
            categories = {}
            for t in retrieved_data:
                cat = t.get('category', 'Uncategorized')
                categories[cat] = categories.get(cat, 0) + 1
            
            summary_data = {
                "total_transactions": transaction_count,
                "total_debit": total_debit,
                "total_credit": total_credit,
                "categories": categories,
                "sample_transactions": retrieved_data[:10]  # First 10 as examples
            }
            data_json_string = json.dumps(summary_data, indent=2, default=str)
        else:
            data_json_string = json.dumps(retrieved_data, indent=2, default=str)
        
        prompt = f"""You are a FAST and precise financial assistant. Respond quickly and concisely.

**SPEED-OPTIMIZED RULES:**
1. Be CONCISE - users want fast answers
2. For large datasets (>50 transactions): Provide summary with key insights
3. For small datasets (50 or less): List all transactions
4. Use bullet points and emojis for readability
5. Calculate totals and provide insights quickly

**RESPONSE FORMATS:**

For SMALL datasets (50 or less transactions):
Found {transaction_count} transactions:
- Date | Description | Amount | Category

For LARGE datasets (>50 transactions):
Analysis of {transaction_count} transactions:
- Total Spent: Rs X,XXX
- Total Received: Rs X,XXX
- Top Categories: [list top 3]
- Sample transactions: [show 5-10 examples]

**USER QUESTION:**
{user_query}

**DATA ({transaction_count} transactions):**
{data_json_string}

**YOUR FAST RESPONSE:**
"""
        try:
            # Use faster generation config
            response = await self.model.generate_content_async(
                prompt,
                generation_config={
                    'temperature': 0.3,  # Lower for faster, more deterministic responses
                    'top_p': 0.8,
                    'top_k': 20,
                    'max_output_tokens': 2048,  # Limit output for speed
                }
            )
            if response and hasattr(response, 'text') and response.text is not None: 
                return response.text.strip()
            else: 
                return "I received an empty response from the analysis service."
        except Exception as e:
            logger.error(f"Chat response error: {e}")
            return "An error occurred while trying to formulate a response."

class QueryRouterAgent(BaseAgent):
    """Analyzes a user query to decide between vector search and filter-based search."""
    async def route_query(self, user_query: str) -> Dict:
        current_year = datetime.datetime.now().year
        
        # Helper to get the last day of a given month
        def get_last_day(year, month):
            return monthrange(year, month)[1]
        
        prompt = f"""You are a master query routing agent. Your job is to analyze the users question and convert it into a valid MongoDB query filter.
Return a JSON object with `query_type` ("filter" or "vector") and `payload`.

**DATABASE SCHEMA:**
- `date`: A BSON Date object. **MUST be queried with date ranges using `$gte` and `$lt`**.
- `description`: Text. Use `$regex` for text matching (case-insensitive with "i" flag).
- `category`: String, e.g., "Food & Dining", "Shopping", "Investments", "Utilities", etc.
- `debit`: Float. For expenses, query with `{{"debit": {{"$gt": 0}} }}`.
- `credit`: Float. For income, query with `{{"credit": {{"$gt": 0}} }}`.
- `amount`: Float. Total transaction amount.

**CRITICAL DATE RULES:**
1.  NEVER use `$regex` on the `date` field. It will fail.
2.  Always convert date queries into a range using `$gte` (start date) and `$lt` (day AFTER end date).
3.  Dates in the payload MUST be strings formatted as "YYYY-MM-DD".
4.  Current year is {current_year}. Use this for queries without explicit year.

**MONTH MAPPINGS:**


**CRITICAL ROUTING RULES:**
- Keywords like "list", "all", "show me", "give me", "tell me" with dates/categories → ALWAYS use FILTER
- Specific merchant names without date/category → use VECTOR
- Date + category combinations → use FILTER
- "transactions in [month]" or "during [month]" → ALWAYS use FILTER
- Any query with "all", "every", "total" → prefer FILTER if date/category mentioned

**EXAMPLES:**

User Query: "give me the list of transactions in the month of august"
Output:
{{
  "query_type": "filter",
  "payload": {{ "date": {{ "$gte": "{current_year}-08-01", "$lt": "{current_year}-09-01" }} }}
}}

User Query: "tell me the total list of transactions in the month of august"
Output:
{{
  "query_type": "filter",
  "payload": {{ "date": {{ "$gte": "{current_year}-08-01", "$lt": "{current_year}-09-01" }} }}
}}

User Query: "list all transactions in august"
Output:
{{
  "query_type": "filter",
  "payload": {{ "date": {{ "$gte": "{current_year}-08-01", "$lt": "{current_year}-09-01" }} }}
}}

User Query: "show me everything from september"
Output:
{{
  "query_type": "filter",
  "payload": {{ "date": {{ "$gte": "{current_year}-09-01", "$lt": "{current_year}-10-01" }} }}
}}

User Query: "all my transactions"
Output:
{{
  "query_type": "filter",
  "payload": {{}}
}}

User Query: "show me all credit transactions"
Output:
{{
  "query_type": "filter",
  "payload": {{ "credit": {{ "$gt": 0 }} }}
}}

User Query: "show me all debit transactions"
Output:
{{
  "query_type": "filter",
  "payload": {{ "debit": {{ "$gt": 0 }} }}
}}

User Query: "what did I spend on food in august"
Output:
{{
  "query_type": "filter",
  "payload": {{ 
    "category": "Food & Dining",
    "date": {{ "$gte": "{current_year}-08-01", "$lt": "{current_year}-09-01" }} 
  }}
}}

User Query: "show me investment transactions"
Output:
{{
  "query_type": "filter",
  "payload": {{ "category": {{ "$regex": "Investment", "$options": "i" }} }}
}}

User Query: "what was that purchase at the bike zone?"
Output:
{{
  "query_type": "vector",
  "payload": "purchase at the bike zone"
}}

**IMPORTANT:**
- For queries asking for "list", "all", "total" transactions in a specific month/period, use FILTER with date range
- For queries about specific merchants or descriptions, use VECTOR search
- For category-based queries, use FILTER with category field
- Always prefer FILTER over VECTOR when the query has clear date/category/amount criteria

**Now, analyze this user query:**

User Query: "{user_query}"
"""
        route = await self._get_json_response(prompt)
        if not isinstance(route, dict) or "query_type" not in route or "payload" not in route:
            return {"query_type": "vector", "payload": user_query}
        return route

class EmbeddingAgent:
    """Handles the creation of embeddings for vector search with batch optimization."""
    
    def __init__(self, model: str = "models/text-embedding-004", batch_size: int = 100):
        """
        Initialize the embedding agent.
        
        Args:
            model: Embedding model to use
            batch_size: Maximum documents per API call (Google supports up to 100)
        """
        self.model = model
        self.batch_size = batch_size
    
    async def embed_single_document(self, document: Dict) -> List[float]:
        """
        Embed a single document (fallback for error cases).
        
        Args:
            document: Single document dictionary
            
        Returns:
            Embedding vector
        """
        result = await self.embed_documents([document])
        return result[0] if result else []
    
    async def embed_documents(self, documents: List[Dict]) -> List[List[float]]:
        """
        Embed documents in batches for optimal API usage.
        
        Google's embedding API supports batch requests (up to 100 documents),
        which is much faster than individual calls.
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            List of embedding vectors
        """
        if not documents:
            return []
        
        # Prepare content strings for all documents
        content = [
            f"Date: {doc.get('date', '')}, Desc: {doc.get('description', '')}, "
            f"Amount: {doc.get('amount', 0):.2f}, Cat: {doc.get('category', '')}"
            for doc in documents
        ]
        
        all_embeddings = []
        
        # Process in batches if necessary (Google supports up to 100 per call)
        for i in range(0, len(content), self.batch_size):
            batch_content = content[i:i + self.batch_size]
            
            try:
                logger.debug(f"Embedding batch {i//self.batch_size + 1}: "
                           f"{len(batch_content)} documents")
                
                result = genai.embed_content(
                    model=self.model,
                    content=batch_content,
                    task_type="retrieval_document"
                )
                
                # Handle both single and batch responses
                if isinstance(result['embedding'][0], list):
                    # Batch response: list of embeddings
                    all_embeddings.extend(result['embedding'])
                else:
                    # Single response: one embedding
                    all_embeddings.append(result['embedding'])
                    
            except Exception as e:
                logger.error(f"Embedding Error for batch {i//self.batch_size + 1}: {e}", 
                           exc_info=True)
                # Return empty vectors for failed batch
                all_embeddings.extend([[]] * len(batch_content))
        
        logger.info(f"Successfully embedded {len(all_embeddings)} documents in "
                   f"{(len(documents) + self.batch_size - 1) // self.batch_size} API call(s)")
        
        return all_embeddings


# app/agents.py - LangChain Agentic Implementation
# app/agents.py - TRUE AGENTIC IMPLEMENTATION with Credit/Debit Fix

# app/agents.py - FIXED VERSION WITH CORRECT AMOUNT EXTRACTION

# app/agents.py - COMPLETE FINAL VERSION FOR YOUR BANK FORMAT

# app/agents.py - FINAL WORKING VERSION FOR YOUR BANK STATEMENT

