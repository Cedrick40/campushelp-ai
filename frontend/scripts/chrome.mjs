/**
 * A very small Chrome DevTools Protocol driver.
 *
 * Used by scripts/verify.mjs to drive the real page in a real browser
 * without adding a test framework or a browser-downloading dependency.
 * Only Node built-ins are used.
 */

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { setTimeout as sleep } from 'node:timers/promises'

const CHROME_PATHS = [
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
]

/** Returns the Chrome binary, or null when no browser is installed. */
export function findChrome() {
  return CHROME_PATHS.find((path) => existsSync(path)) ?? null
}

/**
 * Launches headless Chrome and returns a small driver object.
 * Returns null when there is no Chrome on this machine.
 */
export async function launchChrome({ port = 9333 } = {}) {
  const binary = findChrome()
  if (!binary) return null

  const profile = join(tmpdir(), `campushelp-verify-chrome-${process.pid}-${port}`)
  const chrome = spawn(
    binary,
    [
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
      '--disable-dev-shm-usage',
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${profile}`,
      'about:blank',
    ],
    { stdio: 'ignore' },
  )
  // Do not let a stuck browser keep the verifier alive. The DevTools socket
  // and the polling fetch below keep Node running while work is in progress.
  chrome.unref()

  let target = null
  const deadline = Date.now() + 15000
  while (!target && Date.now() < deadline) {
    try {
      const response = await fetch(`http://localhost:${port}/json/list`, {
        signal: AbortSignal.timeout(1000),
      })
      const list = await response.json()
      target = list.find((entry) => entry.type === 'page')
    } catch {
      // Chrome is not listening yet, or is too busy to answer in time.
    }
    if (!target) await sleep(250)
  }
  if (!target) {
    chrome.kill('SIGKILL')
    return null
  }

  const socket = new WebSocket(target.webSocketDebuggerUrl)
  let timer
  try {
    const opened = await Promise.race([
      new Promise((resolve, reject) => {
        socket.onopen = () => resolve(true)
        socket.onerror = reject
      }),
      new Promise((resolve) => {
        timer = setTimeout(() => resolve(false), 10000)
      }),
    ])
    if (!opened) throw new Error('Chrome DevTools did not accept a connection')
  } catch {
    try {
      socket.close()
    } catch {
      // already closed
    }
    chrome.kill('SIGKILL')
    return null
  } finally {
    clearTimeout(timer)
  }

  let nextId = 1
  const pending = new Map()
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data)
    if (!message.id || !pending.has(message.id)) return
    const { resolve, reject } = pending.get(message.id)
    pending.delete(message.id)
    if (message.error) reject(new Error(JSON.stringify(message.error)))
    else resolve(message.result)
  }

  function send(method, params = {}) {
    const id = nextId++
    socket.send(JSON.stringify({ id, method, params }))
    return new Promise((resolve, reject) => pending.set(id, { resolve, reject }))
  }

  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', {
      expression,
      awaitPromise: true,
      returnByValue: true,
    })
    if (result.exceptionDetails) {
      throw new Error(
        result.exceptionDetails.exception?.description ?? result.exceptionDetails.text,
      )
    }
    return result.result.value
  }

  async function waitFor(expression, timeoutMs = 15000) {
    const deadline = Date.now() + timeoutMs
    while (Date.now() < deadline) {
      if (await evaluate(expression)) return true
      await sleep(100)
    }
    return false
  }

  async function navigate(url) {
    await send('Page.navigate', { url })
  }

  /** Runs a script in every page before any of the page's own scripts. */
  async function addInitScript(source) {
    await send('Page.addScriptToEvaluateOnNewDocument', { source })
  }

  /** innerText of the first element matching the selector. */
  function text(selector) {
    return `document.querySelector(${JSON.stringify(selector)})?.innerText ?? ''`
  }

  /** Sets the value of the question textarea the way a user would. */
  function fillQuestion(value) {
    return `(() => {
      const field = document.querySelector('.ask__input');
      const set = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
      set.call(field, ${JSON.stringify(value)});
      field.dispatchEvent(new Event('input', { bubbles: true }));
    })()`
  }

  async function close() {
    try {
      socket.close()
    } catch {
      // already closed
    }
    chrome.kill('SIGKILL')
  }

  await send('Page.enable')
  await send('Runtime.enable')

  return { evaluate, waitFor, navigate, addInitScript, text, fillQuestion, close }
}
