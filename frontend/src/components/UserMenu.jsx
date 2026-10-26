import { useEffect, useRef, useState } from 'react'

export default function UserMenu({ user, accountName, onLogout }) {
  const [isOpen, setIsOpen] = useState(false)
  const rootRef = useRef(null)
  const triggerRef = useRef(null)
  const initial = (accountName || user?.email || '?')[0].toUpperCase()

  useEffect(() => {
    if (!isOpen) return

    const handlePointerDown = (event) => {
      if (!rootRef.current?.contains(event.target)) setIsOpen(false)
    }
    const handleKeyDown = (event) => {
      if (event.key !== 'Escape') return
      setIsOpen(false)
      triggerRef.current?.focus()
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  const handleLogout = () => {
    setIsOpen(false)
    onLogout()
  }

  return (
    <div className="userMenu" ref={rootRef}>
      <button
        ref={triggerRef}
        className="userMenu__trigger"
        type="button"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label={`Account menu for ${accountName}`}
        onClick={() => setIsOpen((open) => !open)}
      >
        <span className="userAvatar" aria-hidden="true">
          {initial}
        </span>
        <span className="userMenu__name">{accountName}</span>
      </button>

      {isOpen ? (
        <div className="userMenu__panel" role="menu" aria-label="Account">
          <div className="userMenu__identity">
            <span className="userAvatar" aria-hidden="true">
              {initial}
            </span>
            <div className="userMenu__details">
              <span className="userMenu__identityName">{accountName}</span>
              <span className="userMenu__identityEmail">{user?.email}</span>
            </div>
          </div>
          <button
            className="userMenu__logout"
            type="button"
            role="menuitem"
            onClick={handleLogout}
          >
            Log out
          </button>
        </div>
      ) : null}
    </div>
  )
}
