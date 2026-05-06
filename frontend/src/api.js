const BASE = import.meta.env.VITE_API_URL || ''

export async function startAnalysis(url) {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Błąd serwera ${res.status}`)
  }
  return res.json() // { session_id }
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
