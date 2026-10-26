/**
 * Small display helpers shared by the banner and the source cards.
 */

/**
 * Format a YYYY-MM-DD date for display. Parsed as a local date so the day
 * never shifts by one because of the timezone.
 */
export function formatDate(value) {
  const text = String(value ?? '').trim()
  if (!text) return null

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text)
  if (!match) return text

  const [, year, month, day] = match
  const date = new Date(Number(year), Number(month) - 1, Number(day))
  if (Number.isNaN(date.getTime())) return text

  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

/**
 * Compact timestamp for the history list: time for today, then day/month,
 * then day/month/year for older entries.
 */
export function formatHistoryTime(value) {
  const text = String(value ?? '').trim()
  if (!text) return ''

  const date = new Date(text)
  if (Number.isNaN(date.getTime())) return ''

  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()

  if (sameDay) {
    return new Intl.DateTimeFormat('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  const sameYear = date.getFullYear() === now.getFullYear()
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    ...(sameYear ? {} : { year: 'numeric' }),
  }).format(date)
}
