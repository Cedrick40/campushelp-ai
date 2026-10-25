import SourceCard from './SourceCard.jsx'
import { AlertIcon, CheckIcon, InfoIcon, WarningIcon } from './icons.jsx'

/**
 * The content of one assistant reply. It renders exactly one of: the answer
 * with its sources, the honest fallback, the conflicting-sources display, or
 * a failure message with a retry.
 *
 * Each state carries a written label and an icon, so the difference between an
 * answer, a refusal and a failure never depends on colour alone.
 */
export default function AnswerArea({ state, result, error, onRetry }) {
  if (state === 'loading') {
    return (
      <div className="answer__loading" aria-busy="true">
        <div className="answer__header">
          <span className="answer__icon">
            <span className="spinner" />
          </span>
          <p className="answer__status">Searching</p>
        </div>
        <p className="answer__message">
          Looking through the approved documents for passages that answer your
          question.
        </p>
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div className="answer__failed" role="alert">
        <div className="answer__header">
          <span className="answer__icon">
            <AlertIcon size={15} />
          </span>
          <p className="answer__status">Request failed</p>
        </div>
        <p className="answer__message">{error}</p>
        <button className="answer__retry" type="button" onClick={onRetry}>
          Try again
        </button>
      </div>
    )
  }

  if (!result) {
    return (
      <p className="answer__placeholder">
        Your answer will appear here, together with the document it came from.
      </p>
    )
  }

  const sources = result.sources ?? []

  if (result.status === 'insufficient_evidence') {
    return (
      <div className="answer__unverified">
        <div className="answer__header">
          <span className="answer__icon">
            <InfoIcon size={15} />
          </span>
          <p className="answer__status">Not verified</p>
        </div>
        <p className="answer__message">
          I could not verify this from the available documents.
        </p>
        {result.message ? (
          <p className="answer__detail">{result.message}</p>
        ) : null}
        {result.contactLine ? (
          <p className="answer__contact">
            Contact the {result.contactLine.office}
            {result.contactLine.source
              ? ` (see ${result.contactLine.source})`
              : ''}
            .
          </p>
        ) : null}
      </div>
    )
  }

  if (result.status === 'conflicting_sources') {
    return (
      <div className="answer__conflict">
        <div className="answer__header">
          <span className="answer__icon">
            <WarningIcon size={15} />
          </span>
          <p className="answer__status">Sources disagree</p>
        </div>
        <p className="answer__message">These sources disagree.</p>
        {result.answer ? <p className="answer__text">{result.answer}</p> : null}
        {sources.length > 0 ? (
          <div className="sources sources--conflict">
            {sources.map((source, index) => (
              <SourceCard
                key={`${source.title}-${index}`}
                source={source}
                index={index}
              />
            ))}
          </div>
        ) : null}
      </div>
    )
  }

  if (result.status === 'error') {
    return (
      <div className="answer__failed" role="alert">
        <div className="answer__header">
          <span className="answer__icon">
            <AlertIcon size={15} />
          </span>
          <p className="answer__status">Request failed</p>
        </div>
        <p className="answer__message">
          {result.message ??
            'The service is temporarily unavailable. Please try again.'}
        </p>
        <button className="answer__retry" type="button" onClick={onRetry}>
          Try again
        </button>
      </div>
    )
  }

  return (
    <div className="answer__answered">
      <div className="answer__header">
        <span className="answer__icon">
          <CheckIcon size={15} />
        </span>
        <p className="answer__status">Answer</p>
      </div>
      {result.answer ? (
        <p className="answer__text">{result.answer}</p>
      ) : (
        <p className="answer__message">
          I could not verify this from the available documents.
        </p>
      )}
      {sources.length > 0 ? (
        <>
          <h3 className="answer__sourcesHeading">
            Sources
            <span className="answer__sourcesCount">
              {sources.length} {sources.length === 1 ? 'document' : 'documents'}
            </span>
          </h3>
          <div className="sources">
            {sources.map((source, index) => (
              <SourceCard
                key={`${source.title}-${index}`}
                source={source}
                index={index}
              />
            ))}
          </div>
        </>
      ) : null}
    </div>
  )
}
