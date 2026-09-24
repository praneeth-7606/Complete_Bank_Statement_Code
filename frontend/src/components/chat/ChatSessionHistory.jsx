import { useState } from 'react'
import { History, X, RotateCcw, Trash2, MessageSquare } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const formatWhen = (ts) => {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    if (Number.isNaN(d.getTime())) return ''
    return d.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

/**
 * Dropdown listing the active session (summary) plus archived sessions.
 * Click an archived session to restore it as active.
 */
const ChatSessionHistory = ({
  activeId,
  activeTitle,
  activeCount,
  archived = [],
  onOpen,
  onDelete,
  accent = 'blue',
}) => {
  const [open, setOpen] = useState(false)

  const accentBtn =
    accent === 'emerald'
      ? 'hover:border-emerald-400/50 hover:text-emerald-600 dark:hover:text-emerald-400'
      : 'hover:border-primary-400/50 hover:text-primary-600 dark:hover:text-primary-400'

  const empty = !archived.length

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] transition-all text-[var(--text-secondary)] text-xs font-semibold ${accentBtn}`}
        title="Session history"
      >
        <History className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">History</span>
        {archived.length > 0 && (
          <span className="ml-0.5 min-w-[1.1rem] h-4 px-1 rounded-full bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[9px] font-bold flex items-center justify-center">
            {archived.length}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setOpen(false)}
              aria-hidden
            />
            <motion.div
              initial={{ opacity: 0, y: -6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.98 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-full mt-2 z-50 w-72 sm:w-80 max-h-80 overflow-y-auto bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl shadow-lg p-2"
            >
              <div className="flex items-center justify-between px-2 py-1.5 mb-1">
                <p className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-primary-500" />
                  Sessions
                </p>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="p-1 rounded hover:bg-[var(--bg-surface)] text-[var(--text-secondary)]"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="px-2 py-2 rounded-lg bg-primary-50 dark:bg-primary-900/20 border border-primary-200/50 dark:border-primary-800/50 mb-1.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-primary-600 dark:text-primary-400">
                      Current
                    </p>
                    <p className="text-xs font-medium text-[var(--text-primary)] truncate mt-0.5">
                      {activeTitle || 'New conversation'}
                    </p>
                    <p className="text-[10px] text-[var(--text-secondary)] mt-0.5">
                      {activeCount} message{activeCount === 1 ? '' : 's'}
                    </p>
                  </div>
                </div>
              </div>

              <p className="px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-[var(--text-secondary)]">
                Previous
              </p>

              {empty ? (
                <p className="px-2 py-3 text-xs text-[var(--text-secondary)]">
                  No previous sessions. Clear the chat to archive this one.
                </p>
              ) : (
                archived.map((s) => (
                  <div
                    key={s.id}
                    className="group flex items-start gap-2 px-2 py-2 rounded-lg hover:bg-[var(--bg-surface)] transition-colors"
                  >
                    <button
                      type="button"
                      onClick={() => {
                        onOpen?.(s.id)
                        setOpen(false)
                      }}
                      className="flex-1 min-w-0 text-left"
                      title="Restore this session"
                    >
                      <p className="text-xs font-medium text-[var(--text-primary)] truncate">
                        {s.title || 'Untitled session'}
                      </p>
                      <p className="text-[10px] text-[var(--text-secondary)] mt-0.5">
                        {s.messageCount || s.messages?.length || 0} msg
                        {s.archivedAt ? ` · ${formatWhen(s.archivedAt)}` : ''}
                      </p>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        onOpen?.(s.id)
                        setOpen(false)
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded text-[var(--text-secondary)] hover:text-primary-600 transition-all"
                      title="Restore"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        onDelete?.(s.id)
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded text-[var(--text-secondary)] hover:text-red-600 transition-all"
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}

export default ChatSessionHistory
