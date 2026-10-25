import { useEffect, useRef, useState } from 'react'
import { MAX_QUESTION_LENGTH } from '../api.js'
import { SendIcon } from './icons.jsx'

/**
 * The chat composer: a growing textarea, a send button, client-side
 * validation, and (while the conversation is empty) clickable example
 * questions.
 *
 * Enter sends, Shift+Enter adds a new line. Examples submit immediately so
 * the honest fallback is one click away in the demo.
 */
export default function QuestionBox({ examples, showExamples, isLoading, onAsk }) {
  const [value, setValue] = useState('')
  const [validationError, setValidationError] = useState(null)
  const inputRef = useRef(null)

  const length = value.length
  const isOverLimit = length > MAX_QUESTION_LENGTH

  useEffect(() => {
    const input = inputRef.current
    if (!input) return
    input.style.height = 'auto'
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`
  }, [value])

  useEffect(() => {
    if (!isLoading) inputRef.current?.focus()
  }, [isLoading])

  function submit(question) {
    const trimmed = question.trim()

    if (!trimmed) {
      setValidationError('Please enter a question.')
      return
    }
    if (trimmed.length > MAX_QUESTION_LENGTH) {
      setValidationError(
        `Questions are limited to ${MAX_QUESTION_LENGTH} characters. Please shorten your question.`,
      )
      return
    }

    setValidationError(null)
    setValue('')
    onAsk(trimmed)
  }

  function handleSubmit(event) {
    event.preventDefault()
    if (isLoading) return
    submit(value)
  }

  function handleKeyDown(event) {
    if (event.key !== 'Enter' || event.shiftKey) return
    if (event.nativeEvent?.isComposing) return
    event.preventDefault()
    if (!isLoading) submit(value)
  }

  function handleExample(example) {
    if (isLoading) return
    setValue(example.question)
    submit(example.question)
  }

  return (
    <section className="composer" aria-labelledby="ask-heading">
      <h2 className="visually-hidden" id="ask-heading">
        Ask a question
      </h2>

      {showExamples ? (
        <div className="examples">
          <h3 className="examples__heading">Try asking</h3>
          <ul className="examples__list">
            {examples.map((example) => (
              <li key={example.question}>
                <button
                  className="examples__button"
                  type="button"
                  onClick={() => handleExample(example)}
                  disabled={isLoading}
                >
                  {example.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <form onSubmit={handleSubmit} noValidate>
        <div
          className={
            validationError
              ? 'ask__field ask__field--invalid'
              : 'ask__field'
          }
        >
          <label className="visually-hidden" htmlFor="question">
            Ask a question
          </label>
          <textarea
            ref={inputRef}
            id="question"
            className="ask__input"
            name="question"
            rows={1}
            value={value}
            placeholder="Ask about fees, registration, complaints…"
            onChange={(event) => {
              setValue(event.target.value)
              if (validationError) setValidationError(null)
            }}
            onKeyDown={handleKeyDown}
            aria-describedby="question-hint question-count"
            aria-invalid={validationError ? 'true' : 'false'}
            disabled={isLoading}
          />
          <button
            className="ask__submit"
            type="submit"
            disabled={isLoading}
            aria-label={isLoading ? 'Waiting for an answer' : 'Send question'}
          >
            {isLoading ? (
              <span className="spinner spinner--button" aria-hidden="true" />
            ) : (
              <SendIcon size={18} />
            )}
          </button>
        </div>

        <div className="ask__footer">
          {validationError ? (
            <p className="ask__error" role="alert" id="question-hint">
              {validationError}
            </p>
          ) : (
            <p className="ask__hint" id="question-hint">
              Answers come only from approved documents and always show their
              source.
            </p>
          )}

          <span
            className={
              isOverLimit ? 'ask__count ask__count--over' : 'ask__count'
            }
            id="question-count"
          >
            {length} / {MAX_QUESTION_LENGTH}
          </span>
        </div>
      </form>
    </section>
  )
}
