import { useEffect, useRef, useState } from 'react'
import { CloseIcon } from './icons.jsx'

export default function AuthModal({ mode, onClose, onAuthenticate, onSwitchMode }) {
  const isLogin = mode === 'login'
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const cardRef = useRef(null)
  const firstFieldRef = useRef(null)

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    firstFieldRef.current?.focus()
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [])

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        if (!isSubmitting) onClose()
        return
      }
      if (event.key !== 'Tab') return

      const focusable = cardRef.current?.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      )
      if (!focusable || focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isSubmitting, onClose])

  async function handleSubmit(event) {
    event.preventDefault()

    const trimmedEmail = email.trim()
    const trimmedName = name.trim()

    if (!trimmedEmail || !password || (!isLogin && !trimmedName)) {
      setError('Please fill in all fields.')
      return
    }

    setError('')
    setIsSubmitting(true)

    try {
      await onAuthenticate(isLogin ? 'login' : 'register', {
        email: trimmedEmail,
        password,
        ...(isLogin ? {} : { name: trimmedName }),
      })
    } catch (caught) {
      setError(caught?.message ?? 'Something went wrong. Please try again.')
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="modalOverlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isSubmitting) onClose()
      }}
    >
      <div
        ref={cardRef}
        className="authCard"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-title"
        aria-describedby="auth-subtitle"
      >
        <div className="authCard__header">
          <h2 id="auth-title" className="authCard__title">
            {isLogin ? 'Log in to CampusHelp' : 'Create an Account'}
          </h2>
          <button
            className="iconButton"
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            disabled={isSubmitting}
          >
            <CloseIcon size={18} />
          </button>
        </div>

        <p className="authCard__subtitle" id="auth-subtitle">
          {isLogin
            ? 'Access your saved queries and search history across sessions.'
            : 'Register to start saving your chat history and verified sources.'}
        </p>

        {error ? (
          <p className="authCard__error" role="alert">
            {error}
          </p>
        ) : null}

        <form onSubmit={handleSubmit} className="authForm" noValidate>
          {!isLogin ? (
            <div className="formGroup">
              <label htmlFor="auth-name">Name</label>
              <input
                ref={firstFieldRef}
                id="auth-name"
                type="text"
                autoComplete="name"
                placeholder="Your name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                maxLength={150}
              />
            </div>
          ) : null}

          <div className="formGroup">
            <label htmlFor="auth-email">Email Address</label>
            <input
              ref={isLogin ? firstFieldRef : undefined}
              id="auth-email"
              type="email"
              autoComplete="email"
              placeholder="student@university.edu"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div className="formGroup">
            <label htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              aria-describedby={!isLogin ? 'auth-password-hint' : undefined}
              required
            />
            {!isLogin ? (
              <p className="formHint" id="auth-password-hint">
                Use at least 8 characters and avoid common passwords.
              </p>
            ) : null}
          </div>

          <button
            type="submit"
            className="authButton authButton--primary authButton--full"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? 'Please wait…'
              : isLogin
                ? 'Log In'
                : 'Register'}
          </button>
        </form>

        <div className="authCard__footer">
          {isLogin ? (
            <p>
              Don&apos;t have an account?{' '}
              <button
                className="textLink"
                type="button"
                onClick={() => onSwitchMode('register')}
                disabled={isSubmitting}
              >
                Register
              </button>
            </p>
          ) : (
            <p>
              Already have an account?{' '}
              <button
                className="textLink"
                type="button"
                onClick={() => onSwitchMode('login')}
                disabled={isSubmitting}
              >
                Log in
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
