/**
 * API layer for CampusHelp AI.
 *
 * The backend address lives in VITE_API_BASE_URL (see frontend/.env). Set
 * VITE_API_SAME_ORIGIN=true when the static host proxies /proxy-api to the
 * backend's /api (Vercel does this in vercel.json); the build then calls
 * /proxy-api on its own origin and ignores any baked backend URL.
 *
 * Two modes, switched by VITE_USE_MOCK:
 *
 *   VITE_USE_MOCK=true   -> answers come from src/mockApi.js, no backend needed
 *   VITE_USE_MOCK=false  -> answers come from the real Django API
 *
 * Both modes return the exact same shape, so the UI never knows which one it
 * is talking to. That is what lets the interface be built and demoed before
 * the backend exists, then switched over by changing one environment value.
 *
 * Contract (devpost/spec.md > API > POST /api/ask/):
 *   request   { "question": "..." }
 *   response  { "status": "answered" | "insufficient_evidence" |
 *                        "conflicting_sources" | "error",
 *               "answer": string | null,
 *               "sources": [ { "title", "url", "section", "page",
 *                              "date", "excerpt" } ],
 *               "message": string | null,
 *               "contact_line": { "office", "source" } | null }
 */

import { mockAsk, mockCorpus } from './mockApi.js'

const runtimeConfig =
  typeof globalThis !== 'undefined' &&
  globalThis.CAMPUSHELP_CONFIG &&
  typeof globalThis.CAMPUSHELP_CONFIG === 'object'
    ? globalThis.CAMPUSHELP_CONFIG
    : {}

const runtimeBaseUrl =
  typeof runtimeConfig.apiBaseUrl === 'string'
    ? runtimeConfig.apiBaseUrl.trim()
    : ''

const sameOrigin =
  String(import.meta.env?.VITE_API_SAME_ORIGIN ?? 'false').toLowerCase() ===
  'true'

const rawBaseUrl =
  runtimeBaseUrl ||
  (sameOrigin ? '' : import.meta.env?.VITE_API_BASE_URL || '')

/** Backend origin without a trailing slash, e.g. "http://localhost:8000". */
export const API_BASE_URL = String(rawBaseUrl).replace(/\/+$/, '')

// Vercel reserves /api for serverless functions, so the Vercel rewrite uses
// /proxy-api and maps it to the backend's /api. Keep the public API paths
// unchanged; only the same-origin build swaps the prefix.
const SAME_ORIGIN_PROXY = '/proxy-api'

function resolveApiPath(path) {
  if (sameOrigin && path.startsWith('/api/')) {
    return `${SAME_ORIGIN_PROXY}/${path.slice('/api/'.length)}`
  }
  return `${API_BASE_URL}${path}`
}

const runtimeMock =
  typeof runtimeConfig.useMock === 'boolean' ? runtimeConfig.useMock : null

/** True while the app answers from the local mock instead of the backend. */
export const isMockMode =
  runtimeMock ??
  (String(import.meta.env?.VITE_USE_MOCK ?? 'false').toLowerCase() === 'true')

/** Question length limit, enforced here and by the backend. */
export const MAX_QUESTION_LENGTH = 500

/**
 * The auth token is kept in localStorage so a refresh keeps the session.
 * Local storage is only touched in the browser, never during the Node
 * verification checks.
 */
const TOKEN_KEY = 'campushelp.auth.token'

export function getToken() {
  try {
    return globalThis.localStorage?.getItem(TOKEN_KEY) ?? null
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    if (token) globalThis.localStorage?.setItem(TOKEN_KEY, token)
    else globalThis.localStorage?.removeItem(TOKEN_KEY)
  } catch {
    // Storage can be blocked; the session then lasts for this page only.
  }
}

export function clearToken() {
  setToken(null)
}

/** Give up on a request that hangs, so the student gets a retry message. */
const REQUEST_TIMEOUT_MS = Number(import.meta.env?.VITE_REQUEST_TIMEOUT_MS ?? 30000)

const KNOWN_STATUSES = new Set([
  'answered',
  'insufficient_evidence',
  'conflicting_sources',
  'error',
])

/** An error the UI can show to the student without leaking internals. */
export class ApiError extends Error {
  constructor(message, { status = null, kind = 'network' } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.kind = kind
  }
}

