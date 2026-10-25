import AnswerArea from './AnswerArea.jsx'

function bubbleModifier(state, result) {
  if (state === 'loading') return 'loading'
  if (state === 'error') return 'failed'

  switch (result?.status) {
    case 'insufficient_evidence':
      return 'unverified'
    case 'conflicting_sources':
      return 'conflict'
    case 'error':
      return 'failed'
    default:
      return 'answered'
  }
}

/**
 * One message in the conversation: the student's question as a right-aligned
 * bubble, or the assistant's reply with its status, answer and sources.
 */
export default function ChatMessage({ message, onRetry }) {
  if (message.role === 'user') {
    return (
      <div className="message message--user">
        <p className="visually-hidden">You asked:</p>
        <div className="bubble bubble--user">{message.text}</div>
      </div>
    )
  }

  const modifier = bubbleModifier(message.state, message.result)

  return (
    <div className="message message--assistant">
      <span className="message__avatar" aria-hidden="true">
        CH
      </span>
      <div className="message__content">
        <p className="message__author">CampusHelp AI</p>
        <div
          className={`bubble bubble--assistant answer answer--${modifier}`}
          aria-live="polite"
        >
          <AnswerArea
            state={message.state}
            result={message.result}
            error={message.error}
            onRetry={() => onRetry(message)}
          />
        </div>
      </div>
    </div>
  )
}
