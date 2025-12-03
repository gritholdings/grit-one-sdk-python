
import type { Attachment, Message } from '../types';
import { useChat } from '../hooks/use-chat';
import { AnimatePresence, motion } from 'framer-motion';
import { useState, useRef, useEffect } from 'react';
import { useWindowSize } from 'usehooks-ts';

import { ChatHeader } from './chat-header';
import { PreviewMessage, ThinkingMessage } from './message';
import { useScrollToBottom } from './use-scroll-to-bottom';

import { Block } from './block';
import type { UIBlock } from './block';
// import { BlockStreamHandler } from './block-stream-handler';
import { MultimodalInput } from './multimodal-input';
import { Overview } from './overview';

import { apiClient } from '../lib/api-client';

export interface ModelOptions {
  modelId: string;
  suggestedMessages: Array<string>;
  overviewHtml: string;
}

export function Chat({
  id,
  initialMessages,
  onNewThread,
  disableAttachmentUiButton = false,
}: {
  id: string;
  initialMessages: Array<Message>;
  onNewThread?: (threadId: string) => void;
  disableAttachmentUiButton?: boolean;
}) {
  // Initialize threadIdRef with the passed-in id prop
  const threadIdRef = useRef<string>(id);

  // Update threadIdRef whenever the id prop changes
  useEffect(() => {
    threadIdRef.current = id;
  }, [id]);

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
    // If no threadId is available, create one
    if (!threadIdRef.current) {
      const newThreadId = await createThread();
      threadIdRef.current = newThreadId;
      // Notify parent component about the new thread
      onNewThread?.(newThreadId);
    }
    return threadIdRef.current;
  };

  const { width: windowWidth = 1920, height: windowHeight = 1080 } =
    useWindowSize();

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

  const [messagesContainerRef, messagesEndRef] =
    useScrollToBottom<HTMLDivElement>();

  const [attachments, setAttachments] = useState<Array<Attachment>>([]);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [selectedModelOptions, setSelectedModelOptions] = useState<ModelOptions>({
    modelId: '',
    suggestedMessages: [],
    overviewHtml: '',
  });

  const {
    messages,
    setMessages,
    handleSubmit,
    input,
    setInput,
    append,
    isLoading,
    isPendingMessage,
    stop,
  } = useChat({
    modelId: selectedModelOptions.modelId,
    initialMessages,
    onFinish: () => {
      // mutate('/api/history');
    },
    ensureThreadExists
  });

  return (
    <>
      <div className="flex flex-col min-w-0 h-[calc(100vh-57px)] bg-background w-full">
        <ChatHeader
          setSelectedModelOptions={setSelectedModelOptions}
          messagesLength={messages.length}
          threadId={threadIdRef.current}
        />
        <div
          ref={messagesContainerRef}
          className="flex flex-col min-w-0 gap-6 flex-1 overflow-y-scroll pt-4"
        >
          {messages.length === 0 && !isPendingMessage &&
            <Overview
              overviewHtml={selectedModelOptions.overviewHtml}
            />
          }

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
                    chatId={id}
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
                chatId={id}
                message={message}
                block={block}
                setBlock={setBlock}
                isLoading={isLoading && messages.length - 1 === index}
              />
            );
          })}

          {isLoading &&
            messages.length > 0 &&
            messages[messages.length - 1].role === 'user' && (
              <ThinkingMessage />
            )}

          {isUploadingFile && (
            <motion.div
              className="w-full mx-auto max-w-3xl px-4"
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
        <form className="flex mx-auto px-4 bg-background pb-4 md:pb-6 gap-2 w-full md:max-w-3xl">
          <MultimodalInput
            chatId={id}
            input={input}
            setInput={setInput}
            handleSubmit={handleSubmit}
            isLoading={isLoading}
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
            disableAttachmentUiButton={disableAttachmentUiButton}
          />
        </form>
      </div>

      <AnimatePresence>
        {block && block.isVisible && (
          <Block
            chatId={id}
            input={input}
            setInput={setInput}
            handleSubmit={handleSubmit}
            isLoading={isLoading}
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
            disableAttachmentUiButton={disableAttachmentUiButton}
          />
        )}
      </AnimatePresence>
    </>
  );
}
