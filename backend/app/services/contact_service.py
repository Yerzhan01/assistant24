from __future__ import annotations
"""Contact service - Finding and managing contacts for meeting invitations."""
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact


class ContactService:
    """
    Service for managing contacts and finding matches for AI-extracted names.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_by_name(
        self, 
        tenant_id: UUID, 
        name: str
    ) ->Optional[ Contact ]:
        """
        Find contact by name or alias.
        Uses fuzzy matching for better AI integration.
        """
        name_lower = name.lower().strip()
        
        # First try exact match on name
        stmt = select(Contact).where(
            and_(
                Contact.tenant_id == tenant_id,
                func.lower(Contact.name) == name_lower
            )
        )
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()
        if contact:
            return contact
        
        # Try partial match
        stmt = select(Contact).where(
            and_(
                Contact.tenant_id == tenant_id,
                Contact.name.ilike(f"%{name}%")
            )
        )
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()
        if contact:
            return contact
        
        # Try aliases
        stmt = select(Contact).where(
            and_(
                Contact.tenant_id == tenant_id,
                Contact.aliases.any(name)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def find_by_phone(
        self, 
        tenant_id: UUID, 
        phone: str
    ) ->Optional[ Contact ]:
        """Find contact by phone number."""
        # Clean phone
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        
        stmt = select(Contact).where(
            and_(
                Contact.tenant_id == tenant_id,
                Contact.phone == clean_phone
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_contact(
        self,
        tenant_id: UUID,
        name: str,
        phone: str,
        source: str = "auto_extracted",
        **extra_fields
    ) -> Contact:
        """Create a new contact."""
        # Clean phone
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        
        contact = Contact(
            tenant_id=tenant_id,
            name=name,
            phone=clean_phone,
            source=source,
            **extra_fields
        )
        
        self.db.add(contact)
        await self.db.flush()
        
        return contact
    
    async def get_or_create(
        self,
        tenant_id: UUID,
        name: str,
        phone:Optional[ str ] = None
    ) -> tuple[Optional[Contact], bool]:
        """
        Get existing contact or create a new one.
        Returns (contact, was_created).
        If no phone and no match, returns (None, False).
        """
        # Try to find by phone first
        if phone:
            contact = await self.find_by_phone(tenant_id, phone)
            if contact:
                return contact, False
        
        # Try to find by name
        contact = await self.find_by_name(tenant_id, name)
        if contact:
            return contact, False
        
        # Create new if we have phone
        if phone:
            contact = await self.create_contact(tenant_id, name, phone)
            return contact, True
        
        return None, False
    
    async def add_alias(
        self, 
        contact: Contact, 
        alias: str
    ) -> Contact:
        """Add an alias to a contact."""
        if not contact.aliases:
            contact.aliases = []
        
        alias_lower = alias.lower().strip()
        if alias_lower not in [a.lower() for a in contact.aliases]:
            contact.aliases = [*contact.aliases, alias]
        
        return contact
    
    async def list_contacts(
        self,
        tenant_id: UUID,
        search:Optional[ str ] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Contact]:
        """List contacts with optional search."""
        stmt = select(Contact).where(Contact.tenant_id == tenant_id)
        
        if search:
            stmt = stmt.where(
                or_(
                    Contact.name.ilike(f"%{search}%"),
                    Contact.phone.ilike(f"%{search}%"),
                    Contact.company.ilike(f"%{search}%")
                )
            )
        
        stmt = stmt.order_by(Contact.name).limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
