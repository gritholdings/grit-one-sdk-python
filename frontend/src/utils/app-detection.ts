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
 * Detects which app should be active based on the current URL path
 * @param pathname - The current URL pathname (e.g., "/m/Post/list")
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

  // Define additional models that aren't in navItems but belong to each app
  // These are models that don't have list views in the sidebar but still belong to the app
  const additionalAppModels: Record<string, string[]> = {
    CMS: ["Category", "Author"], // Category and Author are CMS models without nav items
    Classroom: ["Student", "Teacher", "CourseWorkMaterial"] // Additional Classroom models
  }

  // Check model-based patterns dynamically based on navItems and additional models
  for (const app of appConfigurations) {
    // Extract models from navItems URLs (e.g., "/m/Post/list" -> "Post")
    const navModels = app.navItems
      ?.map(item => {
        const match = item.url.match(/^\/m\/(\w+)\//)
        return match ? match[1] : null
      })
      .filter((model): model is string => model !== null) || []
    
    // Combine with additional models for this app
    const allModels = [...navModels, ...(additionalAppModels[app.name] || [])]
    
    // Build regex pattern for all models of this app
    if (allModels.length > 0) {
      const modelsPattern = allModels.join("|")
      const regex = new RegExp(`^/(m|r)/(${modelsPattern})(/|$)`)
      
      if (pathname.match(regex)) {
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