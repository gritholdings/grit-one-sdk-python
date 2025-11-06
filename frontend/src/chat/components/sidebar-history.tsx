
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import type { User } from '../types';
import { apiClient } from '../lib/api-client';

import { MoreHorizontalIcon, TrashIcon } from './icons';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@/components/ui/sidebar';

export interface Thread {
  id: string;
  sessionId: string;
  role: string;
  content: string | null;
  createdAt: Date;
  title: string;
}

const ThreadItem = ({
  thread,
  isActive,
  onDelete,
  onNavigate,
  setOpenMobile,
}: {
  thread: Thread;
  isActive: boolean;
  onDelete: (threadId: string) => void;
  onNavigate: (threadId: string) => void;
  setOpenMobile: (open: boolean) => void;
}) => (
  <SidebarMenuItem className="bg-neutral-50 hover:bg-neutral-50">
    <SidebarMenuButton asChild isActive={isActive}>
      <a
        href={`/agent/chat/c/${thread.id}`}
        onClick={(e) => {
          e.preventDefault();
          onNavigate(thread.id);
          setOpenMobile(false);
        }}
      >
        <span>{thread.title}</span>
      </a>
    </SidebarMenuButton>
    <DropdownMenu modal>
      <DropdownMenuTrigger asChild>
        <SidebarMenuAction
          className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground mr-0.5"
          showOnHover={!isActive}
        >
          <MoreHorizontalIcon />
          <span className="sr-only">More</span>
        </SidebarMenuAction>
      </DropdownMenuTrigger>
      <DropdownMenuContent side="bottom" align="end" className="bg-white">
        <DropdownMenuItem
          className="cursor-pointer text-destructive focus:bg-destructive/15 focus:text-destructive"
          onSelect={() => onDelete(thread.id)}
        >
          <TrashIcon />
          <span>Delete</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </SidebarMenuItem>
);

export function SidebarHistory({
  user,
  currentThreadId,
  onNavigate,
}: {
  user: User | undefined;
  currentThreadId: string;
  onNavigate: (threadId: string) => void;
}) {
  const { setOpenMobile } = useSidebar();

  const [threads, setThreads] = useState<Thread[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // fetch history whenever user changes
  useEffect(() => {
    async function fetchHistory() {
      if (!user) {
        setThreads([]);
        return;
      }
      setIsLoading(true);
      const response = await apiClient.post('/agent/api/threads/list');
      try {
        if (response.status !== 200) {
          setThreads([]);
          setIsLoading(false);
          return;
        }
      } catch (error) {
        console.error('Error fetching chat history:', error);
        setThreads([]);
        setIsLoading(false);
        return;
      }
      setIsLoading(false);
      const data = response.data;
      const threads = data.memories.map((thread: any) => ({
        id: thread.id,
        title: thread.title,
      }));
      setThreads(threads);
    }
    fetchHistory();
  }, [user]);

  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleDelete = async () => {
    if (!deleteId) return;
    const deletePromise = apiClient.delete('/agent/api/threads/', { 
      data: { thread_id: deleteId } 
    });

    toast.promise(deletePromise, {
      loading: 'Deleting thread...',
      success: () => {
        // refresh the entire browser
        window.location.reload();
        return 'Thread deleted successfully';
      },
      error: 'Failed to delete thread',
    });

    setShowDeleteDialog(false);
  };

  if (!user) {
    return (
      <SidebarGroup>
        <SidebarGroupContent>
          <div className="text-zinc-500 w-full flex justify-center items-center text-sm">
            Login to save and revisit previous threads.
          </div>
        </SidebarGroupContent>
      </SidebarGroup>
    );
  }

  if (isLoading) {
    return (
      <SidebarGroup>
        <SidebarGroupContent>
          <div className="flex flex-col">
            {[44, 32, 28, 64, 52].map((w) => (
              <div key={w} className="rounded-md h-8 flex gap-2 px-2 items-center">
                <div
                  className="h-4 rounded-md flex-1 bg-sidebar-accent-foreground/10"
                  style={{ maxWidth: `${w}%` }}
                />
              </div>
            ))}
          </div>
        </SidebarGroupContent>
      </SidebarGroup>
    );
  }

  if (threads.length === 0) {
    return (
      <SidebarGroup>
        <SidebarGroupContent>
          <div className="text-zinc-500 w-full flex justify-center items-center text-sm">
            Your conversations will appear here once you start chatting.
          </div>
        </SidebarGroupContent>
      </SidebarGroup>
    );
  }

  return (
    <>
      <SidebarGroup>
        <SidebarGroupContent>
          <SidebarMenu className="bg-neutral-50">
                <div>
                  {threads.map((thread) => (
                    <ThreadItem
                      key={thread.id}
                      thread={thread}
                      isActive={thread.id === currentThreadId}
                      onDelete={(threadId) => {
                        setDeleteId(threadId);
                        setShowDeleteDialog(true);
                      }}
                      onNavigate={onNavigate}
                      setOpenMobile={setOpenMobile}
                    />
                  ))}
                </div>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="sm:max-w-[425px] bg-white">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-xl font-semibold text-gray-900">Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription className="text-sm text-gray-600 mt-2">
              This action cannot be undone. This will permanently delete your chat.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex-row justify-center gap-3 sm:justify-center">
            <AlertDialogCancel className="mt-0 bg-gray-100 hover:bg-gray-200 text-gray-900 border-0">Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDelete}
              className="mt-0 bg-red-600 hover:bg-red-700 text-white border-0"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}