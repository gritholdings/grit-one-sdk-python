
// import { Message } from 'ai';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';
import type { Dispatch, SetStateAction } from 'react';

// import { Vote } from '@/db/schema';

import type { UIBlock } from './block';
// import { DocumentToolCall, DocumentToolResult } from './document';
import { SparklesIcon } from './icons';
import { Markdown } from './markdown';
// import { MessageActions } from './message-actions';
import { PreviewAttachment } from './preview-attachment';
// import { Weather } from './weather';

import type { Attachment, ChatRequestOptions, CreateMessage, Message } from '../types';

export const PreviewMessage = ({
  chatId,
  message,
  block,
  setBlock,
  // vote,
  isLoading,
}: {
  chatId: string;
  message: Message;
  block: UIBlock;
  setBlock: Dispatch<SetStateAction<UIBlock>>;
  // vote: Vote | undefined;
  isLoading: boolean;
}) => {
  return (
    <motion.div
      className="preview-message w-full mx-auto max-w-3xl px-4 group/message"
      initial={{ y: 5, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      data-role={message.role}
    >
      <div
        className={cn(
          'group-data-[role=user]/message:bg-neutral-100 group-data-[role=user]/message:text-black flex gap-4 group-data-[role=user]/message:px-4 w-full group-data-[role=user]/message:w-fit group-data-[role=user]/message:ml-auto group-data-[role=user]/message:max-w-[70%] group-data-[role=user]/message:py-3 rounded-xl'
        )}
      >

        <div className="flex flex-col gap-2 w-full">
          {message.content && (
            <div className="flex flex-col gap-4">
              {/* Check if it's a file upload message */}
              {message.role === 'user_image' ? (
                <div className="ml-auto inline-block border border-dashed border-slate-300 
          text-left rounded-md px-12 py-4">
                  <div>{message.metadata?.filename || 'File'}</div>
                  {message.metadata?.pageCount && (
                    <div className="text-xs text-gray-500 mt-1">{message.metadata.pageCount}</div>
                  )}
                </div>
              ) : message.content.startsWith('data:image') ? (
                /* Backward compatibility for old format */
                <div className="ml-auto inline-block border border-dashed border-slate-300 
          text-left rounded-md px-12 py-4">
                  File
                </div>
              ) : (
                <Markdown>{message.content as string}</Markdown>
              )}
            </div>
          )}

          {/* {message.toolInvocations && message.toolInvocations.length > 0 && (
            <div className="flex flex-col gap-4">
              {message.toolInvocations.map((toolInvocation) => {
                const { toolName, toolCallId, state, args } = toolInvocation;

                if (state === 'result') {
                  const { result } = toolInvocation;

                  return (
                    <div key={toolCallId}>
                      {toolName === 'getWeather' ? (
                        <Weather weatherAtLocation={result} />
                      ) : toolName === 'createDocument' ? (
                        <DocumentToolResult
                          type="create"
                          result={result}
                          block={block}
                          setBlock={setBlock}
                        />
                      ) : toolName === 'updateDocument' ? (
                        <DocumentToolResult
                          type="update"
                          result={result}
                          block={block}
                          setBlock={setBlock}
                        />
                      ) : toolName === 'requestSuggestions' ? (
                        <DocumentToolResult
                          type="request-suggestions"
                          result={result}
                          block={block}
                          setBlock={setBlock}
                        />
                      ) : (
                        <pre>{JSON.stringify(result, null, 2)}</pre>
                      )}
                    </div>
                  );
                } else {
                  return (
                    <div
                      key={toolCallId}
                      className={cn({
                        skeleton: ['getWeather'].includes(toolName),
                      })}
                    >
                      {toolName === 'getWeather' ? (
                        <Weather />
                      ) : toolName === 'createDocument' ? (
                        <DocumentToolCall type="create" args={args} />
                      ) : toolName === 'updateDocument' ? (
                        <DocumentToolCall type="update" args={args} />
                      ) : toolName === 'requestSuggestions' ? (
                        <DocumentToolCall
                          type="request-suggestions"
                          args={args}
                        />
                      ) : null}
                    </div>
                  );
                }
              })}
            </div>
          )} */}

          {message.experimental_attachments && (
            <div className="flex flex-row gap-2">
              {message.experimental_attachments.map((attachment) => (
                <PreviewAttachment
                  key={attachment.url}
                  attachment={attachment}
                />
              ))}
            </div>
          )}

          {/* <MessageActions
            key={`action-${message.id}`}
            chatId={chatId}
            message={message}
            vote={vote}
            isLoading={isLoading}
          /> */}
        </div>
      </div>
    </motion.div>
  );
};

export const ThinkingMessage = () => {
  const role = 'assistant';

  return (
    <motion.div
      className="thinking-message w-full mx-auto max-w-3xl px-4 group/message "
      initial={{ y: 5, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { delay: 1 } }}
      data-role={role}
    >
      <div
        className={cn(
          'flex gap-4 group-data-[role=user]/message:px-3 w-full group-data-[role=user]/message:w-fit group-data-[role=user]/message:ml-auto group-data-[role=user]/message:max-w-2xl group-data-[role=user]/message:py-2 rounded-xl',
          {
            'group-data-[role=user]/message:bg-muted': true,
          }
        )}
      >
        <div className="flex flex-col gap-2 w-full">
          <div className="flex flex-col gap-4 text-muted-foreground">
            Thinking...
          </div>
        </div>
      </div>
    </motion.div>
  );
};
