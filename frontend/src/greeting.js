export function timeGreeting(date = new Date()) {
  const hour = date.getHours()

  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

export function greetingName(user) {
  const name = String(user?.name ?? '').trim()
  if (name) return name

  const email = String(user?.email ?? '').trim()
  if (!email) return 'there'

  return email.split('@')[0].trim() || 'there'
}

export function welcomeMessage(mode, user, date = new Date()) {
  const name = greetingName(user)

  if (mode === 'register') return `${timeGreeting(date)}, ${name}`
  return `Welcome back, ${name}`
}
