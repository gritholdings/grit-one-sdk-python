import { useState, useEffect, useRef } from 'react';
import { checkAuthentication } from '@/chat/lib/auth';
import { apiClient } from '@/chat/lib/api-client';
import type { User, Message } from '@/chat/types';
import { Chat } from '@/chat/components/chat';

interface AssistantChatProps {
  onClose?: () => void;
}

export function AssistantChat({ onClose }: AssistantChatProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentThreadId, setCurrentThreadId] = useState<string>('');
  const [initialMessages, setInitialMessages] = useState<Message[] | null>(null);

  // Authenticate user
  useEffect(() => {
    const authenticate = async () => {
      try {
        const userData = await checkAuthentication();
        if (userData) {
          setUser(userData);
        }
      } catch (error) {
        console.error('Authentication error:', error);
      } finally {
        setIsLoading(false);
      }
    };

    authenticate();
  }, []);

  // Load messages when thread ID changes
  useEffect(() => {
    async function loadMessages() {
      if (!currentThreadId) {
        setInitialMessages([]);
        return;
      }

      try {
        const response = await apiClient.post(`/agent/api/threads/`, {
          thread_id: currentThreadId,
        });
        if (response.status === 200) {
          setInitialMessages(response.data.messages || []);
        }
      } catch (error) {
        console.error('Failed to fetch thread messages:', error);
        setInitialMessages([]);
      }
    }

    if (user) {
      loadMessages();
    }
  }, [currentThreadId, user]);

  // Handle new thread creation
  const handleNewThread = (threadId: string) => {
    setCurrentThreadId(threadId);
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading assistant...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center px-4">
          <p className="text-sm text-gray-600">Authentication required</p>
        </div>
      </div>
    );
  }

  if (initialMessages === null) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading messages...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
        <h2 className="text-lg font-semibold">Assistant</h2>
      </div>

      {/* Chat Content - wrapper to override Chat's viewport-based height */}
      <div className="flex-1 overflow-hidden min-h-0">
        <style>{`
          .assistant-chat-wrapper > div {
            height: 100% !important;
          }
        `}</style>
        <div className="assistant-chat-wrapper h-full">
          <Chat
            id={currentThreadId}
            initialMessages={initialMessages}
            onNewThread={handleNewThread}
          />
        </div>
      </div>
    </div>
  );
}

export default AssistantChat;
