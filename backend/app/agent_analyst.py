import json
import logging
import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from .base_agent import BaseAgent
from .config import settings

logger = logging.getLogger(__name__)

# --- Structured Output Schema ---

class FinancialAnalysisOutput(BaseModel):
    insights: List[str] = Field(description="8 to 10 actionable financial insights")
    summary: str = Field(description="A concise executive summary of the financial state")

# --- Deterministic Financial Tools ---

@tool
def aggregate_by_category(transactions_json: str) -> Dict[str, float]:
    """Returns total spend per category. Input must be a JSON string of transactions."""
    transactions = json.loads(transactions_json)
    category_totals = {}
    for txn in transactions:
        category = txn.get('category', 'Other')
        debit = float(txn.get('debit', 0))
        category_totals[category] = category_totals.get(category, 0.0) + debit
    return category_totals

@tool
def income_vs_expense(transactions_json: str) -> Dict[str, float]:
    """Returns total income, expenses, and savings. Input must be a JSON string of transactions."""
    transactions = json.loads(transactions_json)
    total_income = sum(float(t.get('credit', 0)) for t in transactions)
    total_expenses = sum(float(t.get('debit', 0)) for t in transactions)
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_savings": total_income - total_expenses
    }

@tool
def monthly_trends(transactions_json: str) -> Dict[str, float]:
    """Returns time-based spending trends (monthly). Input must be a JSON string of transactions."""
    transactions = json.loads(transactions_json)
    monthly_totals = {}
    for txn in transactions:
        date_val = txn.get('date', '')
        month = str(date_val)[:7] if date_val else "Unknown"
        debit = float(txn.get('debit', 0))
        monthly_totals[month] = monthly_totals.get(month, 0.0) + debit
    return monthly_totals

@tool
def anomaly_detection(transactions_json: str) -> List[str]:
    """Detects unusual spikes or patterns (e.g. transactions > 3x average). Input must be a JSON string of transactions."""
    transactions = json.loads(transactions_json)
    debits = [float(t.get('debit', 0)) for t in transactions if float(t.get('debit', 0)) > 0]
    if not debits: return ["No anomalies detected."]
    
    avg = sum(debits) / len(debits)
    anomalies = []
    for t in transactions:
        val = float(t.get('debit', 0))
        if val > avg * 3:
            anomalies.append(f"Unusual spike: {t.get('description')} - Rs {val}")
    return anomalies if anomalies else ["No significant anomalies detected."]

@tool
def calculate_savings_rate(total_income: float, total_expenses: float) -> float:
    """Computes savings percentage. Input: total_income, total_expenses."""
    if total_income <= 0: return 0.0
    savings = total_income - total_expenses
    return (savings / total_income) * 100

class FinancialAnalystAgent(BaseAgent):
    """Production-grade financial insights generator using an Agent-driven approach with strictly deterministic tools and LangGraph."""
    
    def __init__(self, model_name="gemini-3.1-flash-lite-preview"):
        super().__init__(model_name=model_name)
        
        # Tools for the Insights Agent
        self.tools = [
            aggregate_by_category,
            income_vs_expense,
            monthly_trends,
            anomaly_detection,
            calculate_savings_rate
        ]
        
        # System prompt as a Financial Analyst
        # Fixed: state_modifier removed to avoid TypeError on older langgraph versions
        self.agent_executor = create_react_agent(
            self.llm, 
            self.tools
        )

    async def generate_financial_insights(self, transactions: List[Dict]) -> Dict:
        """Executes the agentic insights generation flow using LangGraph."""
        logger.info(f"[STATS] Analyzing {len(transactions)} transactions using LangGraph Insights Node...")
        
        # Prepare input
        transactions_json = json.dumps(transactions, default=str)
        
        try:
            # Step 1: Execute agent loop
            result = await self.agent_executor.ainvoke({"messages": [("human", f"Analyze these transactions: {transactions_json}")]})
            last_message = result["messages"][-1].content
            
            # Step 2: Final structuring call to ensure contract is met
            struct_prompt = f"Convert the following financial analysis into the strictly required JSON format with 'insights' (list) and 'summary' (string).\n\nAnalysis:\n{last_message}"
            final_output = await self.llm.with_structured_output(FinancialAnalysisOutput).ainvoke(struct_prompt)
            
            return final_output.model_dump()
            
        except Exception as e:
            logger.error(f"Insights Agent failed: {e}")
            return {
                "insights": ["System error occurred during analysis."],
                "summary": "Full analysis unavailable."
            }
