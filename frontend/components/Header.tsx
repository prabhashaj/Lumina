'use client'

import { useState, useRef, useEffect } from 'react'
import { Search, PanelLeftOpen, PanelLeftClose, Plus, GraduationCap, MessageSquare, Sparkles, User, LogOut, ChevronDown, Presentation, Camera } from 'lucide-react'

export type AppMode = 'chat' | 'exam-prep' | 'personalized' | 'video-lecture' | 'doubt-solver'

interface UserData {
  id: string
  name: string
  email: string
}

interface HeaderProps {
  isSidebarOpen: boolean
  onToggleSidebar: () => void
  onNewChat: () => void
  mode: AppMode
  onModeChange: (mode: AppMode) => void
  user?: UserData | null
  onLogout?: () => void
}

export default function Header({ isSidebarOpen, onToggleSidebar, onNewChat, mode, onModeChange, user, onLogout }: HeaderProps) {
  const [showUserMenu, setShowUserMenu] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])
  return (
    <header className="border-b border-border/20 glass-subtle sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-2.5">
            {/* Sidebar toggle */}
            <button
              onClick={onToggleSidebar}
              className="p-2 rounded-xl hover:bg-muted/60 text-muted-foreground hover:text-foreground transition-all duration-200"
              title={isSidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            >
              {isSidebarOpen ? (
                <PanelLeftClose className="w-[18px] h-[18px]" />
              ) : (
                <PanelLeftOpen className="w-[18px] h-[18px]" />
              )}
            </button>

            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-lg shadow-[hsl(73,31%,45%)]/20">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-[15px] font-bold tracking-tight text-gradient">
                Lumina
              </h1>
            </div>
          </div>

          {/* Center: Mode toggle */}
          <div className="flex items-center bg-muted/40 rounded-xl p-[3px] border border-border/30">
            <button
              onClick={() => onModeChange('chat')}
              className={`flex items-center gap-1.5 px-4 py-[7px] rounded-[10px] text-xs font-semibold transition-all duration-200 ${
                mode === 'chat'
                  ? 'bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white shadow-md shadow-[hsl(73,31%,45%)]/25'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Research</span>
            </button>
            <button
              onClick={() => onModeChange('exam-prep')}
              className={`flex items-center gap-1.5 px-4 py-[7px] rounded-[10px] text-xs font-semibold transition-all duration-200 ${
                mode === 'exam-prep'
                  ? 'bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white shadow-md shadow-[hsl(73,31%,45%)]/25'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <GraduationCap className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Exam Prep</span>
            </button>
            <button
              onClick={() => onModeChange('personalized')}
              className={`flex items-center gap-1.5 px-4 py-[7px] rounded-[10px] text-xs font-semibold transition-all duration-200 ${
                mode === 'personalized'
                  ? 'bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white shadow-md shadow-[hsl(73,31%,45%)]/25'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <User className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Personalized</span>
            </button>
            <button
              onClick={() => onModeChange('video-lecture')}
              className={`flex items-center gap-1.5 px-4 py-[7px] rounded-[10px] text-xs font-semibold transition-all duration-200 ${
                mode === 'video-lecture'
                  ? 'bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white shadow-md shadow-[hsl(73,31%,45%)]/25'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Presentation className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Video Lecture</span>
            </button>
            <button
              onClick={() => onModeChange('doubt-solver')}
              className={`flex items-center gap-1.5 px-4 py-[7px] rounded-[10px] text-xs font-semibold transition-all duration-200 ${
                mode === 'doubt-solver'
                  ? 'bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,50%)] text-white shadow-md shadow-[hsl(73,31%,45%)]/25'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Camera className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Doubt Solver</span>
            </button>
          </div>

          {/* Right: New Chat + User Menu */}
          <div className="flex items-center gap-2">
            {mode === 'chat' && (
              <button
                onClick={onNewChat}
                className="flex items-center gap-1.5 px-3.5 py-[7px] rounded-xl border border-border/40 hover:border-[hsl(73,31%,45%)]/40 bg-card/30 hover:bg-[hsl(73,31%,45%)]/10 text-sm text-muted-foreground hover:text-foreground transition-all duration-200"
                title="Start a new chat"
              >
                <Plus className="w-4 h-4" />
                <span className="hidden sm:inline text-xs font-medium">New Chat</span>
              </button>
            )}

            {/* User Menu */}
            {user && onLogout && (
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-2 px-2.5 py-[6px] rounded-xl hover:bg-muted/60 transition-all duration-200"
                >
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center text-white text-xs font-bold shadow-sm">
                    {user.name.charAt(0).toUpperCase()}
                  </div>
                  <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform duration-200 ${showUserMenu ? 'rotate-180' : ''}`} />
                </button>

                {showUserMenu && (
                  <div className="absolute right-0 top-full mt-2 w-56 bg-card border border-border/30 rounded-2xl shadow-2xl p-2 animate-fadeInScale z-50">
                    <div className="px-3 py-2.5 border-b border-border/20 mb-1">
                      <p className="text-sm font-semibold truncate">{user.name}</p>
                      <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                    </div>
                    <button
                      onClick={() => {
                        setShowUserMenu(false)
                        onLogout()
                      }}
                      className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-xl text-sm text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all duration-200"
                    >
                      <LogOut className="w-4 h-4" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
