import { useState } from 'react'

export default function UrlForm({ onSubmit, loading }) {
  const [url, setUrl] = useState('')
  const [error, setError] = useState('')

  function validate(val) {
    return /youtube\.com\/watch\?v=|youtu\.be\//.test(val)
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!validate(url)) {
      setError('Podaj poprawny link YouTube (youtube.com/watch?v=... lub youtu.be/...)')
      return
    }
    setError('')
    onSubmit(url.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={url}
          onChange={e => { setUrl(e.target.value); setError('') }}
          placeholder="Wklej link YouTube…"
          disabled={loading}
          className="flex-1 bg-card border border-border rounded-lg px-4 py-3 text-white
                     placeholder-subtle focus:outline-none focus:border-primary
                     disabled:opacity-50 text-sm"
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="px-6 py-3 bg-primary hover:bg-primary-dark text-white font-bold
                     rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed
                     text-sm whitespace-nowrap"
        >
          {loading ? 'Analizuję…' : 'Analizuj'}
        </button>
      </div>
      {error && <p className="text-red-400 text-xs">{error}</p>}
    </form>
  )
}
