'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import ChatInterface from '@/components/ChatInterface'
import Header from '@/components/Header'
import { AppMode } from '@/components/Header'
import ChatHistorySidebar from '@/components/ChatHistorySidebar'
import ExamPrepMode from '@/components/exam-prep/ExamPrepMode'
import PersonalizedMode from '@/components/personalized/PersonalizedMode'
import VideoLectureMode from '@/components/video-lecture/VideoLectureMode'
import DoubtSolverMode from '@/components/doubt-solver/DoubtSolverMode'

import { Message, ChatSession } from '@/lib/types'
import {
  loadChatSessions,
  createChatSession,
  saveChatSession,
  deleteChatSession,
} from '@/lib/chatHistory'
import { Sparkles } from 'lucide-react'

export default function AppPage() {
  const router = useRouter()
  const { user, isLoading, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [mode, setMode] = useState<AppMode>('chat')

  // Redirect unauthenticated users to login
  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login')
    }
  }, [user, isLoading, router])

  // Load sessions on mount
  useEffect(() => {
    if (!user) return
    const loaded = loadChatSessions()
    setSessions(loaded)
    if (loaded.length > 0) {
      setActiveSessionId(loaded[0].id)
      setMessages(
        loaded[0].messages.map((m) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }))
      )
    }
  }, [user])

  const handleMessagesChange = useCallback(() => {
    if (!activeSessionId) return
    setTimeout(() => {
      setMessages((currentMessages) => {
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

  const handleNewChat = useCallback(() => {
    const newSession = createChatSession()
    saveChatSession(newSession)
    setSessions(loadChatSessions())
    setActiveSessionId(newSession.id)
    setMessages([])
  }, [])

  const handleSelectSession = useCallback(
    (sessionId: string) => {
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

  useEffect(() => {
    if (user && !activeSessionId && sessions.length === 0) {
      const fresh = createChatSession()
      saveChatSession(fresh)
      setSessions(loadChatSessions())
      setActiveSessionId(fresh.id)
    }
  }, [user, activeSessionId, sessions.length])

  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center animate-pulse-glow">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
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

      <div className="flex flex-col flex-1 min-w-0 transition-all duration-300">
        <Header
          isSidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
          onNewChat={handleNewChat}
          mode={mode}
          onModeChange={setMode}
          user={user}
          onLogout={logout}
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
          ) : mode === 'video-lecture' ? (
            <VideoLectureMode />
          ) : mode === 'doubt-solver' ? (
            <DoubtSolverMode />
          ) : (
            <PersonalizedMode />
          )}
        </main>
      </div>
    </div>
  )
}
