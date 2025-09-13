import type { ComponentType } from 'react'
import FileUploadButton from './file-upload-button'

// Define the props that all action components should accept
export interface ActionComponentProps {
  label?: string
  props?: Record<string, any>
  onSuccess?: () => void
  onError?: (error: Error) => void
}

// Wrapper for FileUploadButton to handle type compatibility
const FileUploadButtonWrapper: ComponentType<ActionComponentProps> = (props) => {
  return FileUploadButton({
    ...props,
    onError: props.onError ? (errorMessage: string) => props.onError!(new Error(errorMessage)) : undefined
  })
}

// Registry of available action components
const componentRegistry: Record<string, ComponentType<ActionComponentProps>> = {
  FileUploadButton: FileUploadButtonWrapper,
  // Add more components here as needed
}

// Function to get a component by name
export function getActionComponent(componentName: string): ComponentType<ActionComponentProps> | null {
  return componentRegistry[componentName] || null
}

// Function to register new components dynamically
export function registerActionComponent(
  name: string, 
  component: ComponentType<ActionComponentProps>
): void {
  componentRegistry[name] = component
}

// Export the registry for debugging/testing
export const ActionComponentRegistry = componentRegistry