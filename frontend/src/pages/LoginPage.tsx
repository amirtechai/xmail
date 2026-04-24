import { type FormEvent, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mail, ShieldCheck } from 'lucide-react'
import { useAuth } from '../lib/auth'

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuth((s) => s.login)
  const completeTOTP = useAuth((s) => s.completeTOTP)
  const loading = useAuth((s) => s.loading)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  // TOTP challenge state
  const [totpToken, setTotpToken] = useState<string | null>(null)
  const [totpCode, setTotpCode] = useState('')
  const totpRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const result = await login(email, password)
      if (result.requires_totp && result.totp_token) {
        setTotpToken(result.totp_token)
        setTimeout(() => totpRef.current?.focus(), 50)
      } else {
        navigate('/dashboard', { replace: true })
      }
    } catch {
      setError('Invalid credentials. Please try again.')
    }
  }

  const handleTOTP = async (e: FormEvent) => {
    e.preventDefault()
    if (!totpToken) return
    setError('')
    try {
      await completeTOTP(totpToken, totpCode)
      navigate('/dashboard', { replace: true })
    } catch {
      setError('Invalid or expired code. Try again.')
      setTotpCode('')
      totpRef.current?.focus()
    }
  }

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Mail className="w-8 h-8 text-accent-yellow" />
          <span className="text-2xl font-bold text-text-primary">Xmail</span>
        </div>

        <div className="card">
          {!totpToken ? (
            <>
              <h1 className="text-lg font-semibold text-text-primary mb-1">Sign in</h1>
              <p className="text-sm text-text-secondary mb-6">PriceONN.com Outreach Console</p>

              <form onSubmit={(e) => { void handleSubmit(e) }} className="space-y-4">
                <div>
                  <label className="block text-xs text-text-secondary mb-1.5">Email</label>
                  <input
                    type="email"
                    className="input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@priceonn.com"
                    required
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1.5">Password</label>
                  <input
                    type="password"
                    className="input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                  />
                </div>

                {error && (
                  <p className="text-xs text-accent-red bg-red-900/20 border border-red-800/30 rounded px-3 py-2">
                    {error}
                  </p>
                )}

                <button type="submit" className="btn-primary w-full" disabled={loading}>
                  {loading ? 'Signing in…' : 'Sign in'}
                </button>
              </form>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-1">
                <ShieldCheck className="w-5 h-5 text-accent-yellow" />
                <h1 className="text-lg font-semibold text-text-primary">Two-Factor Auth</h1>
              </div>
              <p className="text-sm text-text-secondary mb-6">
                Enter the 6-digit code from your authenticator app.
              </p>

              <form onSubmit={(e) => { void handleTOTP(e) }} className="space-y-4">
                <input
                  ref={totpRef}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  className="input text-center text-2xl font-mono tracking-widest"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="000000"
                  required
                  autoComplete="one-time-code"
                />

                {error && (
                  <p className="text-xs text-accent-red bg-red-900/20 border border-red-800/30 rounded px-3 py-2">
                    {error}
                  </p>
                )}

                <button type="submit" className="btn-primary w-full" disabled={loading || totpCode.length !== 6}>
                  {loading ? 'Verifying…' : 'Verify'}
                </button>

                <button
                  type="button"
                  className="w-full text-xs text-text-muted hover:text-text-secondary"
                  onClick={() => { setTotpToken(null); setTotpCode(''); setError('') }}
                >
                  ← Back to login
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-xs text-text-muted mt-6">
          Xmail v1.0 · PriceONN Global Expansion
        </p>
      </div>
    </div>
  )
}
