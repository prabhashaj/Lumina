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

import { Message, ChatSession, UnifiedHistoryItem } from '@/lib/types'
import {
  loadChatSessions,
  loadUnifiedHistoryItems,
  createChatSession,
  saveChatSession,
  deleteChatSession,
} from '@/lib/chatHistory'
import { deleteExamPrepSession } from '@/lib/examPrepStorage'
import { deletePersonalizedSession } from '@/lib/personalizedStorage'
import { deleteDoubtSolverSession } from '@/lib/doubtSolverStorage'
import { deleteVideoLectureSession } from '@/lib/videoLectureStorage'
import { Sparkles } from 'lucide-react'

export default function AppPage() {
  const router = useRouter()
  const { user, isLoading, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [historyItems, setHistoryItems] = useState<UnifiedHistoryItem[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [examPrepSessionId, setExamPrepSessionId] = useState<string | null>(null)
  const [personalizedSessionId, setPersonalizedSessionId] = useState<string | null>(null)
  const [videoLectureSessionId, setVideoLectureSessionId] = useState<string | null>(null)
  const [doubtSolverSessionId, setDoubtSolverSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [mode, setMode] = useState<AppMode>('chat')

  const refreshAllHistory = useCallback(() => {
    setSessions(loadChatSessions())
    setHistoryItems(loadUnifiedHistoryItems())
  }, [])

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
    setHistoryItems(loadUnifiedHistoryItems())
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
        refreshAllHistory()
        return currentMessages
      })
    }, 50)
  }, [activeSessionId, sessions, refreshAllHistory])

  const handleNewChat = useCallback(() => {
    const newSession = createChatSession()
    saveChatSession(newSession)
    refreshAllHistory()
    setActiveSessionId(newSession.id)
    setMessages([])
  }, [refreshAllHistory])

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
      refreshAllHistory()
    },
    [activeSessionId, messages, sessions, refreshAllHistory]
  )

  const handleDeleteSession = useCallback(
    (sessionId: string) => {
      deleteChatSession(sessionId)
      const updated = loadChatSessions()
      setSessions(updated)
      setHistoryItems(loadUnifiedHistoryItems())
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
          refreshAllHistory()
          setActiveSessionId(fresh.id)
          setMessages([])
        }
      }
    },
    [activeSessionId, refreshAllHistory]
  )

  const handleDeleteHistoryItem = useCallback(
    (item: UnifiedHistoryItem) => {
      if (item.mode === 'chat') {
        handleDeleteSession(item.sessionId)
        return
      }
      if (item.mode === 'exam-prep') {
        deleteExamPrepSession(item.sessionId)
        if (examPrepSessionId === item.sessionId) setExamPrepSessionId(null)
      } else if (item.mode === 'personalized') {
        deletePersonalizedSession(item.sessionId)
        if (personalizedSessionId === item.sessionId) setPersonalizedSessionId(null)
      } else if (item.mode === 'video-lecture') {
        deleteVideoLectureSession(item.sessionId)
        if (videoLectureSessionId === item.sessionId) setVideoLectureSessionId(null)
      } else if (item.mode === 'doubt-solver') {
        deleteDoubtSolverSession(item.sessionId)
        if (doubtSolverSessionId === item.sessionId) setDoubtSolverSessionId(null)
      }
      refreshAllHistory()
    },
    [
      handleDeleteSession,
      doubtSolverSessionId,
      examPrepSessionId,
      personalizedSessionId,
      videoLectureSessionId,
      refreshAllHistory,
    ]
  )

  const handleSelectHistoryItem = useCallback(
    (item: UnifiedHistoryItem) => {
      if (item.mode === 'chat') {
        setMode('chat')
        handleSelectSession(item.sessionId)
        return
      }

      setMode(item.mode)
      if (item.mode === 'exam-prep') setExamPrepSessionId(item.sessionId)
      if (item.mode === 'personalized') setPersonalizedSessionId(item.sessionId)
      if (item.mode === 'video-lecture') setVideoLectureSessionId(item.sessionId)
      if (item.mode === 'doubt-solver') setDoubtSolverSessionId(item.sessionId)
    },
    [handleSelectSession]
  )

  const handleNewModeEntry = useCallback(() => {
    if (mode === 'chat') {
      handleNewChat()
      return
    }
    if (mode === 'exam-prep') setExamPrepSessionId(null)
    if (mode === 'personalized') setPersonalizedSessionId(null)
    if (mode === 'video-lecture') setVideoLectureSessionId(null)
    if (mode === 'doubt-solver') setDoubtSolverSessionId(null)
  }, [mode, handleNewChat])

  const activeItemId =
    mode === 'chat'
      ? activeSessionId
        ? `chat:${activeSessionId}`
        : null
      : mode === 'exam-prep'
      ? examPrepSessionId
        ? `exam-prep:${examPrepSessionId}`
        : null
      : mode === 'personalized'
      ? personalizedSessionId
        ? `personalized:${personalizedSessionId}`
        : null
      : mode === 'video-lecture'
      ? videoLectureSessionId
        ? `video-lecture:${videoLectureSessionId}`
        : null
      : doubtSolverSessionId
      ? `doubt-solver:${doubtSolverSessionId}`
      : null

  useEffect(() => {
    if (user && !activeSessionId && sessions.length === 0) {
      const fresh = createChatSession()
      saveChatSession(fresh)
      refreshAllHistory()
      setActiveSessionId(fresh.id)
    }
  }, [user, activeSessionId, sessions.length, refreshAllHistory])

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
        sessions={historyItems}
        activeItemId={activeItemId}
        onSelectSession={handleSelectHistoryItem}
        onNewChat={handleNewModeEntry}
        onDeleteSession={handleDeleteHistoryItem}
      />

      <div className="flex flex-col flex-1 min-w-0 transition-all duration-300">
        <Header
          isSidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
          onNewChat={handleNewModeEntry}
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
              sessionId={activeSessionId}
            />
          ) : mode === 'exam-prep' ? (
            <ExamPrepMode
              selectedSessionId={examPrepSessionId}
              onActiveSessionChange={setExamPrepSessionId}
              onHistoryChanged={refreshAllHistory}
            />
          ) : mode === 'video-lecture' ? (
            <VideoLectureMode
              selectedSessionId={videoLectureSessionId}
              onActiveSessionChange={setVideoLectureSessionId}
              onHistoryChanged={refreshAllHistory}
            />
          ) : mode === 'doubt-solver' ? (
            <DoubtSolverMode
              selectedSessionId={doubtSolverSessionId}
              onActiveSessionChange={setDoubtSolverSessionId}
              onHistoryChanged={refreshAllHistory}
            />
          ) : (
            <PersonalizedMode
              selectedSessionId={personalizedSessionId}
              onActiveSessionChange={setPersonalizedSessionId}
              onHistoryChanged={refreshAllHistory}
            />
          )}
        </main>
      </div>
    </div>
  )
}
