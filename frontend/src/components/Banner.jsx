import { InfoIcon, SampleIcon, CheckIcon } from './icons.jsx'
import { formatDate } from '../format.js'

/**
 * The banner states honestly whether the answers come from official documents
 * or from clearly labelled sample data. The data comes from the backend
 * (GET /api/corpus/), so the wording cannot drift from the real corpus.
 *
 * When the corpus endpoint is unavailable we say so rather than guessing.
 */
export default function Banner({ corpus }) {
  if (!corpus) {
    return (
      <div className="banner banner--unknown" role="status">
        <span className="banner__icon">
          <InfoIcon size={15} />
        </span>
        <span className="banner__label">Source status</span>
        <span className="banner__text">
          The information source status is unavailable right now. Answers may be
          missing their source details.
        </span>
      </div>
    )
  }

  if (corpus.type === 'official') {
    const lastChecked = formatDate(corpus.lastChecked)
    return (
      <div className="banner banner--official" role="status">
        <span className="banner__icon">
          <CheckIcon size={15} />
        </span>
        <span className="banner__label">Official documents</span>
        <span className="banner__text">
          Based on official documents from {corpus.university ?? 'the university'}
          {lastChecked ? `, last checked ${lastChecked}` : ''}.
        </span>
      </div>
    )
  }

  return (
    <div className="banner banner--sample" role="status">
      <span className="banner__icon">
        <SampleIcon size={15} />
      </span>
      <span className="banner__label">Sample data</span>
      <span className="banner__text">
        Answers below use example documents, not official university documents.
      </span>
    </div>
  )
}
