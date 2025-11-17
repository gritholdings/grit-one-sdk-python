"use client"

import * as React from "react"
import {
  MoreHorizontal,
  Trash2,
  Upload,
  Plus
} from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { getActionComponent } from "@/components/action-component-registry"
import { CreateRecordDialog } from "@/components/create-record-dialog"

const defaultGroups = [
  []
]

interface NavActionsProps {
  groups?: Array<Array<{
    label: string
    icon?: React.ComponentType
    href?: string
    url?: string
    method?: string
    action?: string
    component?: string
    props?: Record<string, any>
  }>>
  deleteUrl?: string
  modelName?: string
}

export function NavActions({ groups = defaultGroups, deleteUrl, modelName }: NavActionsProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false)
  const [isDeleting, setIsDeleting] = React.useState(false)
  const [showComponentDialog, setShowComponentDialog] = React.useState<{component: string, props: any} | null>(null)
  const [showCreateDialog, setShowCreateDialog] = React.useState(false)
  const [createUrl, setCreateUrl] = React.useState<string>("")
  
  // Ensure groups is always an array
  const validGroups = Array.isArray(groups) ? groups : defaultGroups
  
  // Add delete option to the first group if deleteUrl is provided
  const enhancedGroups = React.useMemo(() => {
    if (!deleteUrl) return validGroups
    
    const newGroups = [...validGroups]
    const firstGroup = newGroups[0] || []
    
    // Add delete option to the first group
    const deleteOption = {
      label: `Delete ${modelName || 'Record'}`,
      icon: Trash2,
      action: 'delete',
      url: deleteUrl,
      method: 'POST' as const
    }
    
    // Add delete option to the end of the first group
    newGroups[0] = [...firstGroup, deleteOption]
    
    return newGroups
  }, [validGroups, deleteUrl, modelName])
  
  const handleCreateSuccess = (data: any) => {
    if (data?.redirect_url) {
      window.location.href = data.redirect_url
    } else if (data?.id && modelName) {
      window.location.href = `/r/${modelName}/${data.id}/view`
    } else {
      window.location.reload()
    }
    setShowCreateDialog(false)
  }
  
  const handleDelete = async () => {
    if (!deleteUrl) return
    
    setIsDeleting(true)
    
    try {
      // Get CSRF token from cookies
      const getCookie = (name: string) => {
        const value = `; ${document.cookie}`
        const parts = value.split(`; ${name}=`)
        if (parts.length === 2) return parts.pop()?.split(';').shift()
        return null
      }
      
      const csrfToken = getCookie('csrftoken') || ''
      
      const response = await fetch(deleteUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken
        },
        credentials: 'same-origin'
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.redirect_url) {
          // Redirect to the list view or specified URL
          window.location.href = data.redirect_url
        }
      } else {
        const errorData = await response.json()
        console.error('Failed to delete record:', errorData.error || response.statusText)
        alert(errorData.error || 'Failed to delete record')
      }
    } catch (error) {
      console.error('Error deleting record:', error)
      alert('An error occurred while deleting the record')
    } finally {
      setIsDeleting(false)
      setShowDeleteDialog(false)
    }
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      {/* <div className="text-muted-foreground hidden font-medium md:inline-block">
        Edit Oct 08
      </div> */}
      {/* <Button variant="ghost" size="icon" className="h-7 w-7">
        <Star />
      </Button> */}
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="data-[state=open]:bg-accent h-7 w-7 border border-gray-200"
          >
            <MoreHorizontal />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-56 overflow-hidden rounded-lg p-0"
          align="end"
        >
          <Sidebar collapsible="none" className="bg-transparent">
            <SidebarContent>
              {enhancedGroups.map((group, index) => (
                <SidebarGroup key={index} className="border-b last:border-none">
                  <SidebarGroupContent className="gap-0">
                    <SidebarMenu>
                      {group.map((item, index) => (
                        <SidebarMenuItem key={index}>
                          <SidebarMenuButton
                            onClick={async () => {
                              if (item.component) {
                                // Show component-based action in dialog
                                setIsOpen(false)
                                setShowComponentDialog({ component: item.component, props: item.props })
                              } else if (item.action === 'create') {
                                // Show create form dialog
                                setIsOpen(false)
                                setCreateUrl(item.url || '')
                                setShowCreateDialog(true)
                              } else if (item.action === 'delete') {
                                // Show delete confirmation dialog
                                setIsOpen(false)
                                setShowDeleteDialog(true)
                              } else if (item.url && item.method === 'POST') {
                                // Handle POST request for actions
                                try {
                                  // Get CSRF token from cookies
                                  const getCookie = (name: string) => {
                                    const value = `; ${document.cookie}`
                                    const parts = value.split(`; ${name}=`)
                                    if (parts.length === 2) return parts.pop()?.split(';').shift()
                                    return null
                                  }
                                  
                                  const csrfToken = getCookie('csrftoken') || ''
                                  
                                  const response = await fetch(item.url, {
                                    method: 'POST',
                                    headers: {
                                      'Content-Type': 'application/json',
                                      'X-Requested-With': 'XMLHttpRequest',
                                      'X-CSRFToken': csrfToken
                                    },
                                    credentials: 'same-origin'
                                  })
                                  
                                  if (response.ok) {
                                    const data = await response.json()
                                    if (data.success) {
                                      // Dynamically determine the ID field and redirect
                                      // First try to find an ID field based on modelName
                                      let recordId: string | undefined
                                      let redirectModelName = modelName
                                      
                                      if (modelName) {
                                        // Try model-specific ID field pattern (e.g., course_id for Course)
                                        const modelSpecificField = `${modelName.toLowerCase()}_id`
                                        recordId = data[modelSpecificField]
                                      }
                                      
                                      // If no model-specific field found, try generic 'id' field
                                      if (!recordId && data.id) {
                                        recordId = data.id
                                      }
                                      
                                      // If still no ID found, look for any field ending with '_id'
                                      if (!recordId) {
                                        const idField = Object.keys(data).find(key => key.endsWith('_id'))
                                        if (idField) {
                                          recordId = data[idField]
                                          // Extract model name from field name if modelName not provided
                                          if (!redirectModelName) {
                                            // Convert field like 'course_id' to 'Course'
                                            const modelFromField = idField.replace('_id', '')
                                            redirectModelName = modelFromField.charAt(0).toUpperCase() + modelFromField.slice(1)
                                          }
                                        }
                                      }
                                      
                                      // Redirect if we found an ID and model name
                                      if (recordId && redirectModelName) {
                                        window.location.href = `/r/${redirectModelName}/${recordId}/view`
                                      } else {
                                        // Default: refresh the current page
                                        window.location.reload()
                                      }
                                    }
                                  } else {
                                    console.error('Failed to create record:', response.statusText)
                                  }
                                } catch (error) {
                                  console.error('Error creating record:', error)
                                }
                              } else if (item.href) {
                                window.location.href = item.href
                              }
                              setIsOpen(false)
                            }}
                          >
                            {item.icon && <item.icon />}
                            {!item.icon && item.component === 'FileUploadButton' && <Upload />}
                            {!item.icon && item.action === 'create' && <Plus />}
                            <span>{item.label}</span>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      ))}
                    </SidebarMenu>
                  </SidebarGroupContent>
                </SidebarGroup>
              ))}
            </SidebarContent>
          </Sidebar>
        </PopoverContent>
      </Popover>
      
      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this {modelName || 'record'}? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Component-based Action Dialog */}
      {showComponentDialog && (
        <Dialog open={!!showComponentDialog} onOpenChange={(open) => !open && setShowComponentDialog(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Upload File</DialogTitle>
              <DialogDescription>Select a file to upload</DialogDescription>
            </DialogHeader>
            <div className="py-4">
              {(() => {
                const ActionComponent = getActionComponent(showComponentDialog.component)
                if (ActionComponent) {
                  return <ActionComponent props={showComponentDialog.props} />
                }
                return <div>Component not found</div>
              })()}
            </div>
          </DialogContent>
        </Dialog>
      )}
      
      {/* Create Record Dialog */}
      <CreateRecordDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        createUrl={createUrl}
        modelName={modelName}
        onSuccess={handleCreateSuccess}
      />
    </div>
  )
}
