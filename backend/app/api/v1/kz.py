from __future__ import annotations
"""
Kazakhstan Localization API Endpoints
- Currency exchange rates (NBK)
- Kazakhstan holidays calendar
"""

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.services.kz_currency import get_currency_service, CurrencyService
from app.services.kz_holidays import get_holidays_service, KazakhstanHolidays


router = APIRouter(prefix="/api/v1/kz", tags=["Kazakhstan"])


# ==================== SCHEMAS ====================

class ExchangeRateResponse(BaseModel):
    currency: str
    rate: float
    date: str


class ConversionRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str = "KZT"


class ConversionResponse(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    result: float
    rate: float
    formatted: str


class HolidayResponse(BaseModel):
    name_ru: str
    name_kz: str
    date: str
    type: str
    is_day_off: bool


class DateCheckRequest(BaseModel):
    date: str  # Format: YYYY-MM-DD
    language: str = "ru"


class DateCheckResponse(BaseModel):
    date: str
    is_working_day: bool
    is_holiday: bool
    is_weekend: bool
    holiday_name: Optional[str] = None
    warning_message: Optional[str] = None
    suggested_date: Optional[str] = None


# ==================== CURRENCY ENDPOINTS ====================

@router.get("/currency/rates")
async def get_all_rates():
    """Get all exchange rates from National Bank of Kazakhstan"""
    service = get_currency_service()
    rates = await service.get_rates()
    
    return {
        "date": date.today().isoformat(),
        "source": "National Bank of Kazakhstan",
        "rates": rates
    }


@router.get("/currency/rates/popular")
async def get_popular_rates():
    """Get rates for popular currencies (USD, EUR, RUB, etc.)"""
    service = get_currency_service()
    rates = await service.get_popular_rates()
    
    return {
        "date": date.today().isoformat(),
        "rates": rates
    }


@router.get("/currency/rate/{currency}")
async def get_rate(currency: str):
    """Get exchange rate for a specific currency"""
    service = get_currency_service()
    rate = await service.get_rate(currency)
    
    if rate is None:
        return {"error": f"Currency {currency} not found"}
    
    return ExchangeRateResponse(
        currency=currency.upper(),
        rate=rate,
        date=date.today().isoformat()
    )


@router.post("/currency/convert")
async def convert_currency(request: ConversionRequest):
    """Convert amount between currencies"""
    service = get_currency_service()
    
    result = await service.convert(
        request.amount, 
        request.from_currency, 
        request.to_currency
    )
    
    if result is None:
        return {"error": "Conversion failed. Check currency codes."}
    
    # Get rate for reference
    from_rate = await service.get_rate(request.from_currency)
    to_rate = await service.get_rate(request.to_currency) if request.to_currency != "KZT" else 1.0
    
    formatted = await service.format_conversion(
        request.amount, 
        request.from_currency, 
        request.to_currency
    )
    
    return ConversionResponse(
        amount=request.amount,
        from_currency=request.from_currency.upper(),
        to_currency=request.to_currency.upper(),
        result=result,
        rate=from_rate or 0,
        formatted=formatted
    )


# ==================== HOLIDAYS ENDPOINTS ====================

@router.get("/holidays")
async def get_holidays(
    year: Optional[int] = Query(None, description="Year to get holidays for")
):
    """Get all Kazakhstan holidays for a year"""
    service = get_holidays_service()
    target_year = year or date.today().year
    
    holidays = service.get_all_holidays(target_year)
    
    return {
        "year": target_year,
        "holidays": [
            HolidayResponse(
                name_ru=h.name_ru,
                name_kz=h.name_kz,
                date=h.date.isoformat(),
                type=h.holiday_type.value,
                is_day_off=h.is_day_off
            )
            for h in holidays
        ]
    }


@router.get("/holidays/upcoming")
async def get_upcoming_holidays(
    count: int = Query(5, description="Number of holidays to return")
):
    """Get upcoming holidays"""
    service = get_holidays_service()
    holidays = service.get_upcoming_holidays(count)
    
    return {
        "holidays": [
            {
                "name_ru": h.name_ru,
                "name_kz": h.name_kz,
                "date": h.date.isoformat(),
                "days_until": (h.date - date.today()).days
            }
            for h in holidays
        ]
    }


@router.post("/holidays/check-date")
async def check_meeting_date(request: DateCheckRequest):
    """Check if a date is suitable for scheduling a meeting"""
    service = get_holidays_service()
    
    try:
        check_date = datetime.strptime(request.date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    is_weekend = service.is_weekend(check_date)
    is_holiday, holiday = service.is_holiday(check_date)
    is_working = service.is_working_day(check_date)
    
    warning = service.check_meeting_date(check_date, request.language)
    
    suggested = None
    if not is_working:
        suggested = service.get_next_working_day(check_date).isoformat()
    
    return DateCheckResponse(
        date=request.date,
        is_working_day=is_working,
        is_holiday=is_holiday,
        is_weekend=is_weekend,
        holiday_name=holiday.name_ru if holiday else None,
        warning_message=warning if warning else None,
        suggested_date=suggested
    )


@router.get("/holidays/summary")
async def get_holidays_summary(language: str = "ru"):
    """Get formatted summary of upcoming holidays for briefing"""
    service = get_holidays_service()
    summary = service.get_holidays_summary(language)
    
    return {"summary": summary}


# ==================== COMBINED KZ INFO ====================

@router.get("/briefing")
async def get_kz_briefing(language: str = "ru"):
    """Get Kazakhstan-specific briefing (currency + holidays)"""
    currency_service = get_currency_service()
    holidays_service = get_holidays_service()
    
    rates_summary = await currency_service.get_rates_summary()
    holidays_summary = holidays_service.get_holidays_summary(language)
    
    return {
        "date": date.today().isoformat(),
        "currency": rates_summary,
        "holidays": holidays_summary
    }
