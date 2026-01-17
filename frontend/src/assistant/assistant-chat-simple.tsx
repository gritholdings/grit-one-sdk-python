import { useState, useEffect, useRef, useCallback } from 'react';
import { checkAuthentication } from '@/chat/lib/auth';
import { apiClient } from '@/chat/lib/api-client';

const THREAD_STORAGE_KEY = 'assistant_thread_id';
import type { User, Message, Attachment } from '@/chat/types';
import { useChat } from '@/chat/hooks/use-chat';
import { AnimatePresence, motion } from 'framer-motion';
import { SquarePen } from 'lucide-react';
import { PreviewMessage, ThinkingMessage } from '@/chat/components/message';
import { useScrollToBottom } from '@/chat/components/use-scroll-to-bottom';
import { MultimodalInput } from '@/chat/components/multimodal-input';
import { Overview } from '@/chat/components/overview';
import { Block } from '@/chat/components/block';
import type { UIBlock } from '@/chat/components/block';
import type { ModelOptions } from '@/chat/components/chat';
import { useWindowSize } from 'usehooks-ts';

// Type for summarization context passed from AssistantModal
interface SummarizeContext {
  context: Record<string, unknown>;
  modelName: string;
  recordName: string;
}

interface AssistantChatSimpleProps {
  onClose?: () => void;
  summarizeContext?: SummarizeContext | null;
  onSummarizeContextConsumed?: () => void;
}

