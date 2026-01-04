"""
JSON Utilities for safe parsing of LLM outputs.
"""
import json
import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def safe_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON from text (e.g. LLM response).
    Handles markdown code blocks, text wrapper, and basic malformed JSON.
    """
    if not text:
        return None
        
    # 1. Clean Markdown (```json ... ```)
    clean_text = text.strip()
    if "```" in clean_text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
        if match:
            clean_text = match.group(1).strip()
            
    # 2. Extract JSON object if text contains extra chatter
    # Look for first '{' and last '}'
    start = clean_text.find("{")
    end = clean_text.rfind("}")
    
    if start != -1 and end != -1:
        clean_text = clean_text[start:end+1]
    elif start != -1:
        # Attempt minimal repair if closing brace missing
        clean_text = clean_text[start:] + "}"
        
    # 3. Try parsing
    try:
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}. Text: {clean_text[:100]}...")
        return None
