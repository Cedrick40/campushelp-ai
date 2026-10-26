import { useCallback, useEffect, useRef, useState } from 'react'
import Banner from './components/Banner.jsx'
import ChatMessage from './components/ChatMessage.jsx'
import QuestionBox from './components/QuestionBox.jsx'
import Sidebar from './components/Sidebar.jsx'
import AuthModal from './components/AuthModal.jsx'
import { LogoIcon, MenuIcon } from './components/icons.jsx'
import {
  askQuestion,
  clearHistory as clearSavedHistory,
  deleteHistoryEntry,
  fetchCorpus,
  fetchHistory,
  isMockMode,
  loginAccount,
  logoutAccount,
  registerAccount,
  restoreSession,
  saveHistoryEntry,
} from './api.js'

const EXAMPLE_QUESTIONS = [
  {
    label: 'Exam registration deadline',
    question: 'When is the deadline to register for exams?',
  },
  {
    label: 'How do I make a complaint?',
    question: 'How do I make a complaint?',
  },
  {
    label: 'Accommodation fee refund',
    question: 'Can I get a refund on accommodation fees?',
  },
]

const HISTORY_ERROR = 'Your saved history could not be loaded. Please try again.'

export default function App() {
  const [corpus, setCorpus] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const [user, setUser] = useState(null)
  const [authModal, setAuthModal] = useState(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState([])
  const [historyError, setHistoryError] = useState(null)
  const [isRestoring, setIsRestoring] = useState(true)

  const requestId = useRef(0)
  const nextId = useRef(0)
  const scrollRef = useRef(null)

  useEffect(() => {
    let active = true
    fetchCorpus().then((data) => {
      if (active) setCorpus(data)
    })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    let active = true

    async function restore() {
      try {
        const restored = await restoreSession()
        if (!active || !restored) return
        setUser(restored)
        try {
          const entries = await fetchHistory()
          if (active) setChatHistory(entries)
        } catch {
          if (active) setHistoryError(HISTORY_ERROR)
        }
      } catch {
        // The backend is unreachable; stay a guest rather than blocking the page.
      } finally {
        if (active) setIsRestoring(false)
      }
    }

    void restore()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const node = scrollRef.current
    if (!node) return
    const frame = requestAnimationFrame(() => {
      node.scrollTo({ top: node.scrollHeight, behavior: 'smooth' })
    })
    return () => cancelAnimationFrame(frame)
  }, [messages])

  const updateMessage = useCallback((id, patch) => {
    setMessages((previous) =>
      previous.map((message) =>
        message.id === id ? { ...message, ...patch } : message,
      ),
    )
  }, [])

  const runQuestion = useCallback(
    async (question, assistantId) => {
      const id = requestId.current + 1
      requestId.current = id

      setIsLoading(true)
      updateMessage(assistantId, {
        state: 'loading',
        result: null,
        error: null,
      })

      try {
        const data = await askQuestion(question)
        if (requestId.current !== id) return
        updateMessage(assistantId, {
          state: 'done',
          result: data,
          error: null,
        })

        if (user) {
          try {
            const entry = await saveHistoryEntry({ question, result: data })
            if (requestId.current === id) {
              setChatHistory((previous) => [
                entry,
                ...previous.filter((item) => item.id !== entry.id),
              ])
            }
          } catch {
            // The answer is still valid; only the saved copy failed.
          }
        }
      } catch (caught) {
        if (requestId.current !== id) return
        updateMessage(assistantId, {
          state: 'error',
          result: null,
          error: caught?.message ?? 'Something went wrong. Please try again.',
        })
      } finally {
        if (requestId.current === id) setIsLoading(false)
      }
    },
    [updateMessage, user],
  )

  const handleAsk = useCallback(
    (question) => {
      if (!question || isLoading) return

      const userId = `u${nextId.current + 1}`
      const assistantId = `a${nextId.current + 2}`
      nextId.current += 2

      setMessages((previous) => [
        ...previous,
        { id: userId, role: 'user', text: question },
        {
          id: assistantId,
          role: 'assistant',
          question,
          state: 'loading',
          result: null,
          error: null,
        },
      ])

      void runQuestion(question, assistantId)
    },
    [isLoading, runQuestion],
  )

  const handleRetry = useCallback(
    (message) => {
      if (!message?.question || isLoading) return
      void runQuestion(message.question, message.id)
    },
    [isLoading, runQuestion],
  )

  const handleNewChat = useCallback(() => {
    requestId.current += 1
    setMessages([])
    setIsLoading(false)
    setIsSidebarOpen(false)
  }, [])

  const handleAuthenticate = useCallback(async (mode, credentials) => {
    const authenticated =
      mode === 'register'
        ? await registerAccount(credentials)
        : await loginAccount(credentials)

    setUser(authenticated)
    setAuthModal(null)
    setHistoryError(null)

    try {
      setChatHistory(await fetchHistory())
    } catch {
      setHistoryError(HISTORY_ERROR)
    }

    return authenticated
  }, [])

  const handleLogout = useCallback(async () => {
    requestId.current += 1
    setIsLoading(false)
    await logoutAccount()
    setUser(null)
    setAuthModal(null)
    setIsSidebarOpen(false)
    setChatHistory([])
    setHistoryError(null)
    setMessages([])
  }, [])

  const handleSelectHistory = useCallback((entry) => {
    if (!entry?.result) return

    requestId.current += 1
    const userId = `u${nextId.current + 1}`
    const assistantId = `a${nextId.current + 2}`
    nextId.current += 2

    setMessages([
      { id: userId, role: 'user', text: entry.question },
      {
        id: assistantId,
        role: 'assistant',
        question: entry.question,
        state: 'done',
        result: entry.result,
        error: null,
      },
    ])
    setIsLoading(false)
    setIsSidebarOpen(false)
  }, [])

  const handleDeleteHistory = useCallback(async (entry) => {
    if (!entry?.id) return
    try {
      await deleteHistoryEntry(entry.id)
      setChatHistory((previous) => previous.filter((item) => item.id !== entry.id))
      setHistoryError(null)
    } catch {
      setHistoryError('That saved answer could not be deleted. Please try again.')
    }
  }, [])

  const handleClearHistory = useCallback(async () => {
    if (chatHistory.length === 0) return
    if (!window.confirm('Delete all saved history? This cannot be undone.')) return

    try {
      await clearSavedHistory()
      setChatHistory([])
      setHistoryError(null)
    } catch {
      setHistoryError('Your history could not be cleared. Please try again.')
    }
  }, [chatHistory.length])

  const university = corpus?.university
  const accountName = user?.name || user?.email?.split('@')[0] || 'Account'

  return (
    <div className={`page ${isSidebarOpen && user ? 'page--sidebar-open' : ''}`}>
      {user ? (
        <Sidebar
          id="chat-history-sidebar"
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          history={chatHistory}
          onSelect={handleSelectHistory}
          onDelete={handleDeleteHistory}
          onClear={handleClearHistory}
          onNewChat={handleNewChat}
          user={user}
          accountName={accountName}
          onLogout={handleLogout}
          error={historyError}
        />
      ) : null}

      <div className="page__main">
        <Banner corpus={corpus} />

        <header className="chatHeader">
          <div className="chatHeader__inner">
            <div className="chatHeader__brand">
              {user ? (
                <button
                  className="iconButton"
                  type="button"
                  onClick={() => setIsSidebarOpen((open) => !open)}
                  aria-label="Toggle chat history sidebar"
                  aria-expanded={isSidebarOpen}
                  aria-controls="chat-history-sidebar"
                >
                  <MenuIcon size={20} />
                </button>
              ) : null}

              <div className="brandLogoWrap">
                <LogoIcon size={28} className="brandLogoIcon" />
                <div>
                  <h1 className="masthead__title">CampusHelp AI</h1>
                  <p className="chatHeader__subtitle">
                    Grounded answers from official campus documents
                  </p>
                </div>
              </div>
            </div>

            <div className="chatHeader__actions">
              {messages.length > 0 ? (
                <button
                  className="chatHeader__new"
                  type="button"
                  onClick={handleNewChat}
                >
                  New chat
                </button>
              ) : null}

              {!isRestoring ? (
                user ? (
                  <div className="userBadge">
                    <span className="userAvatar" aria-hidden="true">
                      {accountName[0].toUpperCase()}
                    </span>
                    <button
                      className="authButton authButton--text"
                      type="button"
                      onClick={handleLogout}
                    >
                      Log out
                    </button>
                  </div>
                ) : (
                  <div className="authButtons">
                    <button
                      className="authButton authButton--secondary"
                      type="button"
                      onClick={() => setAuthModal('login')}
                    >
                      Log in
                    </button>
                    <button
                      className="authButton authButton--primary"
                      type="button"
                      onClick={() => setAuthModal('register')}
                    >
                      Register
                    </button>
                  </div>
                )
              ) : null}
            </div>
          </div>
        </header>

        <main className="chat">
          <div
            className="chat__scroll"
            ref={scrollRef}
            role="log"
            aria-live="polite"
            aria-label="Conversation"
          >
            {messages.length === 0 ? (
              <div className="welcomeSection">
                <div className="heroCard">
                  <div className="heroCard__content">
                    <span className="heroBadge">Official Reference Assistant</span>
                    <h2 className="heroTitle">
                      Your Grounded Guide to University Information
                    </h2>
                    <p className="heroSubtitle">
                      Ask about rules, fees, and dates, and get direct answers
                      built strictly from approved {university ?? 'campus'}{' '}
                      documents.
                    </p>
                  </div>
                </div>

                <div className="aboutCard">
                  <h3 className="aboutCard__heading">What this AI does</h3>
                  <div className="aboutGrid">
                    <div className="aboutItem">
                      <div className="aboutItem__title">Verified Sources</div>
                      <div className="aboutItem__desc">
                        Every answer quotes and links directly to its source
                        document and exact page.
                      </div>
                    </div>
                    <div className="aboutItem">
                      <div className="aboutItem__title">Honest Fallback</div>
                      <div className="aboutItem__desc">
                        Clearly states when information cannot be found or
                        verified instead of guessing.
                      </div>
                    </div>
                    <div className="aboutItem">
                      <div className="aboutItem__title">Privacy First</div>
                      <div className="aboutItem__desc">
                        Guest queries are session-only and never saved. Log in to
                        save your history.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  onRetry={handleRetry}
                />
              ))
            )}
          </div>

          <div className="chat__composerWrap">
            <QuestionBox
              examples={EXAMPLE_QUESTIONS}
              showExamples={messages.length === 0}
              isLoading={isLoading}
              onAsk={handleAsk}
            />
          </div>
        </main>

        <footer className="footer">
          <p className="footer__text">
            Unofficial student project, not affiliated with{' '}
            {university ?? 'any university'}.
          </p>
          {isMockMode ? (
            <p className="footer__mock" role="status">
              Mock data — backend not connected
            </p>
          ) : null}
        </footer>
      </div>

      {authModal ? (
        <AuthModal
          mode={authModal}
          onClose={() => setAuthModal(null)}
          onAuthenticate={handleAuthenticate}
          onSwitchMode={(newMode) => setAuthModal(newMode)}
        />
      ) : null}
    </div>
  )
}
