import { ChevronUp } from 'lucide-react';
// import Image from 'next/image';
import { type User } from '../types';
import { baseUrl } from '../lib/api-client';
// import { signOut } from 'next-auth/react';
// import { useTheme } from 'next-themes';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';

export function SidebarUserNav({ user }: { user: User }) {
  // const { setTheme, theme } = useTheme();

  return (
    <SidebarMenu className="bg-neutral-50">
      <SidebarMenuItem className="p-0">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton className="bg-neutral-50 text-neutral-950 h-10 border-none outline-none focus:outline-none ring-0 focus:ring-0 hover:bg-neutral-50">
              {/* <Image
                src={`https://avatar.vercel.sh/${user.email}`}
                alt={user.email ?? 'User Avatar'}
                width={24}
                height={24}
                className="rounded-full"
              /> */}
              <span className="truncate">{user?.email}</span>
              <ChevronUp className="ml-auto" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            side="top"
            className="w-[--radix-popper-anchor-width]"
          >
            <DropdownMenuItem asChild className="data-[highlighted]:bg-transparent data-[highlighted]:text-inherit hover:bg-transparent focus:bg-transparent">
              <button
                className="w-full cursor-pointer bg-neutral-50 text-neutral-950"
                onClick={() => {
                  window.location.href = `${baseUrl}/profile`;
                }}
              >
                Profile
              </button>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <button
                className="w-full cursor-pointer bg-neutral-50 text-neutral-950"
                onClick={() => {
                  window.location.href = `${baseUrl}/auth/logout`;
                }}
              >
                Logout
              </button>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
