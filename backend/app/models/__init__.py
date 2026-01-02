from __future__ import annotations
# Models module - import all models to register them with SQLAlchemy

from app.models.tenant import Tenant
from app.models.user import User
from app.models.contact import Contact
from app.models.meeting import Meeting
from app.models.meeting_negotiation import MeetingNegotiation
from app.models.task import Task
from app.models.finance import FinanceRecord
from app.models.memory import Memory
from app.models.module_settings import TenantModuleSettings
from app.models.group_chat import GroupChat
from app.models.birthday import Birthday
from app.models.contract import Contract
from app.models.invoice import Invoice
from app.models.whatsapp_instance import WhatsAppInstance, InstanceStatus
from app.models.chat import Message
from app.models.trace import Trace
from app.models.idea import Idea

__all__ = [
    "Tenant",
    "User", 
    "Contact",
    "Meeting",
    "MeetingNegotiation",
    "Task",
    "FinanceRecord",
    "Memory",
    "TenantModuleSettings",
    "GroupChat",
    "Birthday",
    "Contract",
    "Invoice",
    "WhatsAppInstance",
    "InstanceStatus",
    "Message",
    "Trace",
    "Idea",
]
