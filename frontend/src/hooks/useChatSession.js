import { useCallback, useEffect, useRef, useState } from 'react'
import {
  archiveAndStartNew,
  clearAllChatNamespaces,
  deleteArchived,
  loadSessionState,
  restoreArchived,
  saveSessionState,
} from '../utils/chatSession'

/**
 * Persist a chat conversation across route/tab remounts.
 * - Survives navigation and full app reloads (localStorage).
 * - Clear archives the session and starts a new one (history summary kept).
 * - Archived sessions can be restored from the history panel.
 */
export const useChatSession = (namespace, welcomeText) => {
  const [state, setState] = useState(() =>
    loadSessionState(namespace, welcomeText)
  )
  const saveTimer = useRef(null)
  const stateRef = useRef(state)
  stateRef.current = state

  useEffect(() => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      saveSessionState(namespace, stateRef.current)
    }, 250)
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
    }
  }, [namespace, state])

  useEffect(() => {
    const flush = () => saveSessionState(namespace, stateRef.current)
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') flush()
    }
    window.addEventListener('beforeunload', flush)
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      flush()
      window.removeEventListener('beforeunload', flush)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [namespace])

  const messages = state.active?.messages || []

  const setMessages = useCallback((updater) => {
    setState((prev) => {
      const current = prev.active?.messages || []
      const nextMsgs =
        typeof updater === 'function' ? updater(current) : updater
      return {
        ...prev,
        active: {
          ...prev.active,
          messages: nextMsgs,
          updatedAt: Date.now(),
        },
      }
    })
  }, [])

  const appendMessage = useCallback((message) => {
    setState((prev) => ({
      ...prev,
      active: {
        ...prev.active,
        messages: [...(prev.active?.messages || []), message],
        updatedAt: Date.now(),
      },
    }))
  }, [])

  const clearSession = useCallback(() => {
    setState((prev) => archiveAndStartNew(namespace, prev, welcomeText))
  }, [namespace, welcomeText])

  const openArchived = useCallback(
    (sessionId) => {
      setState((prev) => restoreArchived(namespace, prev, sessionId, welcomeText))
    },
    [namespace, welcomeText]
  )

  const removeArchived = useCallback(
    (sessionId) => {
      setState((prev) => deleteArchived(namespace, prev, sessionId))
    },
    [namespace]
  )

  return {
    messages,
    setMessages,
    appendMessage,
    clearSession,
    openArchived,
    removeArchived,
    archived: state.archived || [],
    activeId: state.activeId || state.active?.id,
  }
}

export { clearAllChatNamespaces }
