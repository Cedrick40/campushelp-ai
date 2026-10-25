#!/usr/bin/env node
/**
 * Verification for the CampusHelp AI frontend.
 *
 *   npm run verify
 *
 * It answers one question: does the student interface actually work?
 *
 * It exercises the real code in src/ (never a copy of it) in three ways:
 *
 *   1. Contract checks  - the real src/api.js is loaded and asked for
 *                         answers in mock mode, against the running backend,
 *                         and against a backend that is not there.
 *   2. Browser checks   - the page is opened in headless Chrome and driven
 *                         like a student: submit, click examples, read the
 *                         answer, break the input.
 *   3. Report           - every check is listed with pass, fail or skip.
 *
 * Nothing here is required to run the app. It is a safety net for the
 * frontend, so that "it works" is a measurement and not an opinion.
 */

import { createServer } from 'vite'
import { existsSync, readFileSync } from 'node:fs'
import { createConnection } from 'node:net'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { launchChrome } from './chrome.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '..')
const PORT = Number(process.env.VERIFY_PORT ?? 5199)
const DEAD_PORT = 59999

// ---------------------------------------------------------------- helpers

const results = []
const check = (name, ok, detail = '') => results.push({ name, ok: Boolean(ok), detail })
const skip = (name, reason) => results.push({ name, ok: null, detail: reason })

function readEnvFile(path) {
  const values = {}
  if (!existsSync(path)) return values
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const equals = trimmed.indexOf('=')
    if (equals === -1) continue
    values[trimmed.slice(0, equals).trim()] = trimmed.slice(equals + 1).trim()
  }
  return values
}

const fileEnv = readEnvFile(resolve(root, '.env'))
const backendEnv = readEnvFile(resolve(root, '../backend/.env'))
const BASE_URL = fileEnv.VITE_API_BASE_URL || 'http://localhost:8000'

// The browser may only call the backend from the origin Django allows
// (FRONTEND_ORIGIN in backend/.env). The live browser checks therefore run
// on that exact origin, not on an arbitrary port.
const ALLOWED_ORIGIN = backendEnv.FRONTEND_ORIGIN || 'http://localhost:5173'
const allowedUrl = new URL(ALLOWED_ORIGIN)

/** True when nothing is listening on the port (a plain socket check). */
async function portIsFree(port, host = '127.0.0.1') {
  return new Promise((resolve) => {
    const socket = createConnection({ port, host })
    const finish = (free) => {
      socket.destroy()
      resolve(free)
    }
    socket.on('connect', () => finish(false))
    socket.on('error', () => finish(true))
    socket.setTimeout(1500, () => finish(true))
  })
}

async function startVite({ mock, baseUrl, port = PORT, host = '127.0.0.1' }) {
  process.env.VITE_USE_MOCK = String(mock)
  process.env.VITE_API_BASE_URL = baseUrl
  const server = await createServer({
    root,
    configFile: resolve(root, 'vite.config.js'),
    logLevel: 'error',
    server: { port, strictPort: true, host },
  })
  await server.listen()
  return server
}

