import { type AppConfiguration } from "@/components/base-app-sidebar"

/**
 * Normalizes a URL by removing trailing slashes
 * @param url - The URL to normalize
 * @returns The normalized URL without trailing slashes
 */
function normalizeURL(url: string): string {
  return url.replace(/\/$/, '')
}

/**
 * Convert snake_case to camelCase
 * Matches the backend's snake_to_camel function in core/utils/case_conversion.py
 * @param str - The snake_case string to convert
 * @returns The camelCase version
 */
function snakeToCamel(str: string): string {
  const components = str.split('_')
  return components[0] + components.slice(1).map(x => x.charAt(0).toUpperCase() + x.slice(1).toLowerCase()).join('')
}

/**
 * Detects which app should be active based on the current URL path
 * @param pathname - The current URL pathname (e.g., "/app/classroom/m/course/list" or legacy "/m/post/list")
 * @param appConfigurations - Array of app configurations to match against
 * @returns The name of the detected app, or the first app name as fallback
 */
export function detectAppFromURL(
  pathname: string,
  appConfigurations: AppConfiguration[]
): string {
  // Return first app as fallback if no configurations
  if (!appConfigurations || appConfigurations.length === 0) {
    return ""
  }

  // Normalize the pathname to handle trailing slashes
  const normalizedPathname = normalizeURL(pathname)

  // NEW: Check for app-prefixed URLs (e.g., "/app/classroom/m/course/list")
  const appPrefixMatch = normalizedPathname.match(/^\/app\/([^/]+)/)
  if (appPrefixMatch) {
    const appNameFromUrl = appPrefixMatch[1]  // e.g., "agent_studio" (snake_case from URL)
    const appNameCamelCase = snakeToCamel(appNameFromUrl)  // Convert to "agentStudio" to match backend keys

    // Find the app configuration that matches this app key
    // The key is in camelCase because backend's convert_keys_to_camel_case() converts dictionary keys
    const matchedApp = appConfigurations.find(
      app => (app.key && app.key.toLowerCase() === appNameCamelCase.toLowerCase()) ||
             app.name.toLowerCase() === appNameFromUrl.toLowerCase()
    )

    if (matchedApp) {
      return matchedApp.name
    }
  }

  // Check each app configuration for matching URLs
  for (const app of appConfigurations) {
    // Check if current pathname matches the app's main href
    if (normalizedPathname === normalizeURL(app.url)) {
      return app.name
    }

    // Check if current pathname matches any of the app's nav item URLs
    if (app.navItems?.some(item => normalizedPathname === normalizeURL(item.url))) {
      return app.name
    }
  }

  // LEGACY: Support old URL format for backwards compatibility
  // Check model-based patterns dynamically based on navItems
  for (const app of appConfigurations) {
    // Extract models from navItems URLs
    // Support both new format ("/app/classroom/m/post/list") and legacy ("/m/post/list")
    const navModels = app.navItems
      ?.map(item => {
        // Try new format first
        let match = item.url.match(/^\/app\/[^/]+\/m\/(\w+)\//)
        if (!match) {
          // Fall back to legacy format
          match = item.url.match(/^\/m\/(\w+)\//)
        }
        return match ? match[1] : null
      })
      .filter((model): model is string => model !== null) || []

    // Build regex pattern for all models of this app (legacy URL format)
    if (navModels.length > 0) {
      const modelsPattern = navModels.join("|")
      const legacyRegex = new RegExp(`^/(m|r)/(${modelsPattern})(/|$)`)

      if (pathname.match(legacyRegex)) {
        return app.name
      }
    }
  }

  // Special case URLs that don't follow model patterns
  if (pathname.startsWith("/tools")) {
    return "Classroom"
  }

  // Default to first app if no match found
  return appConfigurations[0]?.name || ""
}