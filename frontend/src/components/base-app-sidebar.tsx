import * as React from "react"
import { NavMain } from "@/components/nav-main"
import { AppLauncher } from "@/components/app-launcher"
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar"


export type BaseAppSidebarProps = React.ComponentProps<typeof Sidebar> & {
  /** Items for the AppLauncher */
  appLauncherItems?: React.ComponentProps<typeof AppLauncher>["items"]
  /** Items for the main nav */
  navMainItems?: React.ComponentProps<typeof NavMain>["items"]
}


export function BaseAppSidebar({
  appLauncherItems = [],
  navMainItems = [],
  ...props
}: BaseAppSidebarProps) {
  return (
    <Sidebar className="border-r-0 mt-[53px] pb-[53px]" {...props}>
      <SidebarHeader>
        <AppLauncher items={appLauncherItems} />
        <NavMain items={navMainItems} />
      </SidebarHeader>
      <SidebarContent>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}
