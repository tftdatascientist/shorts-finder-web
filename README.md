# Shorts Finder Web

Webowe narzędzie dla @AUTOmatyczni — wklej link YouTube, AI wybiera najlepsze momenty na Shorts.

## Live

- **App:** https://shorts-finder-web.pages.dev
- **API:** https://shorts-finder-api.onrender.com

> Pierwsze żądanie po przerwie może zająć ~30s (Render Free budzi instancję).

## Jak działa

1. Wklej link do filmu YouTube
2. Backend pobiera transkrypcję (napisy YT lub Whisper API)
3. GPT-4o-mini analizuje transkrypcję i wybiera 3–6 najlepszych fragmentów
4. Oglądasz każdy fragment w iframe YouTube, akceptujesz lub odrzucasz
5. Eksportujesz zaakceptowane fragmenty jako JSON

## Uruchomienie lokalne

### Backend
```bash
cd backend
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env
uvicorn main:app --reload
# API: http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# App: http://localhost:5173
```

Vite proxy przekieruje `/analyze`, `/stream`, `/results`, `/history` na `localhost:8000`.

## Stack

| Warstwa | Technologia |
|---|---|
| Backend | FastAPI + uvicorn (Python 3.11) |
| Transkrypcja | youtube-transcript-api → OpenAI Whisper API |
| Analiza AI | OpenAI GPT-4o-mini |
| Frontend | React 18 + Vite + Tailwind CSS |
| Hosting backend | Render.com Free |
| Hosting frontend | Cloudflare Pages |

## Deploy

### Backend → Render.com
1. New → Web Service → `tftdatascientist/shorts-finder-web`
2. Root directory: `backend`
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Env var: `OPENAI_API_KEY=sk-...`

### Frontend → Cloudflare Pages
1. Workers & Pages → Create → Pages → Connect to Git
2. Root directory: `frontend`
3. Build command: `npm run build`
4. Output directory: `dist`
5. Env var: `VITE_API_URL=https://shorts-finder-api.onrender.com`

## Koszt

- Hosting: **$0** (Render Free + Cloudflare Pages Free)
- API: OpenAI GPT-4o-mini ~$0.01–0.05 per analiza, Whisper ~$0.006/min audio
