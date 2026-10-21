import { formatDate } from '../format.js'
import { DocumentIcon, ExternalLinkIcon } from './icons.jsx'

/**
 * One source card. It always shows the document title, and shows the section,
 * date, page and quoted excerpt when the backend has them. The excerpt is what
 * lets a student check the answer without leaving the page.
 */
export default function SourceCard({ source, index = 0 }) {
  return (
    <article className="source">
      <div className="source__top">
        <span className="source__badge" aria-hidden="true">
          {index + 1}
        </span>
        <h3 className="source__title">
          <DocumentIcon size={14} className="source__titleIcon" />
          <span>{source.title}</span>
        </h3>
      </div>

      <dl className="source__meta">
        {source.section ? (
          <div className="source__metaRow">
            <dt>Section</dt>
            <dd>{source.section}</dd>
          </div>
        ) : null}
        {source.date ? (
          <div className="source__metaRow">
            <dt>Date</dt>
            <dd>{formatDate(source.date)}</dd>
          </div>
        ) : null}
        {source.page !== null && source.page !== undefined ? (
          <div className="source__metaRow">
            <dt>Page</dt>
            <dd>{source.page}</dd>
          </div>
        ) : null}
      </dl>

      {source.excerpt ? (
        <blockquote className="source__excerpt">{source.excerpt}</blockquote>
      ) : null}

      {source.url ? (
        <a
          className="source__link"
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open document
          <ExternalLinkIcon size={13} className="source__linkIcon" />
        </a>
      ) : null}
    </article>
  )
}
