'use client'

import { Message } from '@/lib/types'
import MessageBubble from './MessageBubble'

interface MessageListProps {
  messages: Message[]
  onFollowUpClick?: (text: string) => void
}

export default function MessageList({ messages, onFollowUpClick }: MessageListProps) {
  return (
    <div className="space-y-6">
      {messages.map((message, idx) => (
        <MessageBubble
          key={message.id}
          message={message}
          onFollowUpClick={onFollowUpClick}
          isLast={idx === messages.length - 1}
        />
      ))}
    </div>
  )
}
