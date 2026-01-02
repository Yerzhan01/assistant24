from __future__ import annotations
"""Embedding service for RAG memory system using Google text-embedding-004."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import google.generativeai as genai
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.memory import Memory, MemoryType

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings and managing semantic memory.
    Uses Google's text-embedding-004 model for 768-dimensional vectors.
    """
    
    EMBEDDING_MODEL = "models/text-embedding-004"
    EMBEDDING_DIMENSION = 768
    
    def __init__(self, db: AsyncSession, api_key:Optional[ str ] = None):
        self.db = db
        self.api_key = api_key or settings.gemini_api_key
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text using text-embedding-004.
        Returns 768-dimensional vector.
        """
        try:
            result = genai.embed_content(
                model=self.EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return zero vector as fallback
            return [0.0] * self.EMBEDDING_DIMENSION
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for search query.
        Uses retrieval_query task type for better search results.
        """
        try:
            result = genai.embed_content(
                model=self.EMBEDDING_MODEL,
                content=query,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            return [0.0] * self.EMBEDDING_DIMENSION
    
    async def store_memory(
        self,
        tenant_id: UUID,
        content: str,
        content_type: str = MemoryType.MESSAGE.value,
        summary:Optional[ str ] = None,
        user_id:Optional[ UUID ] = None,
        contact_id:Optional[ UUID ] = None,
        source: str = "whatsapp",
        reference_type:Optional[ str ] = None,
        reference_id:Optional[ UUID ] = None,
        metadata:Optional[ Dict[str, Any] ] = None
    ) -> Memory:
        """
        Store content with its embedding in the memory database.
        """
        # Generate embedding
        embedding = await self.embed_text(content)
        
        # Create memory record
        memory = Memory(
            tenant_id=tenant_id,
            user_id=user_id,
            contact_id=contact_id,
            content_type=content_type,
            content=content,
            summary=summary or content[:500] if len(content) > 500 else None,
            embedding=embedding,
            source=source,
            reference_type=reference_type,
            reference_id=reference_id,
            metadata_json=json.dumps(metadata) if metadata else None
        )
        
        self.db.add(memory)
        await self.db.flush()
        
        logger.info(f"Stored memory {memory.id} ({content_type}) for tenant {tenant_id}")
        return memory
    
    async def search_memories(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 5,
        content_types:Optional[ List[str] ] = None,
        contact_id:Optional[ UUID ] = None,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for relevant memories using cosine similarity.
        Returns list of memories with similarity scores.
        """
        # Generate query embedding
        query_embedding = await self.embed_query(query)
        
        # Build query with vector similarity
        # Using pgvector's <=> operator for cosine distance
        # Lower distance = higher similarity, so we use 1 - distance
        
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        sql = text("""
            SELECT 
                id,
                content_type,
                content,
                summary,
                source,
                contact_id,
                reference_type,
                reference_id,
                created_at,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM memories
            WHERE tenant_id = :tenant_id
            AND 1 - (embedding <=> :embedding::vector) > :min_similarity
            {}
            {}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """.format(
            "AND content_type = ANY(:content_types)" if content_types else "",
            "AND contact_id = :contact_id" if contact_id else ""
        ))
        
        params = {
            "tenant_id": str(tenant_id),
            "embedding": embedding_str,
            "min_similarity": min_similarity,
            "limit": limit
        }
        
        if content_types:
            params["content_types"] = content_types
        if contact_id:
            params["contact_id"] = str(contact_id)
        
        result = await self.db.execute(sql, params)
        rows = result.fetchall()
        
        memories = []
        for row in rows:
            memories.append({
                "id": row.id,
                "content_type": row.content_type,
                "content": row.content,
                "summary": row.summary,
                "source": row.source,
                "contact_id": row.contact_id,
                "reference_type": row.reference_type,
                "reference_id": row.reference_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "similarity": float(row.similarity)
            })
        
        return memories
    
    async def get_context_for_query(
        self,
        tenant_id: UUID,
        query: str,
        max_context_length: int = 2000
    ) -> str:
        """
        Build context string from relevant memories for AI prompt.
        Returns formatted context with sources.
        """
        memories = await self.search_memories(
            tenant_id=tenant_id,
            query=query,
            limit=5,
            min_similarity=0.4
        )
        
        if not memories:
            return ""
        
        context_parts = []
        total_length = 0
        
        for mem in memories:
            # Format each memory
            created = mem.get("created_at", "")[:10] if mem.get("created_at") else "неизвестно"
            content_type = mem.get("content_type", "запись")
            content = mem.get("content", "")
            
            entry = f"[{content_type}, {created}]: {content}"
            
            if total_length + len(entry) > max_context_length:
                break
            
            context_parts.append(entry)
            total_length += len(entry)
        
        return "\n---\n".join(context_parts)
    
    async def store_conversation_memory(
        self,
        tenant_id: UUID,
        user_message: str,
        bot_response: str,
        user_id:Optional[ UUID ] = None,
        contact_id:Optional[ UUID ] = None,
        source: str = "whatsapp"
    ) -> Memory:
        """
        Store a conversation exchange as a single memory entry.
        Combines user message and bot response for full context.
        """
        combined = f"Пользователь: {user_message}\nОтвет: {bot_response}"
        
        return await self.store_memory(
            tenant_id=tenant_id,
            content=combined,
            content_type=MemoryType.MESSAGE.value,
            summary=user_message[:200] if len(user_message) > 200 else user_message,
            user_id=user_id,
            contact_id=contact_id,
            source=source
        )
    
    async def store_meeting_memory(
        self,
        tenant_id: UUID,
        meeting_title: str,
        meeting_notes: str,
        attendee_name: str,
        meeting_date: datetime,
        contact_id:Optional[ UUID ] = None,
        meeting_id:Optional[ UUID ] = None
    ) -> Memory:
        """Store meeting details as searchable memory."""
        content = f"Встреча: {meeting_title}\nС кем: {attendee_name}\nДата: {meeting_date.strftime('%d.%m.%Y %H:%M')}\nЗаметки: {meeting_notes}"
        
        return await self.store_memory(
            tenant_id=tenant_id,
            content=content,
            content_type=MemoryType.MEETING.value,
            summary=f"Встреча с {attendee_name}: {meeting_title}",
            contact_id=contact_id,
            reference_type="meeting",
            reference_id=meeting_id,
            metadata={"attendee": attendee_name, "date": meeting_date.isoformat()}
        )
    
    async def store_agreement_memory(
        self,
        tenant_id: UUID,
        agreement_text: str,
        parties: str,
        contact_id:Optional[ UUID ] = None
    ) -> Memory:
        """Store agreement/decision as searchable memory."""
        content = f"Договорённость с {parties}: {agreement_text}"
        
        return await self.store_memory(
            tenant_id=tenant_id,
            content=content,
            content_type=MemoryType.AGREEMENT.value,
            summary=f"Договорённость: {agreement_text[:100]}",
            contact_id=contact_id
        )
