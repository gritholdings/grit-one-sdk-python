
import type { User } from '../types';

import { PlusIcon } from './icons';
import { SidebarHistory } from './sidebar-history';
import { SidebarUserNav } from './sidebar-user-nav';
import { Button } from '@/components/ui/button';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  useSidebar,
} from '@/components/ui/sidebar';
import { BetterTooltip } from '@/components/ui/tooltip';

export function AppSidebar({
  user,
  currentThreadId = '',
  onNavigate,
}: {
  user: User;
  currentThreadId?: string;
  onNavigate: (threadId: string) => void;
}) {
  const { setOpenMobile } = useSidebar();

  const handleNewChat = () => {
    setOpenMobile(false);
    window.location.href = '/agent/chat/';
  };

  return (
    <Sidebar className="group-data-[side=left]:border-r-0 !top-14 !h-[calc(100vh-3.5rem)]">
      <SidebarHeader>
        <SidebarMenu className="bg-neutral-50">
          <div className="flex flex-row justify-between items-center">
            <div
              onClick={handleNewChat}
              className="flex flex-row gap-3 items-center"
            >
              <span className="text-lg font-semibold px-2 hover:bg-muted rounded-md cursor-pointer">
              </span>
            </div>
            <BetterTooltip content="New Chat" side="bottom" align="start">
              <Button
                variant="ghost"
                className="p-2 h-fit border-none"
                onClick={handleNewChat}
              >
                <PlusIcon />
              </Button>
            </BetterTooltip>
          </div>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarHistory
            user={user}
            currentThreadId={currentThreadId}
            onNavigate={onNavigate}
          />
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
