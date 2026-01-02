from __future__ import annotations
"""Company enrichment service using Kazakhstan business registries and search."""
import logging
import re
from typing import Any, Dict, Optional
from uuid import UUID

import httpx
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)


# Common legal forms in Kazakhstan
KZ_LEGAL_FORMS = ["ТОО", "АО", "ИП", "КТ", "ОО", "ПТ", "ПК", "РК"]


class CompanyEnrichmentService:
    """
    Service to enrich company data from:
    - Kazakhstan BIN registry (stat.gov.kz)
    - Google Search for additional info
    - AI to extract structured data
    """
    
    STAT_GOV_URL = "https://stat.gov.kz/api/juridical/counter/api/"
    GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
    
    def __init__(self, api_key:Optional[ str ] = None, google_api_key:Optional[ str ] = None):
        self.gemini_key = api_key or settings.gemini_api_key
        self.google_search_key = google_api_key  # Optional
        
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None
    
    async def enrich_company(self, name: str, bin_iin:Optional[ str ] = None) -> Dict[str, Any]:
        """
        Enrich company data from available sources.
        
        Returns:
            {
                "bin": "123456789012",
                "full_name": "ТОО 'Рога и Копыта'",
                "director": "Иванов Иван Иванович",
                "registration_date": "2015-01-15",
                "address": "г. Алматы, ул. Абая 150",
                "activity": "Оптовая торговля",
                "phone": "+7 777 123 4567",
                "email": "info@rogaikopyta.kz",
                "source": "stat.gov.kz"
            }
        """
        result = {
            "original_name": name,
            "bin": bin_iin,
            "enriched": False
        }
        
        # Try to find BIN in the name
        if not bin_iin:
            bin_match = re.search(r'\b(\d{12})\b', name)
            if bin_match:
                bin_iin = bin_match.group(1)
                result["bin"] = bin_iin
        
        # Try stat.gov.kz API if we have BIN
        if bin_iin:
            gov_data = await self._fetch_from_stat_gov(bin_iin)
            if gov_data:
                result.update(gov_data)
                result["enriched"] = True
                result["source"] = "stat.gov.kz"
        
        # If no BIN, try to search by name
        if not result.get("enriched"):
            search_data = await self._search_company(name)
            if search_data:
                result.update(search_data)
                result["enriched"] = True
        
        # Use AI to extract additional info if we have search results
        if self.model and result.get("search_snippet"):
            ai_enriched = await self._ai_extract_info(name, result.get("search_snippet", ""))
            if ai_enriched:
                result.update(ai_enriched)
        
        return result
    
    async def _fetch_from_stat_gov(self, bin_iin: str) ->Optional[ Dict[str, Any] ]:
        """Fetch company data from Kazakhstan statistics bureau."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # This is the public BIN checker endpoint
                response = await client.get(
                    f"https://stat.gov.kz/api/juridical/counter/api/?bin={bin_iin}&lang=ru"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("obj"):
                        obj = data["obj"]
                        return {
                            "bin": bin_iin,
                            "full_name": obj.get("name"),
                            "director": obj.get("fio"),
                            "registration_date": obj.get("registerDate"),
                            "address": obj.get("address"),
                            "activity": obj.get("okedName"),
                            "status": obj.get("krpName")
                        }
        except Exception as e:
            logger.warning(f"stat.gov.kz lookup failed: {e}")
        
        return None
    
    async def _search_company(self, name: str) ->Optional[ Dict[str, Any] ]:
        """Search for company info using available search APIs."""
        # Clean company name for search
        search_query = self._clean_company_name(name) + " БИН Казахстан"
        
        # Try Google Custom Search if configured
        if self.google_search_key:
            return await self._google_search(search_query)
        
        # Use AI to search via grounding (if available)
        if self.model:
            return await self._ai_web_search(search_query)
        
        return None
    
    async def _google_search(self, query: str) ->Optional[ Dict[str, Any] ]:
        """Search using Google Custom Search API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.GOOGLE_SEARCH_URL,
                    params={
                        "key": self.google_search_key,
                        "cx": settings.google_cse_id if hasattr(settings, 'google_cse_id') else "",
                        "q": query,
                        "num": 3
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    if items:
                        # Combine snippets for AI extraction
                        snippets = " ".join([item.get("snippet", "") for item in items[:3]])
                        return {"search_snippet": snippets}
        except Exception as e:
            logger.warning(f"Google search failed: {e}")
        
        return None
    
    async def _ai_web_search(self, query: str) ->Optional[ Dict[str, Any] ]:
        """Use AI to find company info."""
        prompt = f"""
Найди информацию о компании по запросу: "{query}"

Верни JSON с найденной информацией:
{{
    "bin": "БИН если найден (12 цифр)",
    "address": "адрес офиса если найден",
    "phone": "телефон если найден",
    "director": "ФИО директора если найдено",
    "website": "сайт если найден"
}}

Если информация не найдена, верни пустой JSON {{}}.
"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean markdown
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            import json
            return json.loads(text)
        except Exception as e:
            logger.warning(f"AI web search failed: {e}")
        
        return None
    
    async def _ai_extract_info(self, company_name: str, text: str) ->Optional[ Dict[str, Any] ]:
        """Use AI to extract structured info from text."""
        if not text:
            return None
        
        prompt = f"""
Из текста извлеки информацию о компании "{company_name}".

Текст: {text[:2000]}

Верни JSON:
{{
    "address": "точный адрес если найден",
    "phone": "телефон в формате +7...",
    "email": "email если найден",
    "website": "сайт без https://",
    "note": "важная доп. информация (1-2 предложения)"
}}

Если поле не найдено — null.
"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            import json
            return json.loads(text)
        except Exception as e:
            logger.warning(f"AI extraction failed: {e}")
        
        return None
    
    def _clean_company_name(self, name: str) -> str:
        """Clean company name for search."""
        # Remove common legal form prefixes
        cleaned = name
        for form in KZ_LEGAL_FORMS:
            cleaned = re.sub(rf'\b{form}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Remove quotes and extra spaces
        cleaned = re.sub(r'["\']', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def extract_company_from_text(self, text: str) ->Optional[ str ]:
        """
        Extract company name from natural text.
        E.g., "Встреча с ТОО 'Рога и Копыта'" -> "ТОО 'Рога и Копыта'"
        """
        # Pattern for KZ company names with legal form
        pattern = rf"({'|'.join(KZ_LEGAL_FORMS)})\s*['\"]?([^'\"]+)['\"]?"
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            form = match.group(1).upper()
            name = match.group(2).strip()
            return f"{form} '{name}'"
        
        return None