async function backendIsUp() {
  try {
    const response = await fetch(`${BASE_URL}/api/ask/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: 'ping' }),
      signal: AbortSignal.timeout(4000),
    })
    return response.ok
  } catch {
    return false
  }
}

// ------------------------------------------------- 1. contract, mock mode

async function contractChecksMock(api) {
  check('mock mode is active', api.isMockMode === true)
  check('backend address comes from VITE_API_BASE_URL', api.API_BASE_URL === BASE_URL, api.API_BASE_URL)

  const answered = await api.askQuestion('When is the deadline to register for exams?')
  check('answered response', answered.status === 'answered', answered.status)
  check('answer has text', typeof answered.answer === 'string' && answered.answer.length > 0)
  check('answer has sources', answered.sources.length > 0, `${answered.sources.length} sources`)
  check(
    'source keeps title, section, page, date and excerpt',
    answered.sources.every(
      (source) =>
        source.title && source.section && source.page !== null && source.date && source.excerpt,
    ),
    JSON.stringify(answered.sources[0]),
  )

  const fallback = await api.askQuestion('Can I get a refund on accommodation fees?')
  check('honest fallback response', fallback.status === 'insufficient_evidence', fallback.status)
  check('fallback has no answer', fallback.answer === null)
  check('fallback explains itself', typeof fallback.message === 'string' && fallback.message.length > 0)
  check('fallback names the office to contact', fallback.contactLine?.office === 'Student Affairs Office')

  const conflict = await api.askQuestion('Is there a conflict between the registration dates?')
  check('conflicting sources response', conflict.status === 'conflicting_sources', conflict.status)
  check('conflict shows more than one source', conflict.sources.length >= 2)

  const failed = await api.askQuestion('please trigger an error')
  check('service failure response', failed.status === 'error', failed.status)

  const corpus = await api.fetchCorpus()
  check('corpus banner data', corpus?.type === 'sample' || corpus?.type === 'official', JSON.stringify(corpus))

  let emptyError = null
  try {
    await api.askQuestion('   ')
  } catch (error) {
    emptyError = error
  }
  check('empty question rejected before any request', emptyError?.kind === 'validation')

  let longError = null
  try {
    await api.askQuestion('x'.repeat(api.MAX_QUESTION_LENGTH + 1))
  } catch (error) {
    longError = error
  }
  check('over-limit question rejected before any request', longError?.kind === 'validation')

  const { normalizeResult } = api
  const relative = normalizeResult({
    status: 'answered',
    answer: 'x',
    sources: [{ title: 'Sample doc', url: '/api/documents/12/file/' }],
  })
  check(
    'relative source links get the backend origin',
    relative.sources[0].url === `${BASE_URL}/api/documents/12/file/`,
    relative.sources[0].url,
  )

  const unknown = normalizeResult({ status: 'something-new', answer: 'x', sources: [] })
  check('an unknown status is never treated as an answer', unknown.status === 'error')

  const sparse = normalizeResult({ status: 'answered', answer: 'x', sources: [{ title: 'Only a title' }] })
  check(
    'a source with missing fields still renders',
    sparse.sources[0].title === 'Only a title' && sparse.sources[0].page === null,
  )
}

// ------------------------------------------------ 2. contract, live backend

async function contractChecksLive(api) {
  let result
  try {
    result = await api.askQuestion('When is the deadline to register for exams?')
  } catch (error) {
    check('live failure is a friendly message', typeof error?.message === 'string' && error.message.length > 0, error?.message)
    skip('live answer received', 'the live service returned an error - the UI shows a retry')
    skip('live answer has text', 'no payload on an error response')
    return
  }
  const statuses = ['answered', 'insufficient_evidence', 'conflicting_sources', 'error']
  check('live answer received', statuses.includes(result.status), result.status)
  check('live sources is a list', Array.isArray(result.sources))
  check(
    'live source fields normalised',
    result.sources.every(
      (source) =>
        typeof source.title === 'string' &&
        source.title.length > 0 &&
        (source.page === null || typeof source.page === 'number'),
    ),
    JSON.stringify(result.sources[0] ?? null),
  )
  if (result.status === 'answered' || result.status === 'conflicting_sources') {
    check('live answer has text', typeof result.answer === 'string' && result.answer.length > 0)
  } else if (result.status === 'insufficient_evidence') {
    skip('live answer has text', 'the backend abstained - this is correct')
  } else {
    skip('live answer has text', 'the backend reported a failure')
  }
}

// ----------------------------------------------- 3. contract, backend down

async function contractChecksOffline(api) {
  let networkError = null
  try {
    await api.askQuestion('When is the deadline to register for exams?')
  } catch (error) {
    networkError = error
  }
  check(
    'an unreachable backend becomes a friendly message',
    networkError?.kind === 'network' && /backend is running/.test(networkError.message),
    networkError?.message,
  )

  const corpus = await api.fetchCorpus()
  check('an unreachable backend leaves the banner honest', corpus === null)
}

// ------------------------------------------------------- 4. browser checks

async function browserChecksMock(driver) {
  await driver.navigate('http://127.0.0.1:' + PORT + '/')
  await driver.waitFor("!!document.querySelector('.ask__input')", 20000)
  await new Promise((resolve) => setTimeout(resolve, 500))

  check('page title', (await driver.evaluate('document.title')) === 'CampusHelp AI')
  check('heading rendered', (await driver.evaluate(driver.text('.masthead__title'))) === 'CampusHelp AI')
  check('banner rendered', (await driver.evaluate(driver.text('.banner'))).length > 0)
  check(
    'three example questions',
    (await driver.evaluate("document.querySelectorAll('.examples__button').length")) === 3,
  )
  check(
    'the conversation starts with the welcome message',
    (await driver.evaluate(driver.text('.chat__welcome'))).includes('Your answer will appear here'),
  )
  check(
    'footer says the project is unofficial',
    (await driver.evaluate(driver.text('.footer__text'))).includes('Unofficial student project'),
  )
  check(
    'mock data is announced',
    (await driver.evaluate(driver.text('.footer__mock'))).includes('Mock data'),
  )

  await driver.evaluate("document.querySelector('.ask__submit').click()")
  await new Promise((resolve) => setTimeout(resolve, 250))
  check(
    'empty question is rejected',
    (await driver.evaluate(driver.text('.ask__error'))).includes('Please enter a question'),
  )
  check(
    'empty question sends no request',
    (await driver.evaluate("!!document.querySelector('.answer--loading')")) === false,
  )

  await driver.evaluate(driver.fillQuestion('x'.repeat(520)))
  await new Promise((resolve) => setTimeout(resolve, 200))
  check(
    'character counter is shown',
    (await driver.evaluate(driver.text('.ask__count'))).includes('520 / 500'),
  )
  await driver.evaluate("document.querySelector('.ask__submit').click()")
  await new Promise((resolve) => setTimeout(resolve, 250))
  check(
    'over-limit question is rejected',
    (await driver.evaluate(driver.text('.ask__error'))).includes('limited to 500 characters'),
  )

  await driver.evaluate("document.querySelectorAll('.examples__button')[0].click()")
  await new Promise((resolve) => setTimeout(resolve, 150))
  check(
    'clicking an example adds the question to the conversation',
    (await driver.evaluate(driver.text('.message--user .bubble--user'))).includes('register for exams'),
  )
  check(
    'a loading state is visible while waiting',
    (await driver.evaluate("!!document.querySelector('.answer--loading')")) === true,
  )
  await driver.waitFor("!!document.querySelector('.answer--answered')", 15000)
  check('the answer is rendered', (await driver.evaluate(driver.text('.answer--answered .answer__text'))).length > 0)
  check('the answer is labelled', (await driver.evaluate(driver.text('.answer--answered .answer__status'))).toLowerCase() === 'answer')
  check('source cards are rendered', (await driver.evaluate("document.querySelectorAll('.answer--answered .source').length")) > 0)
  check('the source excerpt is rendered', (await driver.evaluate(driver.text('.answer--answered .source__excerpt'))).length > 0)
  check(
    'the source details are rendered',
    (await driver.evaluate(driver.text('.answer--answered .source__meta'))).includes('Section') &&
      (await driver.evaluate(driver.text('.answer--answered .source__meta'))).includes('Date'),
  )

  await driver.evaluate(driver.fillQuestion('Can I get a refund on accommodation fees?'))
  await new Promise((resolve) => setTimeout(resolve, 150))
  await driver.evaluate("document.querySelector('.ask__submit').click()")
  await driver.waitFor("!!document.querySelector('.answer--unverified')", 15000)
  check(
    'the honest fallback is shown',
    (await driver.evaluate(driver.text('.answer--unverified .answer__status'))).toLowerCase() === 'not verified',
  )
  check(
    'the fallback uses the agreed wording',
    (await driver.evaluate(driver.text('.answer--unverified .answer__message'))).includes(
      'I could not verify this from the available documents.',
    ),
  )
  check(
    'the fallback names the office to contact',
    (await driver.evaluate(driver.text('.answer--unverified'))).includes('Student Affairs Office'),
  )

  await driver.evaluate(driver.fillQuestion('Is there a conflict between the registration dates?'))
  await new Promise((resolve) => setTimeout(resolve, 150))
  await driver.evaluate("document.querySelector('.ask__submit').click()")
  await driver.waitFor("!!document.querySelector('.answer--conflict')", 15000)
  check(
    'conflicting sources are shown',
    (await driver.evaluate(driver.text('.answer--conflict .answer__status'))).toLowerCase() === 'sources disagree',
  )
  check(
    'both conflicting sources are shown',
    (await driver.evaluate("document.querySelectorAll('.answer--conflict .source').length")) >= 2,
  )

  await driver.evaluate(driver.fillQuestion('please trigger an error'))
  await new Promise((resolve) => setTimeout(resolve, 150))
  await driver.evaluate("document.querySelector('.ask__submit').click()")
  await driver.waitFor("!!document.querySelector('.answer--failed')", 15000)
  check(
    'a service failure is shown',
    (await driver.evaluate(driver.text('.answer--failed .answer__status'))).toLowerCase() === 'request failed',
  )
  check(
    'a service failure offers a retry',
    (await driver.evaluate(driver.text('.answer--failed .answer__retry'))).includes('Try again'),
  )
}

async function browserChecksLive(driver) {
  await driver.navigate(ALLOWED_ORIGIN + '/')
  await driver.waitFor("!!document.querySelector('.ask__input')", 20000)
  await new Promise((resolve) => setTimeout(resolve, 1200))

  const mockNotice = await driver.evaluate(driver.text('.footer__mock'))
  if (mockNotice.includes('Mock data')) {
    skip(
      'live browser checks',
      `the server already running on ${ALLOWED_ORIGIN} is in mock mode - set VITE_USE_MOCK=false and restart it`,
    )
    return
  }

  check(
    'no mock notice in the footer when the backend is connected',
    mockNotice === '',
    mockNotice,
  )

  await driver.evaluate(driver.fillQuestion('When is the deadline to register for exams?'))
  await new Promise((resolve) => setTimeout(resolve, 150))
  await driver.evaluate("document.querySelector('.ask__submit').click()")
  await driver.waitFor(
    "!!document.querySelector('.answer--answered, .answer--unverified, .answer--conflict, .answer--failed')",
    20000,
  )

  const settled = await driver.evaluate(`(() => {
    const panel = document.querySelector('.answer')
    const text = document.querySelector('.answer__text, .answer__message')
    const source = document.querySelector('.source__title')
    return {
      state: panel ? panel.className : '',
      text: text ? text.innerText.trim() : '',
      source: source ? source.innerText.trim() : '',
      emptyMeta: [...document.querySelectorAll('.source__meta dd')].some((dd) => !dd.innerText.trim()),
    }
  })()`)

  check('a live state is rendered', settled.text.length > 0, settled.state)
  check('no empty source metadata values', !settled.emptyMeta, settled.emptyMeta ? 'a source row has an empty value' : '')
  if (settled.state.includes('answer--answered')) {
    check('the live answer is rendered', settled.text.length > 0)
    check('the live source card is rendered', settled.source.length > 0, settled.source)
  } else {
    skip('the live source card is rendered', `the backend settled on ${settled.state}`)
  }

  await driver.evaluate(driver.fillQuestion('   '))
  await new Promise((resolve) => setTimeout(resolve, 150))
  await driver.evaluate("document.querySelector('.ask__submit').click()")
  await new Promise((resolve) => setTimeout(resolve, 400))
  check(
    'an empty question never reaches the backend',
    (await driver.evaluate(driver.text('.ask__error'))).includes('Please enter a question'),
  )
  check(
    'the previous answer survives a blocked submit',
    (await driver.evaluate(driver.text('.answer__text, .answer__message, .answer__placeholder'))).length > 0,
  )
}



// ------------------------------------------------------------------- run

const errors = []
const backendUp = await backendIsUp()

console.log(`\nCampusHelp AI — frontend verification`)
console.log(`backend address: ${BASE_URL}`)
console.log(`backend running: ${backendUp ? 'yes' : 'no'}\n`)

// --- mock mode -------------------------------------------------------------
let server = await startVite({ mock: true, baseUrl: BASE_URL })
try {
  const api = await server.ssrLoadModule('/src/api.js')
  await contractChecksMock(api)
} catch (error) {
  errors.push(`mock contract checks crashed: ${error.message}`)
}

const chrome = await launchChrome({ port: 9333 })
if (!chrome) {
  skip('browser checks', 'no Chrome found on this machine')
} else {
  await chrome.addInitScript(`
    window.__errors = [];
    window.addEventListener('error', (event) => window.__errors.push(String(event.message)));
    window.addEventListener('unhandledrejection', (event) => window.__errors.push(String(event.reason)));
  `)
  try {
    await browserChecksMock(chrome)
    const pageErrors = await chrome.evaluate('window.__errors.join(" | ")')
    check('no uncaught errors in the page', !pageErrors, pageErrors)
  } catch (error) {
    errors.push(`browser checks crashed: ${error.message}`)
  } finally {
    await chrome.close()
  }
}
await server.close()

// --- live backend ----------------------------------------------------------
server = await startVite({ mock: false, baseUrl: BASE_URL })
try {
  const api = await server.ssrLoadModule('/src/api.js')
  if (backendUp) {
    await contractChecksLive(api)
  } else {
    skip('live contract checks', 'backend is not running - start it with: cd backend && python manage.py runserver')
  }
} catch (error) {
  errors.push(`live contract checks crashed: ${error.message}`)
}

if (backendUp) {
  const liveChrome = await launchChrome({ port: 9334 })
  if (!liveChrome) {
    skip('live browser checks', 'no Chrome found on this machine')
  } else {
    // The browser may only reach the backend from the allowed origin, so the
    // live checks run there. If a dev server is already running on that port
    // it is reused, otherwise a temporary one is started.
    let liveServer = null
    const allowedPort = Number(allowedUrl.port || 80)
    if (await portIsFree(allowedPort, allowedUrl.hostname)) {
      liveServer = await startVite({
        mock: false,
        baseUrl: BASE_URL,
        port: allowedPort,
        host: allowedUrl.hostname,
      })
    }
    try {
      await browserChecksLive(liveChrome)
    } catch (error) {
      errors.push(`live browser checks crashed: ${error.message}`)
    } finally {
      await liveChrome.close()
      if (liveServer) await liveServer.close()
    }
  }
} else {
  skip('live browser checks', 'backend is not running')
}
await server.close()

// --- backend unreachable ---------------------------------------------------
server = await startVite({ mock: false, baseUrl: `http://127.0.0.1:${DEAD_PORT}` })
try {
  const api = await server.ssrLoadModule('/src/api.js')
  await contractChecksOffline(api)
} catch (error) {
  errors.push(`offline contract checks crashed: ${error.message}`)
}
await server.close()

// --- report ----------------------------------------------------------------
const passed = results.filter((result) => result.ok === true).length
const failed = results.filter((result) => result.ok === false).length
const skipped = results.filter((result) => result.ok === null).length

for (const result of results) {
  const mark = result.ok === true ? 'PASS' : result.ok === false ? 'FAIL' : 'SKIP'
  console.log(`${mark}  ${result.name}${result.detail ? `  -> ${result.detail}` : ''}`)
}

for (const error of errors) console.log(`\nERROR ${error}`)

console.log(
  `\n${passed} passed, ${failed} failed, ${skipped} skipped, ${results.length} checks total`,
)

if (failed > 0 || errors.length > 0) {
  console.log('\nThe frontend is NOT verified. Fix the failures above before merging.\n')
  process.exit(1)
}
console.log('\nThe frontend is verified.\n')
process.exit(0)
