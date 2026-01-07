from __future__ import annotations
"""
Kazakhstan Holidays Service
Knows all national and religious holidays in Kazakhstan
Helps avoid scheduling meetings on holidays
"""

from datetime import date, timedelta
from typing import List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class HolidayType(Enum):
    NATIONAL = "national"       # Государственный праздник
    RELIGIOUS = "religious"     # Религиозный праздник
    PROFESSIONAL = "professional"  # Профессиональный праздник


@dataclass
class Holiday:
    name_ru: str
    name_kz: str
    date: date
    holiday_type: HolidayType
    is_day_off: bool = True  # Выходной день


class KazakhstanHolidays:
    """
    Kazakhstan National Holidays Calendar
    Includes fixed and floating holidays (Eid)
    """
    
    def __init__(self):
        pass
    
    def get_fixed_holidays(self, year: int) -> List[Holiday]:
        """Get fixed-date national holidays for a year"""
        return [
            Holiday(
                name_ru="Новый год",
                name_kz="Жаңа жыл",
                date=date(year, 1, 1),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="Новый год (2-й день)",
                name_kz="Жаңа жыл (2-ші күн)",
                date=date(year, 1, 2),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="Международный женский день",
                name_kz="Халықаралық әйелдер күні",
                date=date(year, 3, 8),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="Наурыз мейрамы",
                name_kz="Наурыз мейрамы",
                date=date(year, 3, 21),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="Наурыз мейрамы (2-й день)",
                name_kz="Наурыз мейрамы (2-ші күн)",
                date=date(year, 3, 22),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="Наурыз мейрамы (3-й день)",
                name_kz="Наурыз мейрамы (3-ші күн)",
                date=date(year, 3, 23),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="Праздник единства народа Казахстана",
                name_kz="Қазақстан халқының бірлігі күні",
                date=date(year, 5, 1),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="День защитника Отечества",
                name_kz="Отан қорғаушы күні",
                date=date(year, 5, 7),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="День Победы",
                name_kz="Жеңіс күні",
                date=date(year, 5, 9),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="День столицы",
                name_kz="Астана күні",
                date=date(year, 7, 6),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="День Конституции",
                name_kz="Конституция күні",
                date=date(year, 8, 30),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="День Республики",
                name_kz="Республика күні",
                date=date(year, 10, 25),
                holiday_type=HolidayType.NATIONAL
            ),
            Holiday(
                name_ru="День Независимости",
                name_kz="Тәуелсіздік күні",
                date=date(year, 12, 16),
                holiday_type=HolidayType.NATIONAL
            ),
        ]
    
    def get_islamic_holidays(self, year: int) -> List[Holiday]:
        """
        Get Islamic holidays (approximate dates)
        These dates shift each year by ~11 days
        """
        # Approximate dates for common years
        # In production, use a proper Hijri calendar library
        eid_dates = {
            2024: {
                "kurban": date(2024, 6, 16),
                "oraza": date(2024, 4, 10),
            },
            2025: {
                "kurban": date(2025, 6, 6),
                "oraza": date(2025, 3, 30),
            },
            2026: {
                "kurban": date(2026, 5, 27), # Corrected per eGov
                "oraza": date(2026, 3, 20),
            },
            2027: {
                "kurban": date(2027, 5, 16),
                "oraza": date(2027, 3, 9),
            },
        }
        
        holidays = []
        
        if year in eid_dates:
            dates = eid_dates[year]
            
            holidays.append(Holiday(
                name_ru="Ораза Айт",
                name_kz="Ораза Айт",
                date=dates["oraza"],
                holiday_type=HolidayType.RELIGIOUS
            ))
            
            holidays.append(Holiday(
                name_ru="Курбан Айт",
                name_kz="Құрбан Айт",
                date=dates["kurban"],
                holiday_type=HolidayType.RELIGIOUS
            ))
        
        return holidays
    
    def get_all_holidays(self, year: int) -> List[Holiday]:
        """Get all holidays for a specific year"""
        return self.get_fixed_holidays(year) + self.get_islamic_holidays(year)
    
    def is_holiday(self, check_date: date) -> Tuple[bool, Optional[Holiday]]:
        """Check if a date is a holiday"""
        holidays = self.get_all_holidays(check_date.year)
        
        for holiday in holidays:
            if holiday.date == check_date:
                return True, holiday
        
        return False, None
    
    def is_weekend(self, check_date: date) -> bool:
        """Check if a date is a weekend (Saturday or Sunday)"""
        return check_date.weekday() >= 5
    
    def is_working_day(self, check_date: date) -> bool:
        """Check if a date is a working day"""
        if self.is_weekend(check_date):
            return False
        
        is_hol, _ = self.is_holiday(check_date)
        return not is_hol
    
    def get_next_working_day(self, from_date: date) -> date:
        """Get the next working day after a given date"""
        next_day = from_date + timedelta(days=1)
        
        while not self.is_working_day(next_day):
            next_day += timedelta(days=1)
        
        return next_day
    
    def get_upcoming_holidays(self, count: int = 3) -> List[Holiday]:
        """Get next N upcoming holidays"""
        today = date.today()
        current_year = today.year
        
        # Get holidays for current and next year
        holidays = (
            self.get_all_holidays(current_year) +
            self.get_all_holidays(current_year + 1)
        )
        
        # Filter future holidays and sort by date
        future_holidays = [h for h in holidays if h.date >= today]
        future_holidays.sort(key=lambda h: h.date)
        
        return future_holidays[:count]
    
    def check_meeting_date(self, meeting_date: date, language: str = 'ru') -> str:
        """
        Check if a date is suitable for a meeting
        Returns warning message if it's a holiday/weekend
        """
        # Check weekend
        if self.is_weekend(meeting_date):
            day_name = {
                5: "суббота" if language == 'ru' else "сенбі",
                6: "воскресенье" if language == 'ru' else "жексенбі"
            }
            next_working = self.get_next_working_day(meeting_date)
            
            if language == 'ru':
                return (
                    f"⚠️ {meeting_date.strftime('%d.%m.%Y')} — {day_name[meeting_date.weekday()]} (выходной).\n"
                    f"Предлагаю перенести на {next_working.strftime('%d.%m.%Y')} ({self._weekday_name(next_working, language)})?"
                )
            else:
                return (
                    f"⚠️ {meeting_date.strftime('%d.%m.%Y')} — {day_name[meeting_date.weekday()]} (демалыс).\n"
                    f"Кездесуді {next_working.strftime('%d.%m.%Y')} күніне ауыстыруды ұсынамын?"
                )
        
        # Check holiday
        is_hol, holiday = self.is_holiday(meeting_date)
        if is_hol and holiday:
            next_working = self.get_next_working_day(meeting_date)
            
            if language == 'ru':
                return (
                    f"🎉 {meeting_date.strftime('%d.%m.%Y')} — {holiday.name_ru} (выходной).\n"
                    f"Предлагаю перенести на {next_working.strftime('%d.%m.%Y')}?"
                )
            else:
                return (
                    f"🎉 {meeting_date.strftime('%d.%m.%Y')} — {holiday.name_kz} (демалыс).\n"
                    f"Кездесуді {next_working.strftime('%d.%m.%Y')} күніне ауыстыруды ұсынамын?"
                )
        
        return ""  # Date is OK
    
    def _weekday_name(self, d: date, language: str = 'ru') -> str:
        """Get weekday name"""
        weekdays_ru = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
        weekdays_kz = ['дүйсенбі', 'сейсенбі', 'сәрсенбі', 'бейсенбі', 'жұма', 'сенбі', 'жексенбі']
        
        return weekdays_ru[d.weekday()] if language == 'ru' else weekdays_kz[d.weekday()]
    
    def get_holidays_summary(self, language: str = 'ru') -> str:
        """Get summary of upcoming holidays for briefing"""
        holidays = self.get_upcoming_holidays(3)
        
        if language == 'ru':
            lines = ["🗓️ **Ближайшие праздники РК:**"]
            for h in holidays:
                days_until = (h.date - date.today()).days
                lines.append(f"  • {h.date.strftime('%d.%m')} — {h.name_ru} (через {days_until} дн.)")
        else:
            lines = ["🗓️ **Жақындағы мерекелер:**"]
            for h in holidays:
                days_until = (h.date - date.today()).days
                lines.append(f"  • {h.date.strftime('%d.%m')} — {h.name_kz} ({days_until} күннен кейін)")
        
        return "\n".join(lines)


# Singleton instance
_holidays_service: Optional[KazakhstanHolidays] = None


def get_holidays_service() -> KazakhstanHolidays:
    """Get or create holidays service singleton"""
    global _holidays_service
    if _holidays_service is None:
        _holidays_service = KazakhstanHolidays()
    return _holidays_service