/**
 * Source links come back in two shapes: a public URL for official documents,
 * and a backend path such as "/api/documents/12/file/" for sample documents.
 * The path form needs the backend origin (or the same-origin proxy)
 * prepended to stay clickable.
 */
function resolveUrl(url) {
  if (!url) return null
  const value = String(url).trim()
  if (!value) return null
  if (/^https?:\/\//i.test(value)) return value
  if (value.startsWith('/')) return resolveApiPath(value)
  return value
}

/**
 * A missing page stays missing. Number(null) and Number('') are both 0, so
 * the empty cases are filtered out before converting.
 */
function normalizePage(value) {
  if (value === null || value === undefined || value === '') return null
  const page = Number(value)
  return Number.isFinite(page) ? page : null
}

function normalizeSource(raw = {}) {
  return {
    title: String(raw.title ?? '').trim() || 'Untitled source',
    url: resolveUrl(raw.url),
    section: String(raw.section ?? '').trim() || null,
    page: normalizePage(raw.page),
    date: String(raw.date ?? '').trim() || null,
    excerpt: String(raw.excerpt ?? '').trim() || null,
  }
}

function normalizeContactLine(raw) {
  if (!raw || typeof raw !== 'object') return null
  const office = String(raw.office ?? '').trim()
  if (!office) return null
  const source = String(raw.source ?? '').trim()
  return { office, source: source || null }
}

/**
 * Turn a raw API payload into the shape the components render, so a missing
 * optional field never crashes a card and an unknown status never renders as
 * a successful answer.
 */
export function normalizeResult(payload) {
  const status = KNOWN_STATUSES.has(payload?.status) ? payload.status : 'error'
  const answer = String(payload?.answer ?? '').trim()
  const message = String(payload?.message ?? '').trim()
  return {
    status,
    answer: answer || null,
    message: message || null,
    contactLine: normalizeContactLine(payload?.contactLine ?? payload?.contact_line),
    sources: Array.isArray(payload?.sources)
      ? payload.sources.map(normalizeSource)
      : [],
  }
}

const LOOPBACK = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i

function backendTarget() {
  if (API_BASE_URL) return API_BASE_URL
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin
  }
  return 'the backend'
}

/** True when a build made on a laptop is still pointed at localhost online. */
function pointsAtLocalhostFromDeployedPage() {
  return (
    Boolean(API_BASE_URL) &&
    LOOPBACK.test(API_BASE_URL) &&
    typeof window !== 'undefined' &&
    Boolean(window.location?.origin) &&
    !LOOPBACK.test(window.location.origin)
  )
}

async function request(path, { method = 'GET', body } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers.Authorization = `Token ${token}`

  let response
  try {
    response = await fetch(resolveApiPath(path), {
      method,
      headers: Object.keys(headers).length > 0 ? headers : undefined,
      body,
      signal: controller.signal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new ApiError('The request took too long. Please try again.', {
        kind: 'timeout',
      })
    }
    if (pointsAtLocalhostFromDeployedPage()) {
      throw new ApiError(
        `This build points at ${API_BASE_URL}, which only works on your computer. ` +
          'Set VITE_API_BASE_URL (or apiBaseUrl in config.js) to the deployed ' +
          'backend address, then redeploy the frontend.',
        { kind: 'config' },
      )
    }
    throw new ApiError(
      `Could not reach the CampusHelp AI service at ${backendTarget()}. ` +
        'Check that the backend is running and that the frontend points at ' +
        'its address.',
      { kind: 'network' },
    )
  } finally {
    clearTimeout(timer)
  }

  const text = await response.text()
  let payload = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) {
    if (response.status === 401) clearToken()
    const detail = String(payload?.message ?? '').trim()
    throw new ApiError(
      detail || `The service returned an error (HTTP ${response.status}).`,
      { status: response.status, kind: 'http' },
    )
  }

  if (response.status === 204) return null

  if (!payload || typeof payload !== 'object') {
    throw new ApiError('The service returned an unreadable response. Please try again.', {
      kind: 'parse',
    })
  }

  return payload
}

/**
 * Ask a question and return the normalized result.
 * Throws ApiError for validation problems, transport failures and bad status
 * codes; the caller turns that into the failure state with a retry button.
 */
