'use client'

import { Search, PanelLeftOpen, PanelLeftClose, Plus, GraduationCap, MessageSquare, Sparkles } from 'lucide-react'

export type AppMode = 'chat' | 'exam-prep'

interface HeaderProps {
  isSidebarOpen: boolean
  onToggleSidebar: () => void
  onNewChat: () => void
  mode: AppMode
  onModeChange: (mode: AppMode) => void
}

export default function Header({ isSidebarOpen, onToggleSidebar, onNewChat, mode, onModeChange }: HeaderProps) {
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
          </div>

          {/* Right: New Chat */}
          {mode === 'chat' ? (
            <button
              onClick={onNewChat}
              className="flex items-center gap-1.5 px-3.5 py-[7px] rounded-xl border border-border/40 hover:border-[hsl(73,31%,45%)]/40 bg-card/30 hover:bg-[hsl(73,31%,45%)]/10 text-sm text-muted-foreground hover:text-foreground transition-all duration-200"
              title="Start a new chat"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline text-xs font-medium">New Chat</span>
            </button>
          ) : (
            <div className="w-[1px]" />
          )}
        </div>
      </div>
    </header>
  )
}
