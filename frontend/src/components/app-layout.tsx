import type { ReactNode } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { NavActions } from "@/components/nav-actions"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"

interface AppLayoutProps {
  /** The title to display in the breadcrumb */
  title: string
  /** The tool component to render */
  children: ReactNode
  /** Optional app configurations to pass to the sidebar */
  appConfigurations?: string | Record<string, any>
  /** Optional custom sidebar component to replace the default AppSidebar */
  customSidebar?: ReactNode
  /** Optional className for the content area */
  contentClassName?: string
}

/**
 * Generic layout wrapper for tools that provides consistent structure with sidebar,
 * breadcrumb navigation, and header actions.
 *
 * @example
 * ```tsx
 * import AppLayout from "@/components/showcases/app-layout"
 * import MyTool from "./my-tool"
 *
 * export default function AppMyTool({ appConfigurations }) {
 *   return (
 *     <AppLayout title="My Tool" appConfigurations={appConfigurations}>
 *       <MyTool />
 *     </AppLayout>
 *   )
 * }
 * ```
 */
export default function AppLayout({ title, children, appConfigurations, customSidebar, contentClassName }: AppLayoutProps) {
  return (
    <SidebarProvider>
      {customSidebar || <AppSidebar appConfigurations={appConfigurations} />}
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2">
          <div className="flex flex-1 items-center gap-2 px-3">
            <SidebarTrigger />
            <Separator
              orientation="vertical"
              className="mr-2 data-[orientation=vertical]:h-4"
            />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbPage className="line-clamp-1">
                    {title}
                  </BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
          <div className="ml-auto px-3">
            <NavActions />
          </div>
        </header>
        <div className={contentClassName || "flex flex-1 flex-col gap-4 px-4 py-10"}>
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
