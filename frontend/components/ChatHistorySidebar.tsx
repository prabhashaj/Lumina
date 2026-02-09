'use client'

import { useState } from 'react'
import { MessageSquare, Plus, Trash2, Clock } from 'lucide-react'
import { ChatSession } from '@/lib/types'
import { groupSessionsByDate } from '@/lib/chatHistory'

interface ChatHistorySidebarProps {
  isOpen: boolean
  onClose: () => void
  sessions: ChatSession[]
  activeSessionId: string | null
  onSelectSession: (sessionId: string) => void
  onNewChat: () => void
  onDeleteSession: (sessionId: string) => void
}

export default function ChatHistorySidebar({
  isOpen,
  onClose,
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
}: ChatHistorySidebarProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  const grouped = groupSessionsByDate(sessions)

  const handleDelete = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    if (confirmDeleteId === sessionId) {
      onDeleteSession(sessionId)
      setConfirmDeleteId(null)
    } else {
      setConfirmDeleteId(sessionId)
      setTimeout(() => setConfirmDeleteId(null), 3000)
    }
  }

  return (
    <aside
      className={`h-full flex-shrink-0 flex flex-col bg-[hsl(0,0%,8%)] border-r border-border/20 overflow-hidden transition-all duration-300 ease-in-out ${
        isOpen ? 'w-[280px]' : 'w-0'
      }`}
    >
      {/* Inner wrapper to prevent content collapse */}
      <div className="w-[280px] h-full flex flex-col min-w-[280px]">
        {/* Sidebar header */}
        <div className="flex items-center justify-between px-4 h-14 border-b border-border/15 flex-shrink-0">
          <div className="flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-muted-foreground/50" />
            <span className="text-[13px] font-semibold text-foreground/80">History</span>
          </div>
        </div>

        {/* New Chat button */}
        <div className="px-3 py-3 flex-shrink-0">
          <button
            onClick={() => {
              onNewChat()
            }}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl border border-border/30 hover:border-[hsl(73,31%,45%)]/30 bg-card/20 hover:bg-[hsl(73,31%,45%)]/8 text-foreground/80 hover:text-foreground text-sm font-medium transition-all duration-200"
          >
            <Plus className="w-4 h-4 text-[hsl(73,31%,45%)]" />
            New Chat
          </button>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto px-2 pb-4">
          {sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-muted-foreground">
              <MessageSquare className="w-8 h-8 mb-2 opacity-20" />
              <p className="text-xs text-muted-foreground/50">No conversations yet</p>
            </div>
          ) : (
            grouped.map((group) => (
              <div key={group.label} className="mb-4">
                <p className="px-3 py-1.5 text-[10px] font-bold text-muted-foreground/40 uppercase tracking-widest">
                  {group.label}
                </p>
                <div className="space-y-0.5">
                  {group.sessions.map((session) => (
                    <div
                      key={session.id}
                      onClick={() => {
                        onSelectSession(session.id)
                      }}
                      onMouseEnter={() => setHoveredId(session.id)}
                      onMouseLeave={() => {
                        setHoveredId(null)
                        if (confirmDeleteId === session.id) setConfirmDeleteId(null)
                      }}
                      className={`group relative flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 text-sm ${
                        activeSessionId === session.id
                          ? 'bg-[hsl(73,31%,45%)]/10 text-foreground border border-[hsl(73,31%,45%)]/15'
                          : 'hover:bg-muted/25 text-foreground/60 hover:text-foreground/80 border border-transparent'
                      }`}
                    >
                      <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${
                        activeSessionId === session.id ? 'text-[hsl(73,31%,45%)]' : 'text-muted-foreground/40'
                      }`} />
                      <span className="flex-1 truncate text-[13px]">{session.title}</span>
                      
                      {/* Delete button */}
                      {hoveredId === session.id && (
                        <button
                          onClick={(e) => handleDelete(e, session.id)}
                          className={`flex-shrink-0 p-1 rounded-lg transition-all duration-200 ${
                            confirmDeleteId === session.id
                              ? 'bg-red-500/15 text-red-400 hover:bg-red-500/25'
                              : 'hover:bg-muted/40 text-muted-foreground/40 hover:text-red-400'
                          }`}
                          title={confirmDeleteId === session.id ? 'Click again to confirm' : 'Delete chat'}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  )
}
