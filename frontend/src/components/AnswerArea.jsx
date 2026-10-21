import SourceCard from './SourceCard.jsx'

/**
 * The answer area renders exactly one of: the answer with its sources, the
 * honest fallback, the conflicting-sources display, or a failure message with
 * a retry.
 *
 * Each state carries a written label, so the difference between an answer, a
 * refusal and a failure never depends on colour alone.
 */
export default function AnswerArea({ state, result, error, onRetry }) {
  if (state === 'idle') {
    return (
      <section className="answer answer--idle" aria-live="polite">
        <p className="answer__placeholder">
          Your answer will appear here, together with the document it came from.
        </p>
      </section>
    )
  }

  if (state === 'loading') {
    return (
      <section className="answer answer--loading" aria-live="polite" aria-busy="true">
        <p className="answer__status">Searching the approved documents…</p>
      </section>
    )
  }

  if (state === 'error') {
    return (
      <section className="answer answer--failed" role="alert">
        <p className="answer__status">Request failed</p>
        <p className="answer__message">{error}</p>
        <button className="answer__retry" type="button" onClick={onRetry}>
          Try again
        </button>
      </section>
    )
  }

  if (!result) {
    return (
      <section className="answer answer--idle" aria-live="polite">
        <p className="answer__placeholder">
          Your answer will appear here, together with the document it came from.
        </p>
      </section>
    )
  }

  if (result.status === 'insufficient_evidence') {
    return (
      <section className="answer answer--unverified" aria-live="polite">
        <p className="answer__status">Not verified</p>
        <p className="answer__message">
          I could not verify this from the available documents.
        </p>
        {result.message ? (
          <p className="answer__detail">{result.message}</p>
        ) : null}
        {result.contactLine ? (
          <p className="answer__contact">
            Contact the {result.contactLine.office}
            {result.contactLine.source ? ` (see ${result.contactLine.source})` : ''}.
          </p>
        ) : null}
      </section>
    )
  }

  if (result.status === 'conflicting_sources') {
    return (
      <section className="answer answer--conflict" aria-live="polite">
        <p className="answer__status">Sources disagree</p>
        <p className="answer__message">These sources disagree.</p>
        {result.answer ? <p className="answer__text">{result.answer}</p> : null}
        {result.sources.length > 0 ? (
          <div className="sources sources--conflict">
            {result.sources.map((source, index) => (
              <SourceCard key={`${source.title}-${index}`} source={source} />
            ))}
          </div>
        ) : null}
      </section>
    )
  }

  if (result.status === 'error') {
    return (
      <section className="answer answer--failed" role="alert">
        <p className="answer__status">Request failed</p>
        <p className="answer__message">
          {result.message ?? 'The service is temporarily unavailable. Please try again.'}
        </p>
        <button className="answer__retry" type="button" onClick={onRetry}>
          Try again
        </button>
      </section>
    )
  }

  return (
    <section className="answer answer--answered" aria-live="polite">
      <p className="answer__status">Answer</p>
      {result.answer ? (
        <p className="answer__text">{result.answer}</p>
      ) : (
        <p className="answer__message">
          I could not verify this from the available documents.
        </p>
      )}
      {result.sources.length > 0 ? (
        <>
          <h3 className="answer__sourcesHeading">Sources</h3>
          <div className="sources">
            {result.sources.map((source, index) => (
              <SourceCard key={`${source.title}-${index}`} source={source} />
            ))}
          </div>
        </>
      ) : null}
    </section>
  )
}
