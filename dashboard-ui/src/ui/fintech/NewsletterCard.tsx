import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'

const LS_KEY = 'arb_newsletter_queue'

export function NewsletterCard({ variant = 'light' }: { variant?: 'light' | 'dark' }) {
  const formId = (import.meta.env.VITE_FORMSPREE_ID as string | undefined)?.trim()
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'ok' | 'err'>('idle')
  const action = formId ? `https://formspree.io/f/${formId}` : ''

  const dark = variant === 'dark'

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!action) {
      setStatus('err')
      return
    }
    setStatus('loading')
    try {
      const fd = new FormData()
      fd.append('email', email)
      const res = await fetch(action, { method: 'POST', body: fd, headers: { Accept: 'application/json' } })
      const j = (await res.json().catch(() => ({}))) as { ok?: boolean }
      if (res.ok || j.ok) {
        setStatus('ok')
        try {
          const prev = JSON.parse(localStorage.getItem(LS_KEY) || '[]') as string[]
          prev.push(email.trim())
          localStorage.setItem(LS_KEY, JSON.stringify(prev))
        } catch {
          /* ignore */
        }
        setEmail('')
      } else {
        setStatus('err')
      }
    } catch {
      setStatus('err')
    }
  }

  function devExportSubscribersTxt() {
    try {
      const prev = JSON.parse(localStorage.getItem(LS_KEY) || '[]') as string[]
      const body = [...new Set(prev.map((e) => e.trim()).filter(Boolean))].join('\n')
      const blob = new Blob([body || '# (empty — submit the form once in dev)\n'], { type: 'text/plain;charset=utf-8' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = 'subscribers.txt'
      a.click()
      URL.revokeObjectURL(a.href)
    } catch {
      /* ignore */
    }
  }

  return (
    <div
      className={
        dark
          ? 'rounded-xl border border-white/10 bg-white/[0.04] p-3 text-white'
          : 'rounded-xl border border-[#E3E3E0] bg-white p-3 text-[#1A1A1A]'
      }
    >
      <div className={`text-[10px] font-semibold uppercase tracking-wide ${dark ? 'text-white/45' : 'text-[#6B6B6B]'}`}>
        Ops newsletter
      </div>
      <div className={`mt-1 text-xs ${dark ? 'text-white/70' : 'text-[#4B4B4B]'}`}>Formspree → merge into subscribers.txt for the bot.</div>

      <form onSubmit={onSubmit} className="mt-3 space-y-2">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@domain.com"
          disabled={!action}
          className={
            dark
              ? 'w-full rounded-lg border border-white/15 bg-black/30 px-2 py-2 text-sm text-white placeholder:text-white/35'
              : 'w-full rounded-lg border border-[#E3E3E0] bg-[#FDFDFC] px-2 py-2 text-sm placeholder:text-[#9A9A97]'
          }
        />
        <button
          type="submit"
          disabled={!action || status === 'loading'}
          className="w-full rounded-lg bg-[#FFD700] px-3 py-2 text-xs font-bold text-black disabled:opacity-40"
        >
          {status === 'loading' ? 'Sending…' : 'Subscribe'}
        </button>
      </form>

      {!formId ? (
        <p className={`mt-2 text-[10px] ${dark ? 'text-amber-200/90' : 'text-amber-800'}`}>Set VITE_FORMSPREE_ID in .env</p>
      ) : null}

      <AnimatePresence mode="wait">
        {status === 'ok' ? (
          <motion.div
            key="ok"
            initial={{ opacity: 0, scale: 0.85, y: 6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ type: 'spring', stiffness: 420, damping: 22 }}
            className="mt-2 text-center text-xs font-semibold text-emerald-400"
          >
            Verified — you’re on the list.
          </motion.div>
        ) : null}
        {status === 'err' ? (
          <motion.div
            key="err"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={`mt-2 text-center text-[11px] ${dark ? 'text-rose-300' : 'text-rose-700'}`}
          >
            Could not submit. Check Formspree id / network.
          </motion.div>
        ) : null}
      </AnimatePresence>

      {import.meta.env.DEV ? (
        <button
          type="button"
          title="Export locally queued emails (dev) for subscribers.txt"
          onClick={devExportSubscribersTxt}
          className={`mt-3 w-full text-left text-[9px] underline opacity-35 hover:opacity-100 ${dark ? 'text-white/80' : 'text-[#6B6B6B]'}`}
        >
          Dev: download local subscriber queue as subscribers.txt
        </button>
      ) : null}
    </div>
  )
}
