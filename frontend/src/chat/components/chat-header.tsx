
import type { Dispatch, SetStateAction } from 'react';
import { useWindowSize } from 'usehooks-ts';

import { ModelSelector } from './model-selector';
import { SidebarToggle } from './sidebar-toggle';
import { Button } from '@/components/ui/button';
import { BetterTooltip } from '@/components/ui/tooltip';

import { PlusIcon, VercelIcon } from './icons';
import { useSidebar } from '@/components/ui/sidebar';
import type { ModelOptions } from './chat';

export function ChatHeader({
    setSelectedModelOptions,
    messagesLength,
    threadId
  }: {
    setSelectedModelOptions: Dispatch<SetStateAction<ModelOptions>>;
    messagesLength: number;
    threadId: string | null;
  }) {
  const { open } = useSidebar();

  const { width: windowWidth } = useWindowSize();

  return (
    <header className="flex sticky top-0 bg-background py-1.5 items-center px-2 md:px-2 gap-2">
      <SidebarToggle />
      {(!open || windowWidth < 768) && (
        <BetterTooltip content="New Chat">
          <Button
            variant="outline"
            className="order-2 md:order-1 md:px-2 px-2 md:h-fit ml-auto md:ml-0"
            onClick={() => {
              window.location.href = '/agent/chat/';
            }}
          >
            <PlusIcon />
            <span className="md:sr-only">New Chat</span>
          </Button>
        </BetterTooltip>
      )}
      <ModelSelector
        setSelectedModelOptions={setSelectedModelOptions}
        messagesLength={messagesLength}
        threadId={threadId}
        className="order-1 md:order-2"
      />
    </header>
  );
}
