# SlideSmith — AI-Powered Presentation Generator

SlideSmith generates professional PowerPoint presentations from a topic, PDF, or existing PPTX file using a local Llama3 model via Ollama. No cloud AI costs, fully local inference.

---

## Features

- **AI-generated presentations** from a text topic, uploaded PDF, or PPTX file
- **Smart slide layouts** — automatically detects and applies the right layout per slide:
  - Bullet + paragraph, two-column, timeline, stats cards, pie chart, bar chart, full-image
- **Relevant images** fetched from Unsplash (with Picsum fallback)
- **Outline preview** — review and edit slide titles before the full PPT is built
- **Sally AI presenter** — explains slides, generates speaker notes, answers audience Q&A
- **Email sharing** — send the PPTX directly from the app
- **Multi-language** support (15 languages via Llama3)
- **User accounts** — JWT auth, per-user presentation history, delete presentations
- **My Presentations** — view, download, and manage all past generations

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Axios |
| Backend | FastAPI, LangGraph, Python 3.12 |
| AI Model | Llama3 (via Ollama — runs locally) |
| Database | PostgreSQL + SQLAlchemy (async) |
| PPT Generation | python-pptx |
| Image Search | Unsplash API + Picsum fallback |
| Auth | JWT (python-jose) + bcrypt |

---

## Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL running locally
- [Ollama](https://ollama.ai) installed with `llama3` pulled:
  ```bash
  ollama pull llama3
  ```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/slidesmith.git
cd slidesmith
```

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your values (see Environment Variables section)

# Run the backend
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

App runs at `http://localhost:3000`

---

## Environment Variables

Create `backend/.env` with the following:

```env
# JWT Secret — change this in production
SECRET_KEY=your_secret_key_here

# Unsplash API (optional — falls back to Picsum if not set)
# Get a free key at https://unsplash.com/developers
UNSPLASH_ACCESS_KEY=your_unsplash_key

# Email sharing (optional — Gmail app password)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_gmail_app_password

# PostgreSQL database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/slidesmith
```

### Getting a Gmail App Password
1. Enable 2FA on your Google account
2. Go to Google Account → Security → App Passwords
3. Generate a password for "Mail"

---

## Project Structure

```
slidesmith/
├── backend/
│   ├── main.py               # FastAPI app, routes, LangGraph workflow
│   ├── outline_node.py       # Llama3 outline generation
│   ├── ppt_node.py           # PPT assembly logic
│   ├── generate_ppt.py       # python-pptx slide layouts
│   ├── image_node.py         # Parallel image fetching
│   ├── pdf_extraction_node.py# PDF/PPTX content extraction
│   ├── agent_sally.py        # Sally AI presenter
│   ├── auth.py               # JWT + password hashing
│   ├── models.py             # SQLAlchemy models
│   ├── db.py                 # Database config
│   ├── schemas.py            # Pydantic schemas
│   ├── language_utils.py     # Multilingual support
│   ├── presentations/        # Generated PPTX files (local)
│   └── image_cache/          # Cached images
│
└── frontend/
    └── src/
        ├── App.js             # Main app, auth, generation flow
        ├── SlideViewer.js     # Slide viewer modal
        ├── AudienceQA.js      # Audience Q&A panel
        ├── EmailShareModal.js # Email sharing modal
        └── services/
            └── sallyIntegration.js  # Sally API client
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Create account |
| POST | `/login` | Get JWT token |
| GET | `/me` | Current user info |
| POST | `/generate-outline` | Preview slide outline before building |
| POST | `/generate` | Generate full presentation |
| GET | `/my-presentations` | List user's presentations |
| GET | `/presentations/{id}` | Get single presentation |
| DELETE | `/presentations/{id}` | Delete presentation |
| GET | `/download/{path}` | Download PPTX file |
| GET | `/image/{filename}` | Serve cached image |
| POST | `/ai/explain-slide` | Sally explains a slide |
| POST | `/ai/speaker-notes` | Generate speaker notes |
| POST | `/ai/chat` | Chat with Sally |
| POST | `/ai/audience-qa` | Answer audience questions |
| POST | `/share/email` | Email presentation |
| GET | `/health` | Health check |

---

## How It Works

```
User submits topic
       │
       ▼
[outline] → Llama3 generates JSON outline (slide titles + descriptions)
       │
       ▼
[fetch_images] → Unsplash/Picsum fetched in parallel
       │
       ▼
[ppt] → python-pptx builds the PPTX with smart layouts
       │
       ▼
[validate] → File verified, saved to DB, returned to frontend
```

---

## Slide Layouts

SlideSmith automatically picks the best layout per slide:

| Layout | Triggered when |
|--------|---------------|
| Standard bullets | Default content |
| Two-column | 3+ bullets, no paragraph |
| Timeline | Title contains: step, phase, process, workflow, roadmap |
| Stats cards | Slide has numbers/percentages (non-chart) |
| Pie chart | 2+ percentage values detected |
| Bar chart | 2+ comparable numeric values detected |
| Full image | Image available + short description |
| Key Takeaways | Last slide / conclusion |

---

## License

MIT
