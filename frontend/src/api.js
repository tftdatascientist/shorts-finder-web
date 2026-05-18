const BASE = import.meta.env.VITE_API_URL || ''

const WAKE_UP_STATUSES = new Set([503, 502, 504])
const RETRY_DELAY_MS = 8000
const MAX_RETRIES = 5

export async function startAnalysis(url, onWakingUp) {
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const res = await fetch(`${BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })

    if (res.ok) return res.json() // { session_id }

    if (WAKE_UP_STATUSES.has(res.status) && attempt < MAX_RETRIES) {
      const eta = Math.round((RETRY_DELAY_MS * (MAX_RETRIES - attempt)) / 1000)
      onWakingUp?.(`Serwer się wybudza… (próba ${attempt + 1}/${MAX_RETRIES}, ~${eta}s)`)
      await new Promise(r => setTimeout(r, RETRY_DELAY_MS))
      continue
    }

    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Błąd serwera ${res.status}`)
  }
  throw new Error('Serwer nie odpowiada — spróbuj za chwilę.')
}

export async function fetchResults(sessionId) {
  const res = await fetch(`${BASE}/results/${sessionId}`)
  if (!res.ok) throw new Error(`Błąd pobierania wyników: ${res.status}`)
  return res.json()
}

export async function fetchHistory() {
  const res = await fetch(`${BASE}/history`)
  if (!res.ok) return []
  return res.json()
}

export function openStream(sessionId, onMessage, onEnd) {
  const url = `${BASE}/stream/${sessionId}`
  const es = new EventSource(url)
  es.onmessage = (e) => {
    const data = JSON.parse(e.data)
    if (data.status === 'stream_end') {
      es.close()
      onEnd()
    } else {
      onMessage(data)
    }
  }
  es.onerror = () => { es.close(); onEnd() }
  return () => es.close()
}
