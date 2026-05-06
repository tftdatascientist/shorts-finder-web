const STEPS = ['fetching_meta', 'transcribing', 'analyzing', 'done']

const STEP_LABELS = {
  fetching_meta: 'Metadane',
  transcribing: 'Transkrypcja',
  analyzing: 'Analiza AI',
  done: 'Gotowe',
}

function stepIndex(status) {
  return STEPS.indexOf(status)
}

export default function ProgressStream({ status, message }) {
  const currentIdx = stepIndex(status)
  const isError = status === 'error'

  return (
    <div className="bg-card border border-border rounded-lg p-5 flex flex-col gap-4">
      {/* Pasek kroków */}
      <div className="flex items-center gap-1">
        {STEPS.map((step, idx) => {
          const done = currentIdx > idx
          const active = currentIdx === idx && !isError
          return (
            <div key={step} className="flex items-center gap-1 flex-1">
              <div className={`flex items-center gap-2 flex-1 ${idx > 0 ? 'ml-1' : ''}`}>
                {idx > 0 && (
                  <div className={`h-px flex-1 ${done ? 'bg-primary' : 'bg-border'}`} />
                )}
                <div className={`
                  w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0
                  ${done ? 'bg-primary text-white' : ''}
                  ${active ? 'bg-primary text-white ring-2 ring-primary/40' : ''}
                  ${!done && !active ? 'bg-border text-muted' : ''}
                `}>
                  {done ? '✓' : idx + 1}
                </div>
                <span className={`text-xs hidden sm:block ${active ? 'text-white' : done ? 'text-primary' : 'text-muted'}`}>
                  {STEP_LABELS[step]}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Komunikat bieżący */}
      <div className={`flex items-center gap-2 text-sm ${isError ? 'text-red-400' : 'text-subtle'}`}>
        {!isError && status !== 'done' && (
          <span className="pulse-dot text-primary">●</span>
        )}
        {isError && <span>✗</span>}
        {status === 'done' && <span className="text-success">✓</span>}
        <span>{message}</span>
      </div>
    </div>
  )
}
