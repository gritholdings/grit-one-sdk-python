import * as React from "react"
import { NavMain } from "@/components/nav-main"
import { AppLauncher } from "@/components/app-launcher"
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar"
import { type LucideIcon } from "lucide-react"
import { detectAppFromURL } from "@/utils/app-detection"


export type AppConfiguration = {
  name: string
  key?: string  // Optional: The snake_case app identifier used in URLs (e.g., "agent_studio")
  logo: React.ElementType
  url: string
  navItems: {
    title: string
    url: string
    icon: LucideIcon
    isActive?: boolean
  }[]
}

export type BaseAppSidebarProps = React.ComponentProps<typeof Sidebar> & {
  /** Unified app configurations with navigation items */
  appConfigurations?: AppConfiguration[]
  /** Legacy: Items for the AppLauncher */
  appLauncherItems?: React.ComponentProps<typeof AppLauncher>["items"]
  /** Legacy: Items for the main nav */
  navMainItems?: React.ComponentProps<typeof NavMain>["items"]
}


export function BaseAppSidebar({
  appConfigurations = [],
  appLauncherItems = [],
  navMainItems = [],
  ...props
}: BaseAppSidebarProps) {
  // Detect the initial app based on current URL
  const initialApp = React.useMemo(() => {
    if (typeof window !== 'undefined' && appConfigurations.length > 0) {
      return detectAppFromURL(window.location.pathname, appConfigurations)
    }
    return appConfigurations[0]?.name || ""
  }, [appConfigurations])

  // Track the selected app name
  const [selectedAppName, setSelectedAppName] = React.useState<string>(initialApp)

  // Use new configuration if provided, otherwise fall back to legacy props
  const useConfigurationDriven = appConfigurations.length > 0

  // Extract app launcher items from configurations
  const launcherItems = useConfigurationDriven
    ? appConfigurations.map(config => ({
        name: config.name,
        logo: config.logo,
        href: config.url
      }))
    : appLauncherItems

  // Get navigation items for the selected app
  const currentNavItems = useConfigurationDriven
    ? appConfigurations.find(config => config.name === selectedAppName)?.navItems || []
    : navMainItems

  // Handle app selection change
  const handleAppChange = (appName: string) => {
    setSelectedAppName(appName)
  }

  return (
    <Sidebar className="border-r-0 mt-[53px] pb-[53px]" {...props}>
      <SidebarHeader>
        <AppLauncher 
          items={launcherItems} 
          onAppChange={useConfigurationDriven ? handleAppChange : undefined}
          initialApp={selectedAppName}
        />
        <NavMain items={currentNavItems} />
      </SidebarHeader>
      <SidebarContent>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}
