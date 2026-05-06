function fmtS(seconds) {
  const s = Math.floor(seconds)
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

export default function AcceptedList({ proposals, accepted }) {
  const items = proposals.filter((_, i) => accepted.has(i))
  if (items.length === 0) return null

  function exportJson() {
    const data = items.map(p => ({
      title: p.title,
      start_s: p.start_s,
      end_s: p.end_s,
      duration_s: p.duration_s,
      reason: p.reason,
    }))
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'shorts_fragments.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="bg-card border border-success/30 rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-success font-bold text-sm tracking-wide">
          WYBRANE FRAGMENTY ({items.length})
        </h3>
        <button
          onClick={exportJson}
          className="text-xs px-3 py-1.5 border border-border rounded-lg text-muted
                     hover:border-primary hover:text-primary transition-colors"
        >
          Eksportuj JSON
        </button>
      </div>
      <ul className="flex flex-col gap-1">
        {items.map((p, i) => (
          <li key={i} className="text-xs text-white flex items-center gap-2">
            <span className="text-success">✓</span>
            <span className="text-muted">{fmtS(p.start_s)}→{fmtS(p.end_s)}</span>
            <span>{p.title}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
