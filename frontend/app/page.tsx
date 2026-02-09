'use client'

import { useState, useEffect, useCallback } from 'react'
import ChatInterface from '@/components/ChatInterface'
import Header from '@/components/Header'
import { AppMode } from '@/components/Header'
import ChatHistorySidebar from '@/components/ChatHistorySidebar'
import ExamPrepMode from '@/components/exam-prep/ExamPrepMode'
import PersonalizedMode from '@/components/personalized/PersonalizedMode'
import { Message, ChatSession } from '@/lib/types'
import {
  loadChatSessions,
  createChatSession,
  saveChatSession,
  deleteChatSession,
} from '@/lib/chatHistory'

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [mode, setMode] = useState<AppMode>('chat')
  // Load sessions on mount
  useEffect(() => {
    const loaded = loadChatSessions()
    setSessions(loaded)
    // If there are sessions, load the most recent one
    if (loaded.length > 0) {
      setActiveSessionId(loaded[0].id)
      setMessages(
        loaded[0].messages.map((m) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }))
      )
    }
  }, [])

  // Persist current session when messages change (called from ChatInterface)
  const handleMessagesChange = useCallback(() => {
    if (!activeSessionId) return

    // Use a timeout to get the latest messages from state
    setTimeout(() => {
      setMessages((currentMessages) => {
        // Only save if there are messages
        if (currentMessages.length === 0) return currentMessages

        const session: ChatSession = {
          id: activeSessionId,
          title: 'New Chat',
          messages: currentMessages.map((m) => ({
            ...m,
            timestamp: m.timestamp instanceof Date ? m.timestamp : new Date(m.timestamp),
          })),
          createdAt:
            sessions.find((s) => s.id === activeSessionId)?.createdAt ||
            new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }

        saveChatSession(session)
        setSessions(loadChatSessions())

        return currentMessages
      })
    }, 50)
  }, [activeSessionId, sessions])

  // Start a new chat
  const handleNewChat = useCallback(() => {
    const newSession = createChatSession()
    saveChatSession(newSession)
    setSessions(loadChatSessions())
    setActiveSessionId(newSession.id)
    setMessages([])
  }, [])

  // Switch to an existing session
  const handleSelectSession = useCallback(
    (sessionId: string) => {
      // Save current session first
      if (activeSessionId && messages.length > 0) {
        const current: ChatSession = {
          id: activeSessionId,
          title: 'New Chat',
          messages,
          createdAt:
            sessions.find((s) => s.id === activeSessionId)?.createdAt ||
            new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }
        saveChatSession(current)
      }

      // Load selected session
      const target = sessions.find((s) => s.id === sessionId)
      if (target) {
        setActiveSessionId(target.id)
        setMessages(
          target.messages.map((m) => ({
            ...m,
            timestamp: new Date(m.timestamp),
          }))
        )
      }
      setSessions(loadChatSessions())
    },
    [activeSessionId, messages, sessions]
  )

  // Delete a session
  const handleDeleteSession = useCallback(
    (sessionId: string) => {
      deleteChatSession(sessionId)
      const updated = loadChatSessions()
      setSessions(updated)

      if (activeSessionId === sessionId) {
        if (updated.length > 0) {
          setActiveSessionId(updated[0].id)
          setMessages(
            updated[0].messages.map((m) => ({
              ...m,
              timestamp: new Date(m.timestamp),
            }))
          )
        } else {
          // Create a fresh session
          const fresh = createChatSession()
          saveChatSession(fresh)
          setSessions(loadChatSessions())
          setActiveSessionId(fresh.id)
          setMessages([])
        }
      }
    },
    [activeSessionId]
  )

  // Ensure there's always an active session
  useEffect(() => {
    if (!activeSessionId && sessions.length === 0) {
      const fresh = createChatSession()
      saveChatSession(fresh)
      setSessions(loadChatSessions())
      setActiveSessionId(fresh.id)
    }
  }, [activeSessionId, sessions.length])

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar - push layout, not overlay */}
      <ChatHistorySidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => {
          handleSelectSession(id)
          setMode('chat')
        }}
        onNewChat={() => {
          handleNewChat()
          setMode('chat')
        }}
        onDeleteSession={handleDeleteSession}
      />

      {/* Main content area - expands/contracts with sidebar */}
      <div className="flex flex-col flex-1 min-w-0 transition-all duration-300">
        <Header
          isSidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
          onNewChat={handleNewChat}
          mode={mode}
          onModeChange={setMode}
        />

        <main className="flex-1 flex flex-col min-h-0">
          {mode === 'chat' ? (
            <ChatInterface
              messages={messages}
              setMessages={setMessages}
              onMessagesChange={handleMessagesChange}
            />
          ) : mode === 'exam-prep' ? (
            <ExamPrepMode />
          ) : (
            <PersonalizedMode />
          )}
        </main>
      </div>
    </div>
  )
}
