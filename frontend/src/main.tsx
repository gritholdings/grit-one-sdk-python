import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Function to dynamically import components
async function loadComponent(componentName: string) {
  // For Vite, we need to use glob imports with eager loading for production builds
  const components = {
    // Import all components from app_frontend components
    ...import.meta.glob('../app_frontend/src/components/*.tsx', { eager: true }),
    // Import all components from app_frontend showcases
    ...import.meta.glob('../app_frontend/src/components/showcases/*.tsx', { eager: true }),
    // Import all components from frontend showcases
    ...import.meta.glob('./components/showcases/*.tsx', { eager: true }),
    // Import all components from ui
    ...import.meta.glob('./components/ui/*.tsx', { eager: true }),
    // Import all components from root components
    ...import.meta.glob('./components/*.tsx', { eager: true })
  }
  
  // Convert component name to kebab-case for showcases
  // AppCountButton -> app-count-button
  const kebabName = componentName
    .replace(/([a-z])([A-Z])/g, '$1-$2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1-$2')
    .toLowerCase()
  
  // Try different paths
  const possiblePaths = [
    `../app_frontend/src/components/${kebabName}.tsx`,
    `../app_frontend/src/components/showcases/${kebabName}.tsx`,
    `../app_frontend/src/components/showcases/app-count-button.tsx`, // Special case for AppCountButton
    `./components/ui/${componentName.toLowerCase()}.tsx`,
    `./components/showcases/${kebabName}.tsx`,
    `./components/showcases/app-count-button.tsx`, // Special case for AppCountButton in frontend
    `./components/${componentName}.tsx`,
    `./components/${kebabName}.tsx`,
    `./components/record-detail.tsx` // Special case for RecordDetail
  ]
  
  for (const path of possiblePaths) {
    if (components[path]) {
      try {
        // With eager loading, modules are already loaded
        const module = components[path] as any
        // Try to find the component by name first, then default export
        const component = module[componentName] || module.default || module['default']
        if (component) {
          return component
        }
      } catch (error) {
        console.error(`Error loading component ${componentName} from ${path}:`, error)
      }
    }
  }
  
  console.error(`Component ${componentName} not found in any location`)
  return null
}

// Function to mount React components based on data-react-component attribute
async function mountComponents() {
  // Find all elements with data-react-component attribute
  const componentElements = document.querySelectorAll('[data-react-component]')
  
  for (const element of componentElements) {
    const componentName = element.getAttribute('data-react-component')
    
    if (!componentName) {
      console.warn('No component name specified in data-react-component')
      continue
    }
    
    // Dynamically load the component
    const Component = await loadComponent(componentName)
    
    if (!Component) {
      console.warn(`Component ${componentName} could not be loaded`)
      continue
    }
    
    // Extract props from data attributes
    const props: Record<string, any> = {}
    Array.from(element.attributes).forEach((attr) => {
      if (attr.name.startsWith('data-prop-')) {
        const propName = attr.name.replace('data-prop-', '').replace(/-([a-z])/g, (g) => g[1].toUpperCase())
        
        // Special handling for data-source
        if (attr.name === 'data-prop-data-source') {
          // Get data from the json_script tag with the specified ID
          const scriptElement = document.getElementById(attr.value)
          if (scriptElement) {
            try {
              props['data'] = JSON.parse(scriptElement.textContent || '{}')
            } catch (e) {
              console.error(`Failed to parse data from script element with id "${attr.value}":`, e)
              props['data'] = {}
            }
          } else {
            console.warn(`Script element with id "${attr.value}" not found`)
            props['data'] = {}
          }
        } else {
          try {
            // Try to parse as JSON first (for objects, arrays, booleans, numbers)
            props[propName] = JSON.parse(attr.value)
          } catch {
            // If not valid JSON, treat as string
            props[propName] = attr.value
          }
        }
      }
    })
    
    // Create root and render component
    const root = createRoot(element as HTMLElement)
    root.render(
      <StrictMode>
        <Component {...props} />
      </StrictMode>
    )
  }
}

// Mount components when DOM is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountComponents)
} else {
  // DOM is already loaded
  mountComponents()
}

// Also mount the main App if root element exists
const rootElement = document.getElementById('root')
if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}