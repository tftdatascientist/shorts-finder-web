# Shorts Finder Web

Webowe narzędzie dla @AUTOmatyczni — wklej link YouTube, AI wybiera najlepsze momenty na Shorts.

## Uruchomienie lokalne

### Backend
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # wpisz OPENAI_API_KEY
uvicorn main:app --reload
# API dostępne na http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# App dostępna na http://localhost:5173
```

## Deploy

### Backend → Render.com
1. Utwórz konto na render.com
2. New → Web Service → połącz z repo GitHub
3. Root directory: `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Environment → dodaj `OPENAI_API_KEY`
7. Plan: Free

### Frontend → Cloudflare Pages
1. Utwórz konto na cloudflare.com
2. Pages → Create project → połącz z repo GitHub
3. Root directory: `frontend`
4. Build command: `npm run build`
5. Output directory: `dist`
6. Environment variable: `VITE_API_URL=https://<twoja-nazwa>.onrender.com`

### Subdomena shorts.automatyczni.sklep.pl
W panelu DNS Cyber Folks dodaj rekord:
```
CNAME  shorts  <twoja-nazwa>.pages.dev
```

## Stack
- **Backend:** FastAPI + yt-dlp + OpenAI (Whisper + GPT-4o-mini)
- **Frontend:** React + Vite + Tailwind CSS
- **Hosting:** Render.com Free (backend) + Cloudflare Pages (frontend)
- **Koszt:** $0 (tylko API OpenAI per użycie)
