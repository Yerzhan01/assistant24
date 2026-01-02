# Цифровой Секретарь | Digital Secretary

🤖 AI-powered digital secretary for Kazakhstan entrepreneurs. Manage finances, meetings, contracts, and more through Telegram or WhatsApp.

## Features

- 🏢 **Multi-tenant SaaS** — Each user connects their own bot
- 🧩 **Modular architecture** — Enable/disable features per tenant
- 🤖 **AI-powered** — Google Gemini for intent classification
- 🌐 **Bilingual** — Kazakh (қазақша) and Russian (русский)
- 📱 **Telegram + WhatsApp** — Multiple messaging platforms

## Modules

| Module | Description |
|--------|-------------|
| 💰 Finance | Track income and expenses |
| 📅 Meetings | Schedule and reminders |
| 📄 Contracts | Business agreements & ESF |
| 💡 Ideas | Business ideas bank |
| 🎂 Birthdays | Birthday reminders |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Google Gemini API key

### 1. Clone and configure

```bash
cd digital-secretary
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start services

```bash
docker-compose up -d
```

### 3. Access

- **Backend API:** http://localhost:8000
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs

## Development

### Backend (Python/FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend (React/Vite)

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Auth
- `POST /api/v1/auth/register` — Register tenant
- `POST /api/v1/auth/login` — Login
- `GET /api/v1/auth/me` — Current tenant

### Modules
- `GET /api/v1/modules` — List modules
- `PATCH /api/v1/modules/{id}` — Toggle module

### Settings
- `POST /api/v1/settings/telegram` — Connect Telegram bot
- `POST /api/v1/settings/whatsapp` — Connect WhatsApp

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** React, TypeScript, Tailwind CSS, Vite
- **AI:** Google Gemini
- **Messaging:** aiogram (Telegram), GreenAPI (WhatsApp)
- **Infrastructure:** Docker, Redis, Celery

## License

MIT
