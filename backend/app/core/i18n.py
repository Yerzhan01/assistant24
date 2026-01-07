from __future__ import annotations
"""Internationalization (i18n) support for Kazakh and Russian languages."""
import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings


# Locales directory
LOCALES_DIR = Path(__file__).parent.parent.parent / "locales"

# Loaded translations cache
_translations: Dict[str, Dict[str, Any]] = {}


def load_translations() -> None:
    """Load all translation files."""
    global _translations
    
    for lang in ["ru", "kz"]:
        locale_file = LOCALES_DIR / f"{lang}.json"
        if locale_file.exists():
            with open(locale_file, "r", encoding="utf-8") as f:
                _translations[lang] = json.load(f)
        else:
            _translations[lang] = {}


def get_text(key: str, lang:Optional[ str ] = None, **kwargs: Any) -> str:
    """
    Get translated text by key.
    
    Args:
        key: Dot-separated key path (e.g., "bot.welcome")
        lang: Language code ("ru" or "kz"), defaults to settings
        **kwargs: Format string arguments
    
    Returns:
        Translated string or key if not found
    """
    if not _translations:
        load_translations()
    
    language = lang or settings.default_language
    translations = _translations.get(language, {})
    
    # Navigate nested keys
    parts = key.split(".")
    value: Any = translations
    
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return key  # Key not found
    
    if not isinstance(value, str):
        return key
    
    # Format with kwargs if provided
    if kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            return value
    
    return value


def t(key: str, lang:Optional[ str ] = None, **kwargs: Any) -> str:
    """Shorthand for get_text."""
    return get_text(key, lang, **kwargs)


# Module names and descriptions for both languages
MODULE_TRANSLATIONS = {
    "finance": {
        "ru": {"name": "Финансы", "description": "Учёт доходов и расходов", "icon": "💰"},
        "kz": {"name": "Қаржы", "description": "Кірістер мен шығыстарды есепке алу", "icon": "💰"},
    },
    "meeting": {
        "ru": {"name": "Встречи", "description": "Календарь и планирование", "icon": "📅"},
        "kz": {"name": "Кездесулер", "description": "Күнтізбе және жоспарлау", "icon": "📅"},
    },
    "contract": {
        "ru": {"name": "Договоры", "description": "Учёт договоров и ЭСФ", "icon": "📄"},
        "kz": {"name": "Шарттар", "description": "Шарттар мен ЭСФ есебі", "icon": "📄"},
    },
    "ideas": {
        "ru": {"name": "Идеи", "description": "Банк идей с приоритетами", "icon": "💡"},
        "kz": {"name": "Идеялар", "description": "Басымдықтары бар идеялар банкі", "icon": "💡"},
    },
    "birthday": {
        "ru": {"name": "Дни рождения", "description": "Напоминания о праздниках", "icon": "🎂"},
        "kz": {"name": "Туған күндер", "description": "Мерекелер туралы еске салулар", "icon": "🎂"},
    },
    "report": {
        "ru": {"name": "Отчёты", "description": "Аналитика и сводки", "icon": "📊"},
        "kz": {"name": "Есептер", "description": "Талдау және жиынтықтар", "icon": "📊"},
    },
}


def get_module_info(module_id: str, lang: str = "ru") -> Dict[str, str]:
    """Get module name and description in specified language."""
    module = MODULE_TRANSLATIONS.get(module_id, {})
    return module.get(lang, {"name": module_id, "description": "", "icon": "📦"})