export function AssistantChatSimple({ onClose, summarizeContext, onSummarizeContextConsumed }: AssistantChatSimpleProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // Initialize thread ID from sessionStorage to persist across page navigations
  const [currentThreadId, setCurrentThreadId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem(THREAD_STORAGE_KEY) || '';
    }
    return '';
  });
  const threadIdRef = useRef<string>(currentThreadId);
  const [attachments, setAttachments] = useState<Array<Attachment>>([]);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [selectedModelOptions, setSelectedModelOptions] = useState<ModelOptions>({
    modelId: '',
    suggestedMessages: [],
    overviewHtml: '',
  });

  const { width: windowWidth = 1920, height: windowHeight = 1080 } = useWindowSize();

  const [block, setBlock] = useState<UIBlock>({
    documentId: 'init',
    content: '',
    title: '',
    status: 'idle',
    isVisible: false,
    boundingBox: {
      top: windowHeight / 4,
      left: windowWidth / 4,
      width: 250,
      height: 50,
    },
  });

  const [messagesContainerRef, messagesEndRef] = useScrollToBottom<HTMLDivElement>();

  // Update threadIdRef and persist to sessionStorage whenever currentThreadId changes
  useEffect(() => {
    threadIdRef.current = currentThreadId;
    if (currentThreadId) {
      sessionStorage.setItem(THREAD_STORAGE_KEY, currentThreadId);
    }
  }, [currentThreadId]);

  const createThread = async (): Promise<string> => {
    try {
      const response = await apiClient.post('/agent/api/threads/create');
      if (response.status !== 201) {
        throw new Error('Failed to create thread');
      }
      return response.data.thread_id;
    } catch (error) {
      console.error('Error creating thread:', error);
      throw new Error('Failed to create thread');
    }
  };

  const ensureThreadExists = async () => {
    if (!threadIdRef.current) {
      const newThreadId = await createThread();
      threadIdRef.current = newThreadId;
      setCurrentThreadId(newThreadId);
    }
    return threadIdRef.current;
  };

  const fetchThreadMessages = async (threadId: string): Promise<Message[]> => {
    try {
      const response = await apiClient.post('/agent/api/threads/', { thread_id: threadId });
      if (response.status === 200 && response.data.messages) {
        // Transform backend messages to frontend Message format
        return response.data.messages.map((msg: { role: string; content: string; metadata?: Record<string, unknown> }, index: number) => ({
          id: `restored-${index}-${Date.now()}`,
          role: msg.role,
          content: msg.content,
          metadata: msg.metadata,
        }));
      }
      return [];
    } catch (error) {
      console.error('Error fetching thread messages:', error);
      // If thread not found, clear the stored thread ID
      sessionStorage.removeItem(THREAD_STORAGE_KEY);
      threadIdRef.current = '';
      setCurrentThreadId('');
      return [];
    }
  };

  const {
    messages,
    setMessages,
    handleSubmit,
    input,
    setInput,
    append,
    isLoading: isChatLoading,
    isPendingMessage,
    stop,
  } = useChat({
    modelId: selectedModelOptions.modelId,
    initialMessages: [],
    onFinish: () => {
      // Could mutate history here if needed
    },
    ensureThreadExists
  });

  const startNewConversation = useCallback(() => {
    // Clear thread from storage and state
    sessionStorage.removeItem(THREAD_STORAGE_KEY);
    threadIdRef.current = '';
    setCurrentThreadId('');
    setMessages([]);
  }, [setMessages]);

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

  // Fetch default model config (no model dropdown in Assistant mode)
  useEffect(() => {
    const fetchDefaultConfig = async () => {
      try {
        const response = await apiClient.get('/agent/api/default-config');
        if (response.status === 200 && response.data.model) {
          setSelectedModelOptions((prev) => ({
            ...prev,
            modelId: response.data.model,
          }));
        }
      } catch (error) {
        console.error('Error fetching default config:', error);
      }
    };

    fetchDefaultConfig();
  }, []);

  // Load existing thread messages when component mounts with a stored thread ID
  useEffect(() => {
    const loadExistingThread = async () => {
      // Skip loading if a summarization request is pending - let the summarize effect handle thread state
      if (summarizeContext) return;

      // Only load if user is authenticated and we have a stored thread ID
      if (user && currentThreadId && messages.length === 0) {
        const restoredMessages = await fetchThreadMessages(currentThreadId);
        if (restoredMessages.length > 0) {
          setMessages(restoredMessages);
        }
      }
    };

    loadExistingThread();
  }, [user, currentThreadId, setMessages, summarizeContext]); // eslint-disable-line react-hooks/exhaustive-deps

  // Track summarization state: null = idle, object = pending submission
  const [pendingSummarization, setPendingSummarization] = useState<{
    prompt: string;
    context: SummarizeContext;
  } | null>(null);

  // Track if we've already processed the current summarization context
  const summarizeProcessedRef = useRef(false);

  // Phase 1: When summarize context arrives, prepare the prompt and clear the thread
  useEffect(() => {
    // Skip if no context, not ready, or already processed
    if (!summarizeContext || !user || !selectedModelOptions.modelId || summarizeProcessedRef.current) return;

    // Mark as processed immediately to prevent duplicate submissions
    summarizeProcessedRef.current = true;

    // Start a fresh conversation for each summarization request
    // This ensures each record gets its own dedicated thread
    sessionStorage.removeItem(THREAD_STORAGE_KEY);
    threadIdRef.current = '';
    setCurrentThreadId('');
    setMessages([]);

    // Format the record context into a readable summary request
    const { context, modelName, recordName } = summarizeContext;

    // Build a structured prompt with the record data
    const contextLines = Object.entries(context)
      .filter(([_, value]) => value !== null && value !== undefined && value !== '')
      .map(([key, value]) => {
        // Format key from snake_case to readable format
        const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        // Handle object values (like foreign keys)
        const formattedValue = typeof value === 'object' && value !== null
          ? ('name' in value ? value.name : JSON.stringify(value))
          : String(value);
        return `- ${formattedKey}: ${formattedValue}`;
      })
      .join('\n');

    const prompt = `Please provide a concise summary of this ${modelName || 'record'}${recordName ? ` "${recordName}"` : ''}:\n\n${contextLines}`;

    // Store the pending summarization - will be submitted after messages are cleared
    setPendingSummarization({ prompt, context: summarizeContext });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summarizeContext, user, selectedModelOptions.modelId]);

  // Phase 2: Submit the summarization after messages have been cleared
  useEffect(() => {
    // Only submit when we have a pending summarization and messages are cleared
    if (!pendingSummarization || messages.length > 0) return;

    const submitSummarization = async () => {
      const { prompt } = pendingSummarization;

      // Use append to send the message programmatically
      await append({
        role: 'user',
        content: prompt,
      });

      // Clear the pending state and context after submitting
      setPendingSummarization(null);
      onSummarizeContextConsumed?.();
    };

    submitSummarization();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingSummarization, messages.length]);

  // Reset the processed flag when context changes to a new value or is cleared
  useEffect(() => {
    if (!summarizeContext) {
      summarizeProcessedRef.current = false;
    }
  }, [summarizeContext]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading assistant...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex h-full items-center justify-center bg-white">
        <div className="text-center px-4">
          <p className="text-sm text-gray-600">Authentication required</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col h-full bg-white">
        {/* Header with New Conversation button (no model dropdown in Assistant mode) */}
        <div className="relative flex items-center justify-between px-4 py-3 border-b shrink-0">
          <h2 className="text-lg font-semibold">Assistant</h2>
          <div className="flex items-center gap-2 ml-auto mr-8">
            <button
              onClick={startNewConversation}
              className="p-1.5 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-300"
              aria-label="Start new conversation"
              title="New conversation"
            >
              <SquarePen className="h-5 w-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Chat Messages */}
        <div
          ref={messagesContainerRef}
          className="flex flex-col min-w-0 gap-6 flex-1 overflow-y-scroll pt-4 px-4"
        >
          {messages.length === 0 && !isPendingMessage && (
            <Overview overviewHtml={selectedModelOptions.overviewHtml} />
          )}

          {messages.map((message, index) => {
            // Skip if this is a grouped user_image (not the first one in a sequence)
            if (message.role === 'user_image' && index > 0 && messages[index - 1]?.role === 'user_image') {
              return null;
            }

            // Check if this is the start of a user_image group
            if (message.role === 'user_image') {
              const imageGroup: Message[] = [message];
              let nextIndex = index + 1;

              // Collect consecutive user_image messages
              while (nextIndex < messages.length && messages[nextIndex]?.role === 'user_image') {
                imageGroup.push(messages[nextIndex]);
                nextIndex++;
              }

              // If there's more than one image, create enhanced message with metadata
              if (imageGroup.length > 1) {
                const totalPages = imageGroup.length;
                const enhancedMessage = {
                  ...message,
                  metadata: {
                    ...message.metadata,
                    totalPages,
                    filename: message.metadata?.filename || 'File',
                    pageCount: `${totalPages} page${totalPages > 1 ? 's' : ''}`
                  }
                };
                return (
                  <PreviewMessage
                    key={message.id}
                    chatId={currentThreadId}
                    message={enhancedMessage}
                    block={block}
                    setBlock={setBlock}
                    isLoading={false}
                  />
                );
              }
            }

            // Regular message rendering
            return (
              <PreviewMessage
                key={message.id}
                chatId={currentThreadId}
                message={message}
                block={block}
                setBlock={setBlock}
                isLoading={isChatLoading && messages.length - 1 === index}
              />
            );
          })}

          {isChatLoading &&
            messages.length > 0 &&
            messages[messages.length - 1].role === 'user' && (
              <ThinkingMessage />
            )}

          {isUploadingFile && (
            <motion.div
              className="w-full mx-auto max-w-3xl"
              initial={{ y: 5, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
            >
              <div className="flex justify-end">
                <div className="inline-block border border-dashed border-slate-300 text-center rounded-md px-12 py-4">
                  <div role="status">
                    <svg aria-hidden="true" className="inline w-8 h-8 text-gray-200 animate-spin dark:text-gray-600 fill-gray-600 dark:fill-gray-300" viewBox="0 0 100 101" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="currentColor"/>
                        <path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="currentFill"/>
                    </svg>
                    <span className="sr-only">Loading...</span>
                </div>
                </div>
              </div>
            </motion.div>
          )}

          <div
            ref={messagesEndRef}
            className="shrink-0 min-w-[24px] min-h-[24px]"
          />
        </div>

        {/* Input Form */}
        <form className="flex mx-auto px-4 bg-background pb-4 md:pb-6 gap-2 w-full">
          <MultimodalInput
            chatId={currentThreadId}
            input={input}
            setInput={setInput}
            handleSubmit={handleSubmit}
            isLoading={isChatLoading}
            isPendingMessage={isPendingMessage}
            stop={stop}
            attachments={attachments}
            setAttachments={setAttachments}
            messages={messages}
            setMessages={setMessages}
            append={append}
            suggestedMessages={selectedModelOptions.suggestedMessages}
            ensureThreadExists={ensureThreadExists}
            onFileUploadStart={() => setIsUploadingFile(true)}
            onFileUploadEnd={() => setIsUploadingFile(false)}
          />
        </form>
      </div>

      <AnimatePresence>
        {block && block.isVisible && (
          <Block
            chatId={currentThreadId}
            input={input}
            setInput={setInput}
            handleSubmit={handleSubmit}
            isLoading={isChatLoading}
            isPendingMessage={isPendingMessage}
            stop={stop}
            attachments={attachments}
            setAttachments={setAttachments}
            append={append}
            block={block}
            setBlock={setBlock}
            messages={messages}
            setMessages={setMessages}
            suggestedMessages={selectedModelOptions.suggestedMessages}
            ensureThreadExists={ensureThreadExists}
          />
        )}
      </AnimatePresence>
    </>
  );
}

export default AssistantChatSimple;
