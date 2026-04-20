import google.generativeai as genai
import json
import re
import asyncio
import logging
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from .config import settings

logger = logging.getLogger(__name__)

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
    """A base class for generative AI agents using LangChain with consistent auth and retry logic."""
    def __init__(self, model_name="gemini-2.0-flash", temperature=0.3):
        self.llm = ChatGoogleGenerativeAI(
            model=model_name, 
            temperature=temperature,
            google_api_key=settings.GEMINI_API_KEY,
            max_retries=3
        )
    
    async def _get_json_response(self, prompt: str) -> Dict[str, Any]:
        """Get JSON response using LangChain and a robust JSON output parser."""
        max_retries = 3
        retry_delay = 2 # Start with 2s
        
        for attempt in range(max_retries):
            try:
                response = await self.llm.ainvoke(prompt)
                return extract_json_from_response(response.content)
            except Exception as e:
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    if attempt < max_retries - 1:
                        wait = retry_delay * (2 ** attempt)
                        logger.warning(f"[WARN] Quota hit (429). Retrying in {wait}s... (Attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(wait)
                        continue
                
                logger.error(f"LangChain SDK Error for {self.__class__.__name__}: {str(e)}")
                raise e
        return {}
