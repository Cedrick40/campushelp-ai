import { useCallback, useEffect, useRef, useState } from 'react'
import Banner from './components/Banner.jsx'
import ChatMessage from './components/ChatMessage.jsx'
import QuestionBox from './components/QuestionBox.jsx'
import { askQuestion, fetchCorpus, isMockMode } from './api.js'

/**
 * Three example questions. The last one is the one the documents do not
 * cover, so the honest fallback can be shown in one click.
 */
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

export default function App() {
  const [corpus, setCorpus] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  // Guards against an older request overwriting a newer answer.
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
    [updateMessage],
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
      if (!message?.question) return
      void runQuestion(message.question, message.id)
    },
    [runQuestion],
  )

  const handleNewChat = useCallback(() => {
    requestId.current += 1
    setMessages([])
    setIsLoading(false)
  }, [])

  const university = corpus?.university

  return (
    <div className="page">
      <Banner corpus={corpus} />

      <header className="chatHeader">
        <div className="chatHeader__inner">
          <div className="chatHeader__brand">
            <span className="brandMark" aria-hidden="true">
              CH
            </span>
            <div>
              <h1 className="masthead__title">CampusHelp AI</h1>
              <p className="chatHeader__subtitle">
                Ask about university rules, fees and dates.
              </p>
            </div>
          </div>

          {messages.length > 0 ? (
            <button
              className="chatHeader__new"
              type="button"
              onClick={handleNewChat}
            >
              New chat
            </button>
          ) : null}
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
            <div className="chat__welcome">
              <span className="welcome__mark" aria-hidden="true">
                CH
              </span>
              <h2 className="welcome__title">
                Ask about university rules, fees and dates.
              </h2>
              <p className="welcome__text">
                I answer only from approved{' '}
                {university ? `${university} ` : ''}documents, and every answer
                shows the source it came from. If the documents do not cover it,
                I will say so.
              </p>
              <p className="answer__placeholder">
                Your answer will appear here, together with the document it came
                from.
              </p>
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
            Mock data — the backend is not connected.
          </p>
        ) : null}
      </footer>
    </div>
  )
}
