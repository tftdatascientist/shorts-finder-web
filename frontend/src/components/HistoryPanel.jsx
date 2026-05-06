import { useEffect, useState } from 'react'
import { fetchHistory } from '../api'

export default function HistoryPanel({ onSelect }) {
  const [history, setHistory] = useState([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (open) fetchHistory().then(setHistory).catch(() => {})
  }, [open])

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-xs text-subtle hover:text-primary transition-colors"
      >
        Historia analiz ▾
      </button>
    )
  }

  return (
    <div className="bg-card border border-border rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted font-bold tracking-wide">HISTORIA ANALIZ</span>
        <button onClick={() => setOpen(false)} className="text-muted hover:text-white text-xs">✕</button>
      </div>
      {history.length === 0 && <p className="text-subtle text-xs">Brak historii w tej sesji.</p>}
      {history.map(item => (
        <button
          key={item.session_id}
          onClick={() => { onSelect(item.session_id); setOpen(false) }}
          className="text-left text-xs p-2 rounded-lg hover:bg-card-hover transition-colors flex items-center gap-3"
        >
          <span className={`shrink-0 ${item.status === 'done' ? 'text-success' : 'text-red-400'}`}>
            {item.status === 'done' ? '✓' : '✗'}
          </span>
          <span className="flex-1 text-white truncate">{item.video_title}</span>
          <span className="text-muted shrink-0">{item.proposals_count} prop.</span>
        </button>
      ))}
    </div>
  )
}
