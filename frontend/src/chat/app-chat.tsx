import { useState, useEffect, useRef } from 'react';
import { checkAuthentication } from './lib/auth';
import { apiClient } from './lib/api-client';
import type { User, Message } from './types';
import AppLayout from '@/components/app-layout';
import { AppSidebar } from './components/app-sidebar';
import { Chat } from './components/chat';
import { useDebugLoading } from '@/hooks/use-debug-loading';

interface AppChatProps {
  threadId?: string;
}

export default function AppChat({ threadId: initialThreadId }: AppChatProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useDebugLoading(true);
  const [currentThreadId, setCurrentThreadId] = useState<string>(initialThreadId || '');
  const [initialMessages, setInitialMessages] = useState<Message[] | null>(null);
  const skipNextReloadRef = useRef(false);

  // Handle browser back/forward navigation
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      const match = path.match(/\/agent\/chat\/c\/([^/]+)/);
      if (match) {
        setCurrentThreadId(match[1]);
      } else {
        setCurrentThreadId('');
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

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

      // Check if we should skip this reload (for new thread creation during message send)
      // This prevents wiping out optimistically added messages when creating a new thread
      if (skipNextReloadRef.current) {
        skipNextReloadRef.current = false; // Reset for next navigation
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

  // Navigate to a new thread (called from Chat component or sidebar)
  const navigateToThread = (threadId: string, skipReload = false) => {
    const newPath = `/agent/chat/c/${threadId}`;
    window.history.pushState({}, '', newPath);

    if (skipReload) {
      // For new thread creation during message send, don't reload messages
      // The messages are already in the Chat component's local state
      skipNextReloadRef.current = true;
    } else {
      // For user navigation, trigger reload
      setInitialMessages(null);
    }

    setCurrentThreadId(threadId);
  };

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading chat...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Authentication required</p>
        </div>
      </div>
    );
  }

  if (initialMessages === null) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading messages...</p>
        </div>
      </div>
    );
  }

  return (
    <AppLayout
      title="Chat"
      customSidebar={
        <AppSidebar
          user={user}
          currentThreadId={currentThreadId}
          onNavigate={navigateToThread}
        />
      }
      contentClassName="flex flex-1 flex-col"
    >
      <Chat
        id={currentThreadId}
        initialMessages={initialMessages}
        onNewThread={(threadId) => navigateToThread(threadId, true)}
      />
    </AppLayout>
  );
}