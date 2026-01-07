# System Architecture & Logic: Digital Secretary
> **Version**: 2.1 (Production Grade)  
> **Date**: January 2026

## 1. High-Level Overview
Digital Secretary is an autonomous **Multi-Agent System** acting as a business assistant. Unlike simple chatbots, it uses a **Loop-based Agent Runtime** to reason, plan, and execute complex multi-step tasks across various domains (Finance, Calendar, CRM).

### Core Components
1.  **Backend (Brain)**: Python (FastAPI) + Google Gemini  (Logic).
2.  **Agent Runtime**: Orchestrates specialized agents.
3.  **Frontend**: React + Tailwind (Management Dashboard).
4.  **Integrations**: WhatsApp (GreenAPI), Telegram (Aiogram), Perplexity (Search).
5.  **Infrastructure**: Docker, PostgreSQL (Source of Truth), Redis (Queue/Cache).

---

## 2. System Contracts & Data Flow

### 2.1. Unified Execution Schema
Every action in the system follows a strict `AgentRun` contract to ensure observability and debugging.

```json
{
  "trace_id": "UUID (Correlation ID)",
  "tenant_id": "UUID",
  "source": "whatsapp | telegram | web",
  "input": {
    "message": "User text",
    "context": "Previous conversation summary"
  },
  "steps": [
    {
      "step_id": 1,
      "agent": "FinanceAgent",
      "tool": "create_transaction",
      "args": { "amount": 5000, "category": "Taxi" },
      "result": "Transaction ID: 123",
      "status": "success",
      "duration_ms": 145
    }
  ],
  "final_output": "Response text",
  "status": "completed" // running, failed, cancelled
}
```

### 2.2. Reliability & Safety
*   **Max Hops:** `runtime.max_hops = 10`. Prevents infinite loops between agents.
*   **Timeouts:** Tools have a 30s hard timeout.
*   **Partial Failures:** If non-critical tools fail (e.g., Knowledge Search), the system degrades gracefully: "I couldn't find the phone number, but I created the task."
*   **PII Policy:** Logs are sanitized. Phone numbers and sensitive data in `trace` logs should be masked (Implementation Pending).

---

## 3. The Logic: Agent Runtime ("The Loop")
The heart of the intelligence is located in `backend/app/agents/runtime.py`.

### 3.1. Routing Logic (ChiefOfStaff)
The `ChiefOfStaffAgent` acts as the router.
*   **Input**: User message + History.
*   **Logic**: Multi-intent classification using Gemini.
*   **Priority**: 
    1.  **Safety/Blockers** (e.g., "Stop", "Cancel").
    2.  **Transactional** (Finance, Calendar).
    3.  **Informational** (Knowledge, Ideas).

### 3.2. Execution Flow
1.  **Input**: User sends "Find Rixos phone and book a meeting".
2.  **Step 1 (Handoff)**: Chief -> `KnowledgeAgent`.
3.  **Step 2 (Tool)**: `KnowledgeAgent` calls `PerplexityClient.search("Rixos phone")`.
    *   *Result*: `+77771234567`.
4.  **Context Injection**: Runtime passes result to next step.
5.  **Step 3 (Handoff)**: Runtime -> `CalendarAgent`.
6.  **Step 4 (Tool)**: `CalendarAgent` calls `create_event(phone="+77771234567")`.

---

## 4. Agents & Tools Catalog (Capabilities)

| Agent | Responsibility | Key Tools |
|-------|----------------|-----------|
| **Chief** | Orchestration | `handoff_to_*` |
| **Finance** | Money | `add_transaction`, `get_balance`, `generate_invoice` |
| **Tasks** | Productivity | `create_task`, `list_tasks`, `complete_task` |
| **Calendar** | Scheduling | `create_event`, `check_availability`, `cancel_event` |
| **Birthday** | Relationships| `add_birthday`, `get_upcoming` |
| **Knowledge**| Research | `deep_search` (Perplexity) |
| **Contacts** | CRM | `save_contact`, `find_contact` |

*Tool Definition*: A deterministic function with JSON Schema input and strict return type.

---

## 5. Integrations & Idempotency

### 5.1. WhatsApp (Green API)
*   **Inbound**: Webhook.
*   **Idempotency**: `messageId` from GreenAPI is stored in Redis (TTL 24h). Duplicate webhooks are discarded.
*   **Retry Policy**: GreenAPI retries webhooks. Backend handles `409 Conflict` gracefully.

### 5.2. Background Workers (Celery)
*   **Meeting Reminders**:
    *   Frequency: Every 1 min.
    *   **Guarantee**: `Meeting.reminders_sent` (JSON) flag in DB prevents double sending.
    *   Logic: `Checking window: [Now, Now + 2h]`.
*   **Brain Tick**: 
    *   Proactive agent.
    *   **Quiet Hours**: Disabled 22:00 - 08:00 (User TZ).
    *   **Opt-out**: Configurable in Tenant Settings.

---

## 6. Data & RAG Strategy
*   **Source of Truth**: PostgreSQL (Users, Tasks, Transactions).
*   **Index**: ChromaDB / Vector Store (Embeddings of chats & docs).
*   **Retrieval Policy**:
    *   **Strict Filtering**: `search(query, filter={tenant_id: ...})`. NO cross-tenant data leakage.
    *   **Strategy**: Retrieve Top-3 relevant chunks + Last 10 messages history.

---

## 7. Non-Functional Requirements
*   **SLO**: API Responses < 200ms (excluding AI generation). AI streaming start < 3s.
*   **Scaling**: Stateless Backend. Horizontal scaling via Docker Swarm/K8s.
*   **Security**: 
    *   Secrets in `GitHub Secrets` / `.env`. 
    *   RBAC in Dashboard (Admin vs Viewer - *Planned*).

---

## 8. Development Lifecycle
*   **Prompts**: Stored as Code (`agents/*.py`). Versioned via Git.
*   **Rollback**: `git revert`.
