import { useState } from 'react'

function fmtS(seconds) {
  const s = Math.floor(seconds)
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

export default function ProposalCard({ index, proposal, videoId, onAccept, onReject, accepted, rejected }) {
  const [playing, setPlaying] = useState(false)
  const { title, start_s, end_s, duration_s, reason } = proposal

  const iframeSrc = playing
    ? `https://www.youtube.com/embed/${videoId}?start=${Math.floor(start_s)}&end=${Math.ceil(end_s)}&autoplay=1&rel=0`
    : null

  const borderColor = accepted
    ? 'border-success'
    : rejected
    ? 'border-red-800 opacity-60'
    : 'border-border hover:border-primary/50'

  return (
    <div className={`bg-card border ${borderColor} rounded-xl p-5 flex flex-col gap-4 transition-all`}>
      {/* Nagłówek */}
      <div className="flex items-start gap-3">
        <span className="text-primary font-bold text-lg shrink-0">#{index + 1}</span>
        <div className="flex-1">
          <h3 className="text-white font-bold text-sm leading-snug">{title}</h3>
          <p className="text-muted text-xs mt-1">
            ▶ {fmtS(start_s)} → ■ {fmtS(end_s)}
            <span className="ml-2 text-subtle">({duration_s.toFixed(1)}s)</span>
          </p>
        </div>
        {accepted && <span className="text-success text-sm font-bold shrink-0">✓ Dodano</span>}
        {rejected && <span className="text-red-500 text-sm shrink-0">✗</span>}
      </div>

      {/* Uzasadnienie */}
      {reason && (
        <p className="text-subtle text-xs italic leading-relaxed">{reason}</p>
      )}

      {/* Odtwarzacz */}
      {playing && iframeSrc ? (
        <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
          <iframe
            className="absolute inset-0 w-full h-full rounded-lg"
            src={iframeSrc}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope"
            allowFullScreen
          />
        </div>
      ) : (
        <button
          onClick={() => setPlaying(true)}
          className="w-full bg-[#1a1a40] hover:bg-[#22225a] border border-border rounded-lg
                     py-8 text-primary text-2xl transition-colors"
          title="Odtwórz podgląd"
        >
          ▶
        </button>
      )}

      {/* Akcje */}
      {!accepted && !rejected && (
        <div className="flex gap-2">
          <button
            onClick={() => setPlaying(p => !p)}
            className="flex-1 py-2 text-xs border border-border rounded-lg text-muted
                       hover:border-primary hover:text-primary transition-colors"
          >
            {playing ? '■ Stop' : '▶ Podgląd'}
          </button>
          <button
            onClick={onReject}
            className="px-4 py-2 text-xs border border-red-800 rounded-lg text-red-400
                       hover:bg-red-900/30 transition-colors"
          >
            ✗ Odrzuć
          </button>
          <button
            onClick={onAccept}
            className="flex-1 py-2 text-xs bg-success-dark border border-success rounded-lg
                       text-success font-bold hover:bg-success/20 transition-colors"
          >
            ✓ Dodaj
          </button>
        </div>
      )}
    </div>
  )
}
