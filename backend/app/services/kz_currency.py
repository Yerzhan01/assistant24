from __future__ import annotations
"""
Kazakhstan Currency Service
Fetches exchange rates from National Bank of Kazakhstan (NBK)
API: https://nationalbank.kz/rss/rates_all.xml
"""

import httpx
from datetime import date, datetime, timedelta
from typing import Optional, Dict
import xml.etree.ElementTree as ET
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class CurrencyService:
    """Service for Kazakhstan National Bank exchange rates"""
    
    NBK_API_URL = "https://nationalbank.kz/rss/rates_all.xml"
    
    # Popular currencies
    POPULAR_CURRENCIES = ['USD', 'EUR', 'RUB', 'CNY', 'GBP', 'TRY', 'AED', 'UZS', 'KGS']
    
    def __init__(self):
        self._rates_cache: Dict[str, float] = {}
        self._cache_date: Optional[date] = None
    
    async def get_rates(self, force_refresh: bool = False) -> Dict[str, float]:
        """
        Get all exchange rates from NBK
        Returns dict: {'USD': 450.5, 'EUR': 490.2, ...}
        """
        today = date.today()
        
        # Return cached if still valid
        if not force_refresh and self._cache_date == today and self._rates_cache:
            return self._rates_cache
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.NBK_API_URL)
                response.raise_for_status()
                
                rates = self._parse_nbk_xml(response.text)
                self._rates_cache = rates
                self._cache_date = today
                
                logger.info(f"Updated NBK rates: {len(rates)} currencies")
                return rates
                
        except Exception as e:
            logger.error(f"Failed to fetch NBK rates: {e}")
            # Return cached rates if available
            if self._rates_cache:
                return self._rates_cache
            raise
    
    def _parse_nbk_xml(self, xml_content: str) -> Dict[str, float]:
        """Parse NBK XML response"""
        rates = {}
        
        try:
            root = ET.fromstring(xml_content)
            
            for item in root.findall('.//item'):
                title = item.find('title')
                description = item.find('description')
                
                if title is not None and description is not None:
                    currency_code = title.text.strip()
                    rate_text = description.text.strip()
                    
                    try:
                        rate = float(rate_text.replace(',', '.'))
                        rates[currency_code] = rate
                    except ValueError:
                        continue
                        
        except ET.ParseError as e:
            logger.error(f"Failed to parse NBK XML: {e}")
            
        return rates
    
    async def get_rate(self, currency: str) -> Optional[float]:
        """Get rate for specific currency"""
        rates = await self.get_rates()
        return rates.get(currency.upper())
    
    async def convert(
        self, 
        amount: float, 
        from_currency: str, 
        to_currency: str = 'KZT'
    ) -> Optional[float]:
        """
        Convert amount between currencies
        All conversions go through KZT
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        rates = await self.get_rates()
        
        # Convert to KZT first
        if from_currency == 'KZT':
            amount_in_kzt = amount
        else:
            rate = rates.get(from_currency)
            if not rate:
                return None
            amount_in_kzt = amount * rate
        
        # Convert from KZT to target
        if to_currency == 'KZT':
            return round(amount_in_kzt, 2)
        else:
            rate = rates.get(to_currency)
            if not rate:
                return None
            return round(amount_in_kzt / rate, 2)
    
    async def get_popular_rates(self) -> Dict[str, float]:
        """Get rates for popular currencies only"""
        all_rates = await self.get_rates()
        return {
            code: rate 
            for code, rate in all_rates.items() 
            if code in self.POPULAR_CURRENCIES
        }
    
    async def format_rate_message(self, currency: str = 'USD') -> str:
        """Format rate for display in chat"""
        rate = await self.get_rate(currency)
        if rate:
            return f"💱 Курс {currency} на сегодня: {rate:,.2f} ₸"
        return f"❌ Курс {currency} не найден"
    
    async def format_conversion(
        self, 
        amount: float, 
        from_currency: str, 
        to_currency: str = 'KZT'
    ) -> str:
        """Format conversion result for display"""
        result = await self.convert(amount, from_currency, to_currency)
        
        if result is not None:
            if to_currency == 'KZT':
                return f"💱 {amount:,.2f} {from_currency} = {result:,.2f} ₸"
            else:
                return f"💱 {amount:,.2f} {from_currency} = {result:,.2f} {to_currency}"
        
        return f"❌ Не удалось конвертировать {from_currency} → {to_currency}"
    
    async def get_rates_summary(self) -> str:
        """Get summary of popular rates for briefing"""
        rates = await self.get_popular_rates()
        
        lines = ["💱 **Курсы валют НБ РК:**"]
        for code in ['USD', 'EUR', 'RUB']:
            if code in rates:
                lines.append(f"  • {code}: {rates[code]:,.2f} ₸")
        
        return "\n".join(lines)


# Singleton instance
_currency_service: Optional[CurrencyService] = None


def get_currency_service() -> CurrencyService:
    """Get or create currency service singleton"""
    global _currency_service
    if _currency_service is None:
        _currency_service = CurrencyService()
    return _currency_service
