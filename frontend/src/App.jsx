import { useState, useCallback } from 'react'
import UrlForm from './components/UrlForm'
import ProgressStream from './components/ProgressStream'
import ProposalCard from './components/ProposalCard'
import AcceptedList from './components/AcceptedList'
import HistoryPanel from './components/HistoryPanel'
import { startAnalysis, fetchResults, openStream } from './api'

const STATE = {
  IDLE: 'idle',
  LOADING: 'loading',
  STREAMING: 'streaming',
  DONE: 'done',
  ERROR: 'error',
}

export default function App() {
  const [state, setState] = useState(STATE.IDLE)
  const [streamStatus, setStreamStatus] = useState({ status: '', message: '' })
  const [results, setResults] = useState(null)
  const [accepted, setAccepted] = useState(new Set())
  const [rejected, setRejected] = useState(new Set())
  const [errorMsg, setErrorMsg] = useState('')

  const handleSubmit = useCallback(async (url) => {
    setState(STATE.LOADING)
    setResults(null)
    setAccepted(new Set())
    setRejected(new Set())
    setErrorMsg('')
    setStreamStatus({ status: 'pending', message: 'Uruchamiam analizę…' })

    try {
      const { session_id } = await startAnalysis(url)
      setState(STATE.STREAMING)

      const closeStream = openStream(
        session_id,
        (data) => setStreamStatus({ status: data.status, message: data.message }),
        async () => {
          const data = await fetchResults(session_id)
          if (data.status === 'error') {
            setErrorMsg(data.error_msg || 'Nieznany błąd serwera.')
            setStreamStatus({ status: 'error', message: data.error_msg || 'Błąd' })
            setState(STATE.ERROR)
          } else {
            setResults(data)
            setStreamStatus({ status: 'done', message: `Gotowe — ${data.proposals.length} propozycji` })
            setState(STATE.DONE)
          }
        }
      )

      return closeStream
    } catch (err) {
      setErrorMsg(err.message)
      setStreamStatus({ status: 'error', message: err.message })
      setState(STATE.ERROR)
    }
  }, [])

  const handleHistorySelect = useCallback(async (sessionId) => {
    setState(STATE.LOADING)
    setStreamStatus({ status: 'fetching_meta', message: 'Wczytuję wyniki…' })
    try {
      const data = await fetchResults(sessionId)
      setResults(data)
      setAccepted(new Set())
      setRejected(new Set())
      setStreamStatus({ status: 'done', message: `Wczytano — ${data.proposals.length} propozycji` })
      setState(STATE.DONE)
    } catch {
      setState(STATE.IDLE)
    }
  }, [])

  const isLoading = state === STATE.LOADING || state === STATE.STREAMING

  return (
    <div className="min-h-screen bg-bg text-white">
      {/* Header */}
      <header className="border-b border-border px-6 py-4 flex items-center gap-3">
        <div className="w-2 h-6 bg-primary rounded-full" />
        <h1 className="text-white font-bold text-lg tracking-tight">Shorts Finder</h1>
        <span className="text-subtle text-sm">@AUTOmatyczni</span>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 flex flex-col gap-6">
        {/* Formularz */}
        <section className="flex flex-col gap-3">
          <UrlForm onSubmit={handleSubmit} loading={isLoading} />
          <div className="flex justify-end">
            <HistoryPanel onSelect={handleHistorySelect} />
          </div>
        </section>

        {/* Postęp */}
        {(state === STATE.STREAMING || state === STATE.LOADING || state === STATE.ERROR) && (
          <ProgressStream status={streamStatus.status} message={streamStatus.message} />
        )}

        {/* Wyniki */}
        {state === STATE.DONE && results && (
          <section className="flex flex-col gap-4">
            {/* Info o filmie */}
            <div className="flex items-center gap-3 pb-1 border-b border-border">
              <div className="flex-1">
                <p className="text-white font-semibold text-sm">{results.video_title}</p>
                <a
                  href={results.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary text-xs hover:underline"
                >
                  Otwórz na YouTube ↗
                </a>
              </div>
              <span className="text-subtle text-xs">
                {results.proposals.length} propozycji
              </span>
            </div>

            {/* Zaakceptowane */}
            <AcceptedList proposals={results.proposals} accepted={accepted} />

            {/* Karty propozycji */}
            <div className="flex flex-col gap-4">
              {results.proposals.map((p, i) => (
                <ProposalCard
                  key={i}
                  index={i}
                  proposal={p}
                  videoId={results.video_id}
                  accepted={accepted.has(i)}
                  rejected={rejected.has(i)}
                  onAccept={() => setAccepted(prev => new Set([...prev, i]))}
                  onReject={() => setRejected(prev => new Set([...prev, i]))}
                />
              ))}
            </div>

            <button
              onClick={() => setState(STATE.IDLE)}
              className="text-xs text-subtle hover:text-primary transition-colors self-center mt-2"
            >
              ← Analizuj inny film
            </button>
          </section>
        )}

        {/* Stan pusty */}
        {state === STATE.IDLE && (
          <div className="text-center text-subtle text-sm py-12">
            Wklej link do filmu YouTube i kliknij <strong className="text-white">Analizuj</strong>.<br />
            AI wybierze najlepsze momenty na Shorts.
          </div>
        )}
      </main>
    </div>
  )
}
