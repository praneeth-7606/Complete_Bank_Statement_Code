const STORAGE_PREFIX = 'chat_sessions'
const MAX_ARCHIVED = 20
const MAX_MESSAGES = 200

const welcomeMessage = (text) => ({
  role: 'assistant',
  content: text,
  timestamp: new Date(),
})

const storageKey = (namespace) => `${STORAGE_PREFIX}:${namespace}`

const readJSON = (key) => {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const writeJSON = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Quota or private mode — ignore so chat still works in-memory
  }
}

const serializeMessages = (messages) =>
  (messages || []).slice(-MAX_MESSAGES).map((m) => ({
    role: m.role,
    content: m.content,
    timestamp:
      m.timestamp instanceof Date
        ? m.timestamp.toISOString()
        : m.timestamp || new Date().toISOString(),
  }))

const reviveMessages = (messages) =>
  (messages || []).map((m) => {
    const ts = m.timestamp
    let timestamp
    if (ts instanceof Date && !Number.isNaN(ts.getTime())) {
      timestamp = ts
    } else if (typeof ts === 'string' || typeof ts === 'number') {
      const parsed = new Date(ts)
      timestamp = Number.isNaN(parsed.getTime()) ? new Date() : parsed
    } else {
      timestamp = new Date()
    }
    return { ...m, timestamp }
  })

const summarize = (messages) => {
  const userMsg = (messages || []).find((m) => m.role === 'user' && typeof m.content === 'string')
  const preview = userMsg ? userMsg.content.slice(0, 80) : 'No messages yet'
  return {
    title: preview,
    messageCount: (messages || []).length,
  }
}

export const createSessionState = (welcomeText) => {
  const id = `s_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`
  return {
    activeId: id,
    active: {
      id,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      messages: [welcomeMessage(welcomeText)],
    },
    archived: [],
  }
}

export const loadSessionState = (namespace, welcomeText) => {
  const stored = readJSON(storageKey(namespace))
  if (!stored || !stored.active || !Array.isArray(stored.active.messages)) {
    return createSessionState(welcomeText)
  }
  return {
    activeId: stored.activeId || stored.active.id,
    active: {
      ...stored.active,
      messages: reviveMessages(stored.active.messages),
    },
    archived: Array.isArray(stored.archived)
      ? stored.archived.slice(0, MAX_ARCHIVED).map((s) => ({
          ...s,
          messages: reviveMessages(s.messages),
        }))
      : [],
  }
}

export const saveSessionState = (namespace, state) => {
  if (!state?.active) return
  const payload = {
    activeId: state.activeId || state.active.id,
    active: {
      ...state.active,
      messages: serializeMessages(state.active.messages),
      updatedAt: Date.now(),
    },
    archived: (state.archived || []).slice(0, MAX_ARCHIVED).map((s) => ({
      ...s,
      messages: serializeMessages(s.messages),
    })),
  }
  writeJSON(storageKey(namespace), payload)
}

export const hasRealConversation = (messages) =>
  (messages || []).some((m) => m.role === 'user')

export const archiveAndStartNew = (namespace, state, welcomeText) => {
  const archived = [...(state.archived || [])]
  if (state.active && hasRealConversation(state.active.messages)) {
    const summary = summarize(state.active.messages)
    archived.unshift({
      ...state.active,
      ...summary,
      archivedAt: Date.now(),
    })
  }
  const next = createSessionState(welcomeText)
  next.active.messages = reviveMessages(next.active.messages)
  next.archived = archived.slice(0, MAX_ARCHIVED)
  saveSessionState(namespace, next)
  return next
}

export const restoreArchived = (namespace, state, sessionId, welcomeText) => {
  const archived = state.archived || []
  const target = archived.find((s) => s.id === sessionId)
  if (!target) return state

  const remaining = archived.filter((s) => s.id !== sessionId)
  const nextArchived = [...remaining]
  if (state.active && hasRealConversation(state.active.messages)) {
    const summary = summarize(state.active.messages)
    nextArchived.unshift({
      ...state.active,
      ...summary,
      archivedAt: Date.now(),
    })
  }

  const restored = {
    ...target,
    messages: reviveMessages(target.messages),
  }
  const next = {
    activeId: restored.id,
    active: restored,
    archived: nextArchived.slice(0, MAX_ARCHIVED),
  }
  saveSessionState(namespace, next)
  return next
}

export const deleteArchived = (namespace, state, sessionId) => {
  const next = {
    ...state,
    archived: (state.archived || []).filter((s) => s.id !== sessionId),
  }
  saveSessionState(namespace, next)
  return next
}

export const clearAllSessions = (namespace) => {
  try {
    localStorage.removeItem(storageKey(namespace))
  } catch {
    // ignore
  }
}

export const clearAllChatNamespaces = () => {
  try {
    const keys = []
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith(`${STORAGE_PREFIX}:`)) keys.push(key)
    }
    keys.forEach((k) => localStorage.removeItem(k))
  } catch {
    // ignore
  }
}

export const getSessionSummaryList = (state) => {
  const list = []
  if (state.active && hasRealConversation(state.active.messages)) {
    list.push({
      id: state.active.id,
      title: summarize(state.active.messages).title,
      messageCount: state.active.messages.length,
      updatedAt: state.active.updatedAt || state.active.createdAt,
      isActive: true,
    })
  }
  for (const s of state.archived || []) {
    list.push({
      id: s.id,
      title: s.title || summarize(s.messages).title,
      messageCount: s.messageCount || s.messages?.length || 0,
      updatedAt: s.archivedAt || s.updatedAt,
      isActive: false,
    })
  }
  return list
}
