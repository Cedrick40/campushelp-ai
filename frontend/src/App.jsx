import { useCallback, useEffect, useRef, useState } from 'react'
import ChatMessage from './components/ChatMessage.jsx'
import QuestionBox from './components/QuestionBox.jsx'
import Sidebar from './components/Sidebar.jsx'
import AuthModal from './components/AuthModal.jsx'
import UserMenu from './components/UserMenu.jsx'
import { MenuIcon, MoonIcon, SunIcon } from './components/icons.jsx'
import { welcomeMessage } from './greeting.js'
import {
  askQuestion,
  clearHistory as clearSavedHistory,
  deleteConversation,
  fetchConversation,
  fetchConversations,
  fetchCorpus,
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

const HISTORY_ERROR = 'Your saved chats could not be loaded. Please try again.'
const HISTORY_OPEN_ERROR = 'That saved chat could not be opened. Please try again.'
const THEME_KEY = 'campushelp.theme'

function initialTheme() {
  const saved = document.documentElement.dataset.theme
  if (saved === 'light' || saved === 'dark') return saved

  try {
    const stored = window.localStorage.getItem(THEME_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // Storage can be blocked; fall back to the system preference.
  }

  return window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export default function App() {
  const [corpus, setCorpus] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const [user, setUser] = useState(null)
  const [authModal, setAuthModal] = useState(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState([])
  const [historyError, setHistoryError] = useState(null)
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [isRestoring, setIsRestoring] = useState(true)
  const [theme, setTheme] = useState(initialTheme)
  const [greeting, setGreeting] = useState('')

  const requestId = useRef(0)
  const nextId = useRef(0)
  const scrollRef = useRef(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', theme === 'dark' ? '#0b1120' : '#ffffff')

    try {
      window.localStorage.setItem(THEME_KEY, theme)
    } catch {
      // The chosen theme still applies to this page when storage is blocked.
    }
  }, [theme])

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
        setGreeting(welcomeMessage('login', restored))
        try {
          const chats = await fetchConversations()
          if (active) setChatHistory(chats)
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
            const saved = await saveHistoryEntry({
              question,
              result: data,
              conversationId: activeConversationId,
            })
            if (requestId.current === id) {
              setActiveConversationId(saved.conversation.id)
              setChatHistory((previous) => [
                saved.conversation,
                ...previous.filter((item) => item.id !== saved.conversation.id),
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
    [activeConversationId, updateMessage, user],
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
    setActiveConversationId(null)
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
    setGreeting(welcomeMessage(mode, authenticated))
    setActiveConversationId(null)
    setAuthModal(null)
    setHistoryError(null)

    try {
      setChatHistory(await fetchConversations())
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
    setGreeting('')
    setActiveConversationId(null)
    setAuthModal(null)
    setIsSidebarOpen(false)
    setChatHistory([])
    setHistoryError(null)
    setMessages([])
  }, [])

  const handleSelectHistory = useCallback(async (chat) => {
    if (!chat?.id) return

    requestId.current += 1
    setIsLoading(false)
    try {
      const conversation = await fetchConversation(chat.id)
      const nextMessages = []
      for (const entry of conversation.entries) {
        if (!entry.result) continue
        nextMessages.push({
          id: `h${entry.id}-u`,
          role: 'user',
          text: entry.question,
        })
        nextMessages.push({
          id: `h${entry.id}-a`,
          role: 'assistant',
          question: entry.question,
          state: 'done',
          result: entry.result,
          error: null,
        })
      }
      setActiveConversationId(chat.id)
      setMessages(nextMessages)
      setHistoryError(null)
      setIsSidebarOpen(false)
    } catch {
      setHistoryError(HISTORY_OPEN_ERROR)
    }
  }, [])

  const handleDeleteHistory = useCallback(async (chat) => {
    if (!chat?.id) return
    const deletingActive = activeConversationId === chat.id
    try {
      await deleteConversation(chat.id)
      setChatHistory((previous) => previous.filter((item) => item.id !== chat.id))
      setHistoryError(null)
      if (deletingActive) {
        requestId.current += 1
        setActiveConversationId(null)
        setMessages([])
        setIsLoading(false)
      }
    } catch {
      setHistoryError('That saved chat could not be deleted. Please try again.')
    }
  }, [activeConversationId])

  const handleClearHistory = useCallback(async () => {
    if (chatHistory.length === 0) return
    if (!window.confirm('Delete all saved chats? This cannot be undone.')) return

    try {
      await clearSavedHistory()
      setChatHistory([])
      setHistoryError(null)
      if (activeConversationId) {
        requestId.current += 1
        setActiveConversationId(null)
        setMessages([])
        setIsLoading(false)
      }
    } catch {
      setHistoryError('Your saved chats could not be cleared. Please try again.')
    }
  }, [activeConversationId, chatHistory.length])

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
        <header className="chatHeader">
          <div className="chatHeader__inner">
            <div className="chatHeader__brand">
              {user ? (
                <button
                  className={`iconButton chatHeader__menu ${
                    isSidebarOpen ? 'chatHeader__menu--hidden' : ''
                  }`}
                  type="button"
                  onClick={() => setIsSidebarOpen((open) => !open)}
                  aria-label="Toggle chat history sidebar"
                  aria-expanded={isSidebarOpen}
                  aria-controls="chat-history-sidebar"
                  aria-hidden={isSidebarOpen}
                  tabIndex={isSidebarOpen ? -1 : 0}
                >
                  <MenuIcon size={20} />
                </button>
              ) : null}

              <div className="brandLogoWrap">
                <img
                  className="brandLogoIcon"
                  src="/cesd-logo.png"
                  alt=""
                  width="40"
                  height="40"
                />
                <h1 className="masthead__title">CampusHelp AI</h1>
              </div>
            </div>

            <div className="chatHeader__actions">
              <button
                className="iconButton themeToggle"
                type="button"
                onClick={() =>
                  setTheme((current) => (current === 'dark' ? 'light' : 'dark'))
                }
                aria-label={`Switch to ${
                  theme === 'dark' ? 'light' : 'dark'
                } mode`}
                title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              >
                {theme === 'dark' ? (
                  <SunIcon size={18} />
                ) : (
                  <MoonIcon size={18} />
                )}
              </button>

              {!isRestoring && user ? (
                <UserMenu
                  user={user}
                  accountName={accountName}
                  onLogout={handleLogout}
                />
              ) : null}

              {!isRestoring && !user ? (
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
              ) : null}
            </div>
          </div>
        </header>

        {messages.length === 0 ? (
          <section
            className={`heroBanner${user ? ' heroBanner--account' : ''}`}
            aria-labelledby={user ? undefined : 'heroTitle'}
            aria-label={user ? 'Account home' : undefined}
          >
            <div className="heroBanner__content">
              {greeting ? <p className="heroGreeting">{greeting}</p> : null}
              {!user ? (
                <>
                  <span className="heroBadge">Official Reference Assistant</span>
                  <h2 id="heroTitle" className="heroTitle">
                    Your Grounded Guide to University Information
                  </h2>
                </>
              ) : null}
              <p className="heroSubtitle">
                Ask about rules, fees, and dates, and get direct answers built
                strictly from approved {university ?? 'campus'} documents.
              </p>
            </div>
          </section>
        ) : null}

        <main className={`chat${messages.length === 0 ? ' chat--welcome' : ''}`}>
          <div
            className="chat__scroll"
            ref={scrollRef}
            role="log"
            aria-live="polite"
            aria-label="Conversation"
          >
            {messages.length === 0 ? (
              <div className="welcomeSection">
                <div className="welcomeExamples">
                  <h3 className="examples__heading">Try asking</h3>
                  <ul className="examples__list">
                    {EXAMPLE_QUESTIONS.map((example) => (
                      <li key={example.question}>
                        <button
                          className="examples__button"
                          type="button"
                          onClick={() => handleAsk(example.question)}
                          disabled={isLoading}
                        >
                          {example.label}
                        </button>
                      </li>
                    ))}
                  </ul>
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
            <QuestionBox isLoading={isLoading} onAsk={handleAsk} />
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
