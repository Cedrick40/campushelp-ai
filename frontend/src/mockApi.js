/**
 * Mock backend for the frontend.
 *
 * It answers with the same payload shapes as the Django API so the interface
 * can be built, reviewed and demoed before the backend is wired up. Switch it
 * off with VITE_USE_MOCK=false in frontend/.env to use the real API.
 *
 * The wording below is clearly sample content, not real university policy.
 */

const MOCK_CORPUS = {
  type: 'sample',
  university: 'Sample University',
  last_checked: '2026-10-20',
}

const MOCK_SOURCES = {
  examRegistration: {
    title: 'Academic Calendar 2026 (sample)',
    section: 'Examination registration',
    page: 12,
    date: '2026-01-15',
    excerpt:
      'Examination registration opens on 6 April 2026 and closes at 17:00 on 17 April 2026. Late registration requires written approval from the Head of Department.',
    url: null,
  },
  libraryHours: {
    title: 'Student Handbook 2026 (sample)',
    section: 'Library services',
    page: 34,
    date: '2026-02-01',
    excerpt:
      'The main library is open Monday to Friday from 08:00 to 22:00 and on Saturdays from 09:00 to 16:00 during term time.',
    url: null,
  },
  fees: {
    title: 'Fees and Payments Policy 2026 (sample)',
    section: 'Accommodation refunds',
    page: 21,
    date: '2026-03-02',
    excerpt:
      'Accommodation fee refunds are processed by the Student Affairs Office within 30 days of the approved withdrawal date.',
    url: null,
  },
  conflictingDeadline: {
    title: 'Academic Calendar 2026 (sample)',
    section: 'Examination registration',
    page: 12,
    date: '2026-01-15',
    excerpt:
      'Examination registration closes at 17:00 on 17 April 2026 for all faculties.',
    url: null,
  },
  conflictingNotice: {
    title: 'Faculty Notice on Examinations (sample)',
    section: 'Revised registration dates',
    page: 1,
    date: '2026-03-28',
    excerpt:
      'Following a change in the examination schedule, the Faculty advises that registration now closes on 24 April 2026.',
    url: null,
  },
}

const MOCK_LATENCY_MS = 700

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function copy(source) {
  return { ...source }
}

/**
 * Decides which mock response a question gets. Keyword matching is enough
 * for a mock; the real relevance logic lives in the backend.
 */
export async function mockAsk(question) {
  await delay(MOCK_LATENCY_MS)

  const text = question.toLowerCase()

  if (text.includes('error')) {
    return {
      status: 'error',
      answer: null,
      sources: [],
      message: 'The service is temporarily unavailable. Please try again.',
      contact_line: null,
    }
  }

  if (/refund|accommodation fee|hostel fee|money back/.test(text)) {
    return {
      status: 'insufficient_evidence',
      answer: null,
      sources: [],
      message:
        'I could not verify this from the available documents. The documents describe how refunds are processed, but not whether a refund can be granted.',
      contact_line: {
        office: 'Student Affairs Office',
        source: 'Student Handbook 2026 (sample), Student affairs contacts',
      },
    }
  }

  if (/conflict|disagree|different date/.test(text)) {
    return {
      status: 'conflicting_sources',
      answer:
        'The two documents in the knowledge base give different closing dates for examination registration, so I cannot confirm one of them.',
      sources: [copy(MOCK_SOURCES.conflictingDeadline), copy(MOCK_SOURCES.conflictingNotice)],
      message: 'These sources disagree.',
      contact_line: null,
    }
  }

  if (/library|opening hours|opening time/.test(text)) {
    return {
      status: 'answered',
      answer:
        'During term time the main library is open Monday to Friday from 08:00 to 22:00, and on Saturdays from 09:00 to 16:00.',
      sources: [copy(MOCK_SOURCES.libraryHours)],
      message: null,
      contact_line: null,
    }
  }

  if (/register|registration|exam/.test(text)) {
    return {
      status: 'answered',
      answer:
        'Examination registration closes at 17:00 on 17 April 2026. Late registration needs written approval from the Head of Department.',
      sources: [copy(MOCK_SOURCES.examRegistration), copy(MOCK_SOURCES.fees)],
      message: null,
      contact_line: null,
    }
  }

  return {
    status: 'answered',
    answer:
      'The documents I have do not cover that topic directly, but the closest information is in the fees and payments policy.',
    sources: [copy(MOCK_SOURCES.fees)],
    message: null,
    contact_line: null,
  }
}

export function mockCorpus() {
  return { ...MOCK_CORPUS }
}
