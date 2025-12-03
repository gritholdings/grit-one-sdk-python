import { BaseAppSidebar } from "@/components/base-app-sidebar"
import * as Icons from "lucide-react"

interface AppSidebarProps {
  appConfigurations?: string | Record<string, any> | any[]
  [key: string]: any
}

// Map string icon names to Lucide icon components
const iconMap: Record<string, any> = {
  GraduationCap: Icons.GraduationCap,
  BookOpen: Icons.BookOpen,
  Bot: Icons.Bot,
  Wrench: Icons.Wrench,
  Briefcase: Icons.Briefcase,
  FileText: Icons.FileText,
  FolderOpen: Icons.FolderOpen,
  ChartCandlestick: Icons.ChartCandlestick,
}

/**
 * Convert snake_case to PascalCase
 * Examples: 'course' -> 'Course', 'course_work' -> 'CourseWork'
 */
function toPascalCase(str: string): string {
  return str
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join('')
}

/**
 * Convert snake_case to camelCase
 * Examples: 'course' -> 'course', 'course_work' -> 'courseWork'
 */
function toCamelCase(str: string): string {
  const parts = str.split('_')
  return parts[0] + parts.slice(1).map(word =>
    word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
  ).join('')
}

/**
 * Transform backend APP_METADATA_SETTINGS into AppConfiguration format
 * Backend structure: { APPS: { appKey: { label, icon, tabs } }, MODELS: {...}, TABS: {...} }
 * Frontend structure: [{ name, logo, url, navItems: [{ title, url, icon }] }]
 */
function transformAppSettings(settings: any, iconMap: Record<string, any>): any[] {
  if (!settings || !settings.APPS) {
    return []
  }

  const apps = settings.APPS
  const models = settings.MODELS || {}
  const tabs = settings.TABS || {}

  // Handle both dict and array formats for APPS
  const appEntries: [string, any][] = Array.isArray(apps)
    ? apps.map((app: any, idx: number) => [`app_${idx}`, app] as [string, any])
    : Object.entries(apps)

  return appEntries.map(([appKey, appConfig]: [string, any]) => {
    // Build nav items from tabs
    const navItems = (appConfig.tabs || []).map((tabKey: string) => {
      // Convert tabKey to camelCase for lookup since backend converts all keys to camelCase
      // e.g., 'course_work' -> 'courseWork'
      const camelKey = toCamelCase(tabKey)

      // Check if it's a model or a custom tab (use camelCase key for lookup)
      const modelConfig = models[camelKey]
      const tabConfig = tabs[camelKey]

      if (modelConfig) {
        // It's a model - use URL from backend (app-prefixed) or construct legacy format as fallback
        const modelName = toPascalCase(tabKey)
        const title = modelConfig.pluralLabel || modelConfig.label || modelName
        // Prefer URL from app-specific tabUrls (set by resolve_urls_in_app_metadata),
        // then model URL, then legacy fallback
        const url = appConfig.tabUrls?.[camelKey] || modelConfig.url || `/m/${modelName}/list`
        return {
          title,
          url,
          icon: iconMap[modelConfig.icon] || Icons.FileText
        }
      } else if (tabConfig) {
        // It's a custom tab - use the tab config
        return {
          title: tabConfig.label || tabKey,
          url: tabConfig.url || (tabConfig.urlName ? `/${tabConfig.urlName}` : `/${tabKey}`),
          icon: iconMap[tabConfig.icon] || Icons.Wrench
        }
      } else {
        // Fallback - create a basic nav item using PascalCase
        const pascalKey = toPascalCase(tabKey)
        return {
          title: pascalKey.replace(/([A-Z])/g, ' $1').trim(),
          url: `/${pascalKey}`,
          icon: Icons.FileText
        }
      }
    })

    // Determine the app's main URL (first nav item or fallback)
    const mainUrl = navItems.length > 0 ? navItems[0].url : `/${appKey}`

    return {
      name: appConfig.label || appKey,
      key: appKey,  // Store the original snake_case key for URL matching
      logo: iconMap[appConfig.icon] || Icons.FileText,
      url: mainUrl,
      navItems
    }
  })
}

export function AppSidebar({
  appConfigurations = [],
  ...props
}: AppSidebarProps) {
  // Parse appConfigurations if it's a string (from data-prop-app-configurations)
  let rawSettings: any = null

  if (typeof appConfigurations === 'string') {
    try {
      rawSettings = JSON.parse(appConfigurations)
    } catch (e) {
      console.error('Failed to parse appConfigurations:', e)
      rawSettings = null
    }
  } else if (appConfigurations && typeof appConfigurations === 'object') {
    rawSettings = appConfigurations
  }

  // Transform backend APP_METADATA_SETTINGS into AppConfiguration format
  const configs = rawSettings ? transformAppSettings(rawSettings, iconMap) : []
    
  return (
    <BaseAppSidebar
      appConfigurations={configs}
      {...props}
    />
  )
}