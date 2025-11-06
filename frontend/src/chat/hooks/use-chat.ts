import { useState, useEffect, useCallback } from 'react';
import type { Message, CreateMessage } from '../types';
import { baseUrl, getCookie } from '../lib/api-client';

export function useChat({
  initialMessages = [],
  body = {},
  onFinish,
  modelId,
  ensureThreadExists
}: {
  initialMessages?: Message[];
  body?: Record<string, any>;
  onFinish?: () => void;
  modelId: string;
  ensureThreadExists: () => Promise<string>;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPendingMessage, setIsPendingMessage] = useState(false);
  const [streamingData, setStreamingData] = useState<any>(null);

  useEffect(() => {
    setMessages(initialMessages);
  }, [initialMessages]);

  const append = useCallback(async (message: CreateMessage) => {
    try {
      setIsPendingMessage(true);
      setIsLoading(true);
      let currentThreadId = await ensureThreadExists();

      // Add user message
      setMessages(prevMessages => [...prevMessages, {
        ...message,
        id: Date.now().toString(),
        role: message.role || 'user'
      }]);
      const response = await fetch(baseUrl + "/agent/api/threads/runs", {
        method: "POST",
        credentials: "include",
        headers: new Headers({
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken") || ""
        }),
        body: JSON.stringify({
          message: message.content,
          thread_id: currentThreadId,
          content: message.content,
          chat_id: body.id,
          model_id: modelId,
          attachments: message.attachments
        })
      });
      // Format assistant message
      const newAssistantMessageId = Date.now().toString();
      const assistantMessage: Message = {
        id: newAssistantMessageId,
        role: 'assistant',
        content: ''
      };

      // Set an initial empty assistant response
      setMessages(prevMessages => [...prevMessages, assistantMessage]);

      // Read the streaming response using a ReadableStream reader
      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");

      let done = false;

      while (!done) {
        const result = await reader?.read();
        const { value, done: readerDone } = result || {};
        done = readerDone ?? true;
        if (value) {
          // Decode the current chunk
          const chunkValue = decoder.decode(value, { stream: true });
          // Append it to the existing text
          setMessages(prevMessages =>
            prevMessages.map(msg =>
              msg.id === newAssistantMessageId
                ? { ...msg, content: msg.content + chunkValue }
                : msg
            )
          );
        }
      }

      onFinish?.();
      return assistantMessage.id;

    } catch (error) {
      console.error('Chat API error:', error);
    } finally {
      setIsLoading(false);
      setIsPendingMessage(false);
    }
  }, [body.id, modelId, ensureThreadExists, onFinish]);

  const handleSubmit = useCallback(
    (event?: { preventDefault?: () => void }) => {
      event?.preventDefault?.();
      if (!input.trim() || isLoading) return;

      const userMessage = {
        id: Date.now().toString(),
        role: 'user' as const,
        content: input
      };

      setInput('');
      return append(userMessage);
    },
    [input, isLoading, append, setInput]
  );

  const stop = useCallback(() => {
    // Implement cancel logic here if needed
    setIsLoading(false);
  }, []);

  return {
    messages,
    setMessages,
    input,
    setInput,
    handleSubmit,
    append,
    isLoading,
    isPendingMessage,
    stop,
    data: streamingData
  };
}
