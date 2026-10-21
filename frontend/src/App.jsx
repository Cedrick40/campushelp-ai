import { useCallback, useEffect, useRef, useState } from 'react'
import AnswerArea from './components/AnswerArea.jsx'
import Banner from './components/Banner.jsx'
import QuestionBox from './components/QuestionBox.jsx'
import { askQuestion, fetchCorpus, isMockMode } from './api.js'

/**
 * Three example questions. The last one is the one the documents do not
 * cover, so the honest fallback can be shown in one click.
 */
const EXAMPLE_QUESTIONS = [
  {
    label: 'When does examination registration close?',
    question: 'When is the deadline to register for exams?',
  },
  {
    label: 'What are the library opening hours?',
    question: 'What are the library opening hours during term time?',
  },
  {
    label: 'Can I get a refund on accommodation fees?',
    question: 'Can I get a refund on accommodation fees?',
  },
]

export default function App() {
  const [corpus, setCorpus] = useState(null)
  const [state, setState] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [lastQuestion, setLastQuestion] = useState('')

  // Guards against an older request overwriting a newer answer.
  const requestId = useRef(0)

  useEffect(() => {
    let active = true
    fetchCorpus().then((data) => {
      if (active) setCorpus(data)
    })
    return () => {
      active = false
    }
  }, [])

  const handleAsk = useCallback(async (question) => {
    const id = requestId.current + 1
    requestId.current = id

    setLastQuestion(question)
    setState('loading')
    setResult(null)
    setError(null)

    try {
      const data = await askQuestion(question)
      if (requestId.current !== id) return
      setResult(data)
      setState('done')
    } catch (caught) {
      if (requestId.current !== id) return
      setError(
        caught?.message ?? 'Something went wrong. Please try again.',
      )
      setState('error')
    }
  }, [])

  const handleRetry = useCallback(() => {
    if (lastQuestion) handleAsk(lastQuestion)
  }, [handleAsk, lastQuestion])

  const isLoading = state === 'loading'
  const university = corpus?.university

  return (
    <div className="page">
      <Banner corpus={corpus} />

      <main className="main">
        <header className="masthead">
          <h1 className="masthead__title">CampusHelp AI</h1>
          <p className="masthead__subtitle">
            Ask a question about university rules and get an answer with its
            source.
          </p>
        </header>

        <QuestionBox
          examples={EXAMPLE_QUESTIONS}
          isLoading={isLoading}
          onAsk={handleAsk}
        />

        <AnswerArea
          state={state}
          result={result}
          error={error}
          onRetry={handleRetry}
        />
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
