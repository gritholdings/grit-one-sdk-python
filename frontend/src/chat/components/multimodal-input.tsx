
import type { Attachment, ChatRequestOptions, CreateMessage, Message } from '../types';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';
import { useRef, useEffect, useState, useCallback } from 'react';
import type { Dispatch, SetStateAction, ChangeEvent } from 'react';
import { toast } from 'sonner';
import { useLocalStorage, useWindowSize } from 'usehooks-ts';

// import { sanitizeUIMessages } from '@/lib/utils';

import { ArrowUpIcon, PaperclipIcon, StopIcon } from './icons';
import { PreviewAttachment } from './preview-attachment';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

import { apiClient } from '../lib/api-client';
import { set } from 'date-fns';

import { ChatConfig } from '../lib/config';


export function MultimodalInput({
  chatId,
  input,
  setInput,
  isLoading,
  isPendingMessage,
  stop,
  attachments,
  setAttachments,
  messages,
  setMessages,
  append,
  handleSubmit,
  className,
  suggestedMessages,
  ensureThreadExists,
  onFileUploadStart,
  onFileUploadEnd,
  disableAttachmentUiButton = false,
}: {
  chatId: string;
  input: string;
  setInput: (value: string) => void;
  isLoading: boolean;
  isPendingMessage: boolean;
  stop: () => void;
  attachments: Array<Attachment>;
  setAttachments: Dispatch<SetStateAction<Array<Attachment>>>;
  messages: Array<Message>;
  setMessages: Dispatch<SetStateAction<Array<Message>>>;
  append: (
    message: Message | CreateMessage,
    chatRequestOptions?: ChatRequestOptions
  ) => Promise<string | null | undefined>;
  handleSubmit: (
    event?: {
      preventDefault?: () => void;
    },
    chatRequestOptions?: ChatRequestOptions
  ) => void;
  className?: string;
  suggestedMessages: Array<string>;
  ensureThreadExists: () => Promise<string>;
  onFileUploadStart?: () => void;
  onFileUploadEnd?: () => void;
  disableAttachmentUiButton?: boolean;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { width } = useWindowSize();

  useEffect(() => {
    if (textareaRef.current) {
      adjustHeight();
    }
  }, []);

  const adjustHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight + 2}px`;
    }
  };

  const [localStorageInput, setLocalStorageInput] = useLocalStorage(
    'input',
    ''
  );

  useEffect(() => {
    if (textareaRef.current) {
      const domValue = textareaRef.current.value;
      // Prefer DOM value over localStorage to handle hydration
      const finalValue = domValue || localStorageInput || '';
      setInput(finalValue);
      adjustHeight();
    }
    // Only run once after hydration
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setLocalStorageInput(input);
  }, [input, setLocalStorageInput]);

  const handleInput = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(event.target.value);
    adjustHeight();
  };

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadQueue, setUploadQueue] = useState<Array<string>>([]);

  const submitForm = useCallback(() => {
    // window.history.replaceState({}, '', `/chat/${chatId}`);
    handleSubmit(undefined, {
      experimental_attachments: attachments,
    });

    // Keep <PreviewAttachment> showing at all times for now in the
    // same thread because backend doesn't return the attachment details yet.
    // setAttachments([]);
    setLocalStorageInput('');

    if (width && width > 768) {
      textareaRef.current?.focus();
    }
  }, [
    attachments,
    handleSubmit,
    setAttachments,
    setLocalStorageInput,
    width,
    chatId || '',
  ]);

  const fetchThreadMessages = async (threadId: string) => {
    try {
      const response = await apiClient.post(`/agent/api/threads/`, {
        thread_id: threadId,
      });
      if (response.status === 200 && response.data.messages) {
        setMessages(response.data.messages);
      }
    } catch (error) {
      console.error('Failed to fetch thread messages:', error);
    }
  };

  const uploadFile = async (file: File) => {
    let currentThreadId = await ensureThreadExists();
    const formData = new FormData();
    formData.append('file', file);
    formData.append('thread_id', currentThreadId);

    try {
      const response = await apiClient.post(`/agent/api/files/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const url = '';

      return {
        url,
        name: file.name,
        contentType: '',
        type: 'file',
        content: file.name
      };
    } catch (error) {
      console.error('Error uploading file:', error);
      toast.error('Failed to upload file, please try again!');
    }
  };

  const handleFileChange = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(event.target.files || []);

      // Filter out files exceeding the size limit
      const validFiles = files.filter((file) => {
        const fileInMB = file.size / (1024 * 1024);
        if (fileInMB > ChatConfig.MAX_UPLOAD_SIZE_MB) {
          alert(
            `File ${file.name} exceeds the ${ChatConfig.MAX_UPLOAD_SIZE_MB}MB size limit.`
          );
          return false;
        }
        return true;
      });

      // if a file is invalid, cancel the upload
      if (validFiles.length !== files.length) {
        // Reset the file input
        setUploadQueue([]);
        return;
      }

      setUploadQueue(files.map((file) => file.name));
      onFileUploadStart?.();

      try {
        const uploadPromises = files.map((file) => uploadFile(file));
        const uploadedAttachments = await Promise.all(uploadPromises);
        const successfullyUploadedAttachments = uploadedAttachments.filter(
          (attachment) => attachment !== undefined
        );
        setAttachments((currentAttachments) => [
          ...currentAttachments,
          ...successfullyUploadedAttachments,
        ]);
        
        // Refresh messages to show the uploaded images
        const currentThreadId = await ensureThreadExists();
        await fetchThreadMessages(currentThreadId);
      } catch (error) {
        console.error('Error uploading files!', error);
      } finally {
        setUploadQueue([]);
        onFileUploadEnd?.();
      }
    },
    [setAttachments, ensureThreadExists, fetchThreadMessages, onFileUploadStart, onFileUploadEnd]
  );

  return (
    <div className="multimodal-input relative w-full flex flex-col gap-4">
      {messages.length === 0 &&
        !isPendingMessage &&
        attachments.length === 0 &&
        uploadQueue.length === 0 && (
          <div className="grid sm:grid-cols-2 gap-2 w-full">
            {suggestedMessages.map((suggestedMessage, index) => (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                transition={{ delay: 0.05 * index }}
                key={index}
                className={index > 1 ? 'hidden sm:block' : 'block'}
              >
                <Button
                  variant="ghost"
                  onClick={async (event) => {
                    event.preventDefault();
                    // window.history.replaceState({}, '', `/chat/${chatId}`);
                    append({
                      role: 'user',
                      content: suggestedMessage[1],
                    });
                  }}
                  className="text-left border rounded-xl px-4 py-3.5 text-sm flex-1 gap-1
                    sm:flex-col w-full h-auto justify-start items-start overflow-hidden">
                  <span className="font-medium">{suggestedMessage[0]}</span>
                  {/* <span className="text-muted-foreground">
                    {suggestedAction.label}
                  </span> */}
                </Button>
              </motion.div>
            ))}
          </div>
        )}

      <input
        type="file"
        className="file-upload-input-hidden fixed -top-4 -left-4 size-0.5 opacity-0 pointer-events-none"
        ref={fileInputRef}
        multiple
        onChange={handleFileChange}
        tabIndex={-1}
      />

      {/* Do not use this since the browser re-render from ChatHeader */}
      {/* {(attachments.length > 0 || uploadQueue.length > 0) && (
        <div className="flex flex-row gap-2 overflow-x-scroll items-end">
          {attachments.map((attachment, index) => (
            <PreviewAttachment key={`${attachment.name}-${index}`} attachment={attachment} />
          ))}

          {uploadQueue.map((filename, index) => (
            <PreviewAttachment
              key={`${filename}-${index}`}
              attachment={{
                url: '',
                name: filename,
                contentType: '',
              }}
              isUploading={true}
            />
          ))}
        </div>
      )} */}

      <Textarea
        ref={textareaRef}
        placeholder="Send a message..."
        value={input}
        onChange={handleInput}
        className={cn(
          'min-h-[24px] max-h-[calc(75dvh)] overflow-hidden resize-none rounded-xl text-base bg-muted',
          className
        )}
        rows={3}
        autoFocus
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();

            if (isLoading) {
              toast.error('Please wait for the model to finish its response!');
            } else {
              submitForm();
            }
          }
        }}
      />

      {isLoading ? (
        <Button
          className="bg-black rounded-full p-1.5 h-fit absolute bottom-2 right-2 m-0.5 border"
          onClick={(event) => {
            event.preventDefault();
            stop();
            // setMessages((messages) => sanitizeUIMessages(messages));
            setMessages(messages);
          }}
        >
          <StopIcon size={14} />
        </Button>
      ) : (
        <Button
          className="send-button bg-black rounded-full p-1.5 h-fit absolute bottom-2 right-2 m-0.5 border"
          onClick={(event) => {
            event.preventDefault();
            submitForm();
          }}
          disabled={input.length === 0 || uploadQueue.length > 0}
        >
          <ArrowUpIcon size={14} />
        </Button>
      )}

      {!disableAttachmentUiButton && (
        <Button
          className="file-upload-button rounded-full p-1.5 h-fit absolute bottom-2 right-14 m-0.5"
          onClick={(event) => {
            event.preventDefault();
            fileInputRef.current?.click();
          }}
          variant="outline"
          disabled={isLoading}
        >
          <PaperclipIcon size={14} />
        </Button>
      )}
    </div>
  );
}
