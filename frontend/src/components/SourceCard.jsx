import { formatDate } from '../format.js'

/**
 * One source card. It always shows the document title, and shows the section,
 * date, page and quoted excerpt when the backend has them. The excerpt is what
 * lets a student check the answer without leaving the page.
 */
export default function SourceCard({ source }) {
  return (
    <article className="source">
      <h3 className="source__title">{source.title}</h3>

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
        </a>
      ) : null}
    </article>
  )
}
