"""
RAG Response Formatter - Structures and formats RAG pipeline responses for frontend display
"""

import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RAGResponseFormatter:
    """Formats raw RAG responses into structured, user-friendly format"""
    
    # Response type patterns
    RESPONSE_PATTERNS = {
        'summary': r'(total|sum|overall|in total|altogether)',
        'list': r'(list|following|here are|these are)',
        'table': r'(table|breakdown|comparison|category)',
        'metric': r'(average|median|highest|lowest|maximum|minimum)',
        'insight': r'(insight|recommendation|suggest|should|consider)',
    }
    
    # Currency patterns
    CURRENCY_PATTERN = r'?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
    
    @staticmethod
    def format_currency(amount: float, include_symbol: bool = True) -> str:
        """Format amount as currency with thousand separators"""
        if isinstance(amount, str):
            try:
                amount = float(amount.replace('', '').replace(',', '').strip())
            except:
                return str(amount)
        
        formatted = f"{amount:,.2f}"
        return f"{formatted}" if include_symbol else formatted
    
    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """Extract all numbers from text"""
        import re
        numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d{2})?', text)
        return [float(n.replace(',', '')) for n in numbers]
    
    @staticmethod
    def detect_response_type(text: str) -> str:
        """Detect the type of response based on content"""
        text_lower = text.lower()
        
        for response_type, pattern in RAGResponseFormatter.RESPONSE_PATTERNS.items():
            if re.search(pattern, text_lower):
                return response_type
        
        return 'summary'
    
    @staticmethod
    def extract_metrics(text: str) -> List[Dict[str, Any]]:
        """Extract metrics from response text"""
        metrics = []
        
        # Pattern for "X spent on Y" or "Total X: Y"
        patterns = [
            r'([\w\s&]+):\s*?([\d,]+(?:\.\d{2})?)',
            r'([\w\s&]+)\s+(?:is|was|of)\s+?([\d,]+(?:\.\d{2})?)',
            r'([\w\s&]+)\s+(?:amount|total|sum)\s+(?:is|was)\s+?([\d,]+(?:\.\d{2})?)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                label = match.group(1).strip()
                value_str = match.group(2).replace(',', '')
                try:
                    value = float(value_str)
                    metrics.append({
                        'label': label,
                        'value': value,
                        'currency': True,
                        'formatted': RAGResponseFormatter.format_currency(value)
                    })
                except:
                    pass
        
        return metrics
    
    @staticmethod
    def extract_insights(text: str) -> List[Dict[str, Any]]:
        """Extract key insights from response"""
        insights = []
        
        # Split by common insight indicators
        sentences = re.split(r'[.!?]\s+', text)
        
        insight_keywords = {
            'positive': ['great', 'good', 'excellent', 'well', 'improved', 'increased', 'saved'],
            'warning': ['high', 'excessive', 'decreased', 'low', 'concern', 'warning', 'alert'],
            'neutral': ['note', 'observe', 'found', 'shows', 'indicates', 'suggests']
        }
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check for insight keywords
            insight_type = 'neutral'
            for key_type, keywords in insight_keywords.items():
                if any(kw in sentence_lower for kw in keywords):
                    insight_type = key_type
                    break
            
            # Only add substantial sentences
            if len(sentence.strip()) > 20 and any(kw in sentence_lower for kw in 
                                                   ['spend', 'save', 'income', 'expense', 'category', 'transaction']):
                insights.append({
                    'text': sentence.strip(),
                    'type': insight_type,
                    'icon': RAGResponseFormatter._get_insight_icon(insight_type)
                })
        
        return insights[:3]  # Return top 3 insights
    
    @staticmethod
    def _get_insight_icon(insight_type: str) -> str:
        """Get icon name for insight type"""
        icons = {
            'positive': 'TrendingUp',
            'warning': 'AlertCircle',
            'neutral': 'Info'
        }
        return icons.get(insight_type, 'Info')
    
    @staticmethod
    def extract_transactions(text: str) -> List[Dict[str, Any]]:
        """Extract transaction information from response"""
        transactions = []
        
        # Pattern for transaction-like data
        # "Date: X, Description: Y, Amount: Z"
        pattern = r'(?:date|on):\s*([^,]+),\s*(?:description|item):\s*([^,]+),\s*(?:amount|spent):\s*?([\d,]+(?:\.\d{2})?)'
        
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                transactions.append({
                    'date': match.group(1).strip(),
                    'description': match.group(2).strip(),
                    'amount': float(match.group(3).replace(',', ''))
                })
            except:
                pass
        
        return transactions
    
    @staticmethod
    def format_response(raw_response: str, response_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Format raw RAG response into structured format
        
        Args:
            raw_response: The raw text response from RAG pipeline
            response_data: Optional structured data from backend
            
        Returns:
            Formatted response dict with sections, metrics, insights
        """
        try:
            response_type = RAGResponseFormatter.detect_response_type(raw_response)
            metrics = RAGResponseFormatter.extract_metrics(raw_response)
            insights = RAGResponseFormatter.extract_insights(raw_response)
            transactions = RAGResponseFormatter.extract_transactions(raw_response)
            
            # Create sections based on response type
            sections = []
            
            # Main answer section
            sections.append({
                'title': 'Answer',
                'type': 'text',
                'content': raw_response,
                'icon': 'MessageSquare',
                'color': 'from-blue-500 to-cyan-500'
            })
            
            # Metrics section
            if metrics:
                sections.append({
                    'title': 'Key Metrics',
                    'type': 'metric',
                    'content': metrics,
                    'icon': 'BarChart3',
                    'color': 'from-purple-500 to-pink-500'
                })
            
            # Insights section
            if insights:
                sections.append({
                    'title': 'Insights',
                    'type': 'insight',
                    'content': insights,
                    'icon': 'Lightbulb',
                    'color': 'from-yellow-500 to-orange-500'
                })
            
            # Transactions section
            if transactions:
                sections.append({
                    'title': 'Transactions',
                    'type': 'table',
                    'content': transactions,
                    'icon': 'List',
                    'color': 'from-green-500 to-emerald-500'
                })
            
            return {
                'status': 'success',
                'data': {
                    'answer': raw_response,
                    'type': response_type,
                    'sections': sections,
                    'metrics': metrics,
                    'insights': insights,
                    'transactions': transactions,
                    'formatted_at': datetime.utcnow().isoformat()
                }
            }
        
        except Exception as e:
            logger.error(f"Error formatting RAG response: {e}")
            return {
                'status': 'success',
                'data': {
                    'answer': raw_response,
                    'type': 'summary',
                    'sections': [{
                        'title': 'Answer',
                        'type': 'text',
                        'content': raw_response,
                        'icon': 'MessageSquare',
                        'color': 'from-blue-500 to-cyan-500'
                    }],
                    'metrics': [],
                    'insights': [],
                    'transactions': []
                }
            }


# Create singleton instance
rag_formatter = RAGResponseFormatter()
