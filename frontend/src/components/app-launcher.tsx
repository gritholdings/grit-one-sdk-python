import * as React from "react"
import { ChevronDown } from "lucide-react"

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

export function AppLauncher({
  items,
  onAppChange,
  initialApp,
}: {
  items: {
    name: string
    logo: React.ElementType
    href: string
  }[]
  onAppChange?: (appName: string) => void
  initialApp?: string
}) {
  // Initialize with the provided initial app or fallback to first item
  const getInitialItem = () => {
    if (initialApp) {
      const found = items.find(item => item.name === initialApp)
      if (found) return found
    }
    return items[0]
  }
  
  const [activeItem, setActiveItem] = React.useState(getInitialItem())

  // Update active item when initialApp changes
  React.useEffect(() => {
    if (initialApp) {
      const found = items.find(item => item.name === initialApp)
      if (found && found !== activeItem) {
        setActiveItem(found)
      }
    }
  }, [initialApp, items])

  // Notify parent component when active item is set initially
  React.useEffect(() => {
    if (activeItem && onAppChange) {
      onAppChange(activeItem.name)
    }
  }, [])

  if (!activeItem) {
    return null
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton className="w-fit px-1.5">
              <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-5 items-center justify-center rounded-md">
                <activeItem.logo className="size-3" />
              </div>
              <span className="truncate font-medium">{activeItem.name}</span>
              <ChevronDown className="opacity-50" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-64 rounded-lg"
            align="start"
            side="bottom"
            sideOffset={4}
          >
            <DropdownMenuLabel className="text-muted-foreground text-xs">
              App Launcher
            </DropdownMenuLabel>
            {items.map((item) => (
              <DropdownMenuItem
                key={item.name}
                onClick={() => {
                  setActiveItem(item)
                  // Notify parent component of app change
                  if (onAppChange) {
                    onAppChange(item.name)
                  }
                  if (item.href) {
                    window.location.href = item.href
                  }
                }}
                className="gap-2 p-2 cursor-pointer"
              >
                <div className="flex size-6 items-center justify-center rounded-xs border">
                  <item.logo className="size-4 shrink-0" />
                </div>
                {item.name}
              </DropdownMenuItem>
            ))}
            {/* <DropdownMenuSeparator /> */}
            {/* <DropdownMenuItem className="gap-2 p-2">
              <div className="bg-background flex size-6 items-center justify-center rounded-md border">
                <Plus className="size-4" />
              </div>
              <div className="text-muted-foreground font-medium">Add</div>
            </DropdownMenuItem> */}
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
