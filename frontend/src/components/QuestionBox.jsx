import { useState } from 'react'
import { MAX_QUESTION_LENGTH } from '../api.js'

/**
 * The question box: input, submit button, three clickable examples, the
 * client-side validation rules and the loading state.
 *
 * Examples fill the box and submit immediately, so the honest fallback is
 * one click away in the demo.
 */
export default function QuestionBox({ examples, isLoading, onAsk }) {
  const [value, setValue] = useState('')
  const [validationError, setValidationError] = useState(null)

  const length = value.length
  const isOverLimit = length > MAX_QUESTION_LENGTH

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
    onAsk(trimmed)
  }

  function handleSubmit(event) {
    event.preventDefault()
    if (isLoading) return
    submit(value)
  }

  function handleExample(example) {
    if (isLoading) return
    setValue(example.question)
    submit(example.question)
  }

  return (
    <section className="ask" aria-labelledby="ask-heading">
      <h2 className="visually-hidden" id="ask-heading">
        Ask a question
      </h2>

      <form onSubmit={handleSubmit} noValidate>
        <div className="ask__header">
          <label className="ask__label" htmlFor="question">
            Ask a question
          </label>
          <span
            className={isOverLimit ? 'ask__count ask__count--over' : 'ask__count'}
            id="question-count"
          >
            {length} / {MAX_QUESTION_LENGTH}
          </span>
        </div>

        <div className={validationError ? 'ask__field ask__field--invalid' : 'ask__field'}>
          <textarea
            id="question"
            className="ask__input"
            name="question"
            rows={3}
            value={value}
            placeholder="Example: When is the deadline to register for exams?"
            onChange={(event) => {
              setValue(event.target.value)
              if (validationError) setValidationError(null)
            }}
            aria-describedby="question-hint question-count"
            aria-invalid={validationError ? 'true' : 'false'}
            disabled={isLoading}
          />
        </div>

        <div className="ask__footer">
          {validationError ? (
            <p className="ask__error" role="alert" id="question-hint">
              {validationError}
            </p>
          ) : (
            <p className="ask__hint" id="question-hint">
              Answers come only from approved documents, and always show the
              source they came from.
            </p>
          )}

          <button className="ask__submit" type="submit" disabled={isLoading}>
            {isLoading ? 'Asking…' : 'Ask'}
          </button>
        </div>
      </form>

      <div className="examples">
        <h3 className="examples__heading">Example questions</h3>
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
    </section>
  )
}
