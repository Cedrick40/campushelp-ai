import { useEffect, useRef, useState } from 'react'
import { MAX_QUESTION_LENGTH } from '../api.js'
import { MicIcon, SendIcon } from './icons.jsx'

/**
 * The chat composer: a growing textarea, a send button and client-side
 * validation.
 *
 * Enter sends, Shift+Enter adds a new line.
 */
export default function QuestionBox({ isLoading, onAsk }) {
  const [value, setValue] = useState('')
  const [validationError, setValidationError] = useState(null)
  const [isListening, setIsListening] = useState(false)
  const [voiceError, setVoiceError] = useState(null)
  const inputRef = useRef(null)
  const recognitionRef = useRef(null)
  const voiceBaseRef = useRef('')

  const length = value.length
  const isOverLimit = length > MAX_QUESTION_LENGTH
  const voiceSupported =
    typeof window !== 'undefined' &&
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)

  useEffect(() => {
    const input = inputRef.current
    if (!input) return
    input.style.height = 'auto'
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`
  }, [value])

  useEffect(() => {
    if (!isLoading) inputRef.current?.focus()
  }, [isLoading])

  useEffect(
    () => () => {
      recognitionRef.current?.abort()
    },
    [],
  )

  function startListening() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition

    if (!SpeechRecognition) return

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = navigator.language || 'en-US'
    voiceBaseRef.current = value.trim() ? `${value.trim()} ` : ''

    recognition.onresult = (event) => {
      if (recognitionRef.current !== recognition) return

      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript ?? '')
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim()

      setValue(`${voiceBaseRef.current}${transcript}`)
      setValidationError(null)
      setVoiceError(null)
    }

    recognition.onerror = (event) => {
      if (event.error === 'aborted') return
      if (recognitionRef.current !== recognition) return

      const messages = {
        'not-allowed':
          'Microphone access was blocked. Allow microphone access in your browser and try again.',
        'service-not-allowed':
          'Microphone access was blocked. Allow microphone access in your browser and try again.',
        'no-speech': 'No speech was detected. Click the microphone and try again.',
        'audio-capture':
          'No microphone was found. Check your microphone and try again.',
        network:
          'Voice typing needs a network connection. Check your connection and try again.',
      }

      setVoiceError(
        messages[event.error] ??
          'Voice typing could not start. Please try again.',
      )
      setIsListening(false)
    }

    recognition.onend = () => {
      if (recognitionRef.current !== recognition) return

      setIsListening(false)
      recognitionRef.current = null
    }

    recognitionRef.current = recognition
    setVoiceError(null)
    setValidationError(null)

    try {
      recognition.start()
      setIsListening(true)
    } catch {
      recognitionRef.current = null
      setIsListening(false)
      setVoiceError('Voice typing could not start. Please try again.')
    }
  }

  function stopListening({ discard = false } = {}) {
    const recognition = recognitionRef.current
    if (!recognition) return
    if (discard) recognition.onresult = null
    recognition.stop()
    setIsListening(false)
  }

  function toggleListening() {
    if (isLoading) return
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }

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

    stopListening({ discard: true })
    setIsListening(false)
    setValidationError(null)
    setVoiceError(null)
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

  const feedback = validationError || voiceError

  return (
    <section className="composer" aria-labelledby="ask-heading">
      <h2 className="visually-hidden" id="ask-heading">
        Ask a question
      </h2>

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
            placeholder="Ask a question…"
            onChange={(event) => {
              setValue(event.target.value)
              if (validationError) setValidationError(null)
              if (voiceError) setVoiceError(null)
            }}
            onKeyDown={handleKeyDown}
            aria-describedby="question-hint question-count"
            aria-invalid={validationError ? 'true' : 'false'}
            disabled={isLoading}
          />
          <button
            className={
              isListening
                ? 'ask__voice ask__voice--listening'
                : 'ask__voice'
            }
            type="button"
            onClick={toggleListening}
            disabled={isLoading || !voiceSupported}
            aria-label={
              !voiceSupported
                ? 'Voice typing is not supported in this browser'
                : isListening
                  ? 'Stop voice typing'
                  : 'Start voice typing'
            }
            aria-pressed={isListening}
            title={
              !voiceSupported
                ? 'Voice typing is not supported in this browser'
                : isListening
                  ? 'Stop voice typing'
                  : 'Start voice typing'
            }
          >
            <MicIcon size={18} />
          </button>
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
          {feedback ? (
            <p className="ask__error" role="alert" id="question-hint">
              {feedback}
            </p>
          ) : (
            <p className="ask__hint" id="question-hint" aria-live="polite">
              {isListening
                ? 'Listening… speak your question, then click the microphone to stop.'
                : 'Answers come only from approved documents and always show their source.'}
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