export async function askQuestion(question) {
  const trimmed = String(question ?? '').trim()

  if (!trimmed) {
    throw new ApiError('Please enter a question.', { kind: 'validation' })
  }
  if (trimmed.length > MAX_QUESTION_LENGTH) {
    throw new ApiError(
      `Questions are limited to ${MAX_QUESTION_LENGTH} characters. Please shorten your question.`,
      { kind: 'validation' },
    )
  }

  if (isMockMode) {
    return normalizeResult(await mockAsk(trimmed))
  }

  return normalizeResult(
    await request('/api/ask/', {
      method: 'POST',
      body: JSON.stringify({ question: trimmed }),
    }),
  )
}

/**
 * Corpus metadata for the university label. Returns null when the endpoint
 * is missing or fails, so the page never invents a university name or a
 * last-checked date.
 */
export async function fetchCorpus() {
  if (isMockMode) {
    return mockCorpus()
  }

  try {
    const payload = await request('/api/corpus/')
    const type = payload?.type
    if (type !== 'sample' && type !== 'official') return null
    return {
      type,
      university: String(payload?.university ?? '').trim() || null,
      lastChecked: String(payload?.last_checked ?? '').trim() || null,
    }
  } catch {
    return null
  }
}

/* ------------------------------------------------------------------ accounts */

function normalizeUser(raw) {
  return {
    id: raw?.id ?? null,
    email: String(raw?.email ?? '').trim(),
    name: String(raw?.name ?? '').trim(),
  }
}

function storeSession(payload) {
  const token = String(payload?.token ?? '').trim()
  if (!token) {
    throw new ApiError('The service did not return a session. Please try again.', {
      kind: 'parse',
    })
  }
  setToken(token)
  return normalizeUser(payload?.user)
}

export async function registerAccount({ email, password, name }) {
  return storeSession(
    await request('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    }),
  )
}

export async function loginAccount({ email, password }) {
  return storeSession(
    await request('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  )
}

/** Restore a saved login on page load. Returns null when there is no session. */
export async function restoreSession() {
  if (!getToken()) return null
  try {
    return normalizeUser(await request('/api/auth/me/'))
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

/** Revoke the token on the server, then forget it locally. */
export async function logoutAccount() {
  if (!getToken()) return
  try {
    await request('/api/auth/logout/', { method: 'POST' })
  } catch {
    // The token may already be gone; clearing it locally is what matters.
  } finally {
    clearToken()
  }
}

/* ------------------------------------------------------------------- history */

function normalizeEntry(raw) {
  const question = String(raw?.question ?? '').trim()
  return {
    id: raw?.id ?? null,
    conversationId: raw?.conversation ?? null,
    question,
    result: raw?.result ? normalizeResult(raw.result) : null,
    createdAt: String(raw?.created_at ?? '').trim() || null,
  }
}

function normalizeConversation(raw) {
  return {
    id: raw?.id ?? null,
    title: String(raw?.title ?? '').trim() || 'Saved chat',
    entryCount: Number(raw?.entry_count ?? raw?.entries?.length ?? 0) || 0,
    createdAt: String(raw?.created_at ?? '').trim() || null,
    updatedAt: String(raw?.updated_at ?? raw?.created_at ?? '').trim() || null,
  }
}

function normalizeConversationDetail(raw) {
  return {
    ...normalizeConversation(raw),
    entries: Array.isArray(raw?.entries) ? raw.entries.map(normalizeEntry) : [],
  }
}

export async function fetchConversations() {
  const payload = await request('/api/history/')
  return Array.isArray(payload) ? payload.map(normalizeConversation) : []
}

export async function fetchConversation(id) {
  return normalizeConversationDetail(await request(`/api/history/${id}/`))
}

export async function saveHistoryEntry({ question, result, conversationId }) {
  const payload = await request('/api/history/', {
    method: 'POST',
    body: JSON.stringify({
      question,
      result,
      ...(conversationId ? { conversation: conversationId } : {}),
    }),
  })
  return {
    entry: normalizeEntry(payload?.entry),
    conversation: normalizeConversation(payload?.conversation),
  }
}

export async function deleteConversation(id) {
  await request(`/api/history/${id}/`, { method: 'DELETE' })
}

export async function clearHistory() {
  await request('/api/history/', { method: 'DELETE' })
}
