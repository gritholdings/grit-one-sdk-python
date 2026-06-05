"use client"

import * as React from "react"
import {
  MoreHorizontal,
  Trash2,
  Upload,
  Plus,
  Sparkles,
} from "lucide-react"
import type { BulkAction } from "@/components/list-view"

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
  bulkActions?: BulkAction[]
  selectedIds?: string[]
  autoOpenCreate?: boolean
}

export function NavActions({ groups = defaultGroups, deleteUrl, modelName, bulkActions = [], selectedIds = [], autoOpenCreate = false }: NavActionsProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false)
  const [isDeleting, setIsDeleting] = React.useState(false)
  const [showBulkDeleteDialog, setShowBulkDeleteDialog] = React.useState(false)
  const [isBulkDeleting, setIsBulkDeleting] = React.useState(false)
  const [showComponentDialog, setShowComponentDialog] = React.useState<{component: string, props: any} | null>(null)
  const [showCreateDialog, setShowCreateDialog] = React.useState(false)
  const [createUrl, setCreateUrl] = React.useState<string>("")
  
  // Ensure groups is always an array
  const validGroups = Array.isArray(groups) ? groups : defaultGroups

  // Find the create action's URL among the action groups (used when the
  // dialog is opened from a URL rather than a click).
  const findCreateUrl = React.useCallback(() => {
    for (const group of validGroups) {
      for (const item of group) {
        if (item.action === 'create') return item.url || ''
      }
    }
    return ''
  }, [validGroups])

  // Open the create dialog and reflect it in the URL as .../list/new without
  // a page reload, so the popup is shareable and survives a refresh.
  const openCreateDialog = (url: string) => {
    setCreateUrl(url)
    setShowCreateDialog(true)
    const { pathname, search, hash } = window.location
    const base = pathname.replace(/\/$/, '')
    // Only rewrite when on a model list view and not already at .../list/new.
    if (/\/m\/[^/]+\/list$/.test(base)) {
      window.history.pushState({ createDialog: true }, '', `${base}/new${search}${hash}`)
    }
  }

  // Close the create dialog and revert the URL from .../list/new to .../list.
  const handleCreateDialogChange = (open: boolean) => {
    setShowCreateDialog(open)
    if (!open) {
      const { pathname, search, hash } = window.location
      if (/\/list\/new\/?$/.test(pathname)) {
        const reverted = pathname.replace(/\/new\/?$/, '')
        window.history.pushState({}, '', `${reverted}${search}${hash}`)
      }
    }
  }

  // Auto-open the dialog when the page was loaded directly at .../list/new.
  React.useEffect(() => {
    if (!autoOpenCreate) return
    const url = findCreateUrl()
    if (url) {
      setCreateUrl(url)
      setShowCreateDialog(true)
    }
    // Run once on mount; the deep-link state is fixed at load time.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Keep the dialog in sync with browser Back/Forward navigation.
  React.useEffect(() => {
    const onPopState = () => {
      if (/\/list\/new\/?$/.test(window.location.pathname)) {
        const url = findCreateUrl()
        if (url) {
          setCreateUrl(url)
          setShowCreateDialog(true)
        }
      } else {
        setShowCreateDialog(false)
      }
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [findCreateUrl])


  // Add delete option to the first group if deleteUrl is provided
  const enhancedGroups = React.useMemo(() => {
    if (!deleteUrl) return validGroups
    
    const newGroups = [...validGroups]
    const firstGroup = newGroups[0] || []
    
    // Add delete option to the first group
    const deleteOption = {
      label: 'Delete',
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
  
  const handleBulkAction = (action: string) => {
    if (action === "delete") {
      setShowBulkDeleteDialog(true)
    }
  }

  const handleBulkDelete = async () => {
    setIsBulkDeleting(true)
    try {
      const pathMatch = window.location.pathname.match(/^\/app\/([^/]+)\/m\/([^/]+)\/list/)
      if (!pathMatch) return

      const [, appName, model] = pathMatch
      const url = `/app/${appName}/m/${model}/bulk-action`

      const getCookie = (name: string) => {
        const value = `; ${document.cookie}`
        const parts = value.split(`; ${name}=`)
        if (parts.length === 2) return parts.pop()?.split(";").shift()
        return null
      }

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken") || "",
        },
        credentials: "same-origin",
        body: JSON.stringify({ action: "delete", ids: selectedIds }),
      })

      if (response.ok) {
        window.location.reload()
      }
    } finally {
      setIsBulkDeleting(false)
      setShowBulkDeleteDialog(false)
    }
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
    <div className="more-actions-button flex items-center gap-2 text-sm">
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
                                // Show create form dialog and sync URL to .../list/new
                                setIsOpen(false)
                                openCreateDialog(item.url || '')
                              } else if (item.action === 'delete') {
                                // Show delete confirmation dialog
                                setIsOpen(false)
                                setShowDeleteDialog(true)
                              } else if (item.action === 'summarize') {
                                // Open assistant with record context for summarization
                                setIsOpen(false)
                                window.dispatchEvent(new CustomEvent('openAssistantWithContext', {
                                  detail: {
                                    context: item.props?.context || {},
                                    modelName: item.props?.modelName || modelName,
                                    recordName: item.props?.recordName || ''
                                  }
                                }))
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
                            {!item.icon && item.action === 'summarize' && <Sparkles />}
                            <span>{item.label}</span>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      ))}
                    </SidebarMenu>
                  </SidebarGroupContent>
                </SidebarGroup>
              ))}
              {bulkActions.length > 0 && (
                <SidebarGroup className="border-b last:border-none">
                  <SidebarGroupContent className="gap-0">
                    <SidebarMenu>
                      {bulkActions.map((action, index) => (
                        <SidebarMenuItem key={index}>
                          <SidebarMenuButton
                            disabled={selectedIds.length === 0}
                            onClick={() => {
                              setIsOpen(false)
                              handleBulkAction(action.action)
                            }}
                          >
                            {action.action === 'delete' && <Trash2 />}
                            <span>{action.label}{selectedIds.length > 0 ? ` (${selectedIds.length})` : ''}</span>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      ))}
                    </SidebarMenu>
                  </SidebarGroupContent>
                </SidebarGroup>
              )}
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
      
      {/* Bulk Delete Confirmation Dialog */}
      <Dialog open={showBulkDeleteDialog} onOpenChange={setShowBulkDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Bulk Delete</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {selectedIds.length} record(s)? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBulkDeleteDialog(false)} disabled={isBulkDeleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleBulkDelete} disabled={isBulkDeleting}>
              {isBulkDeleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Record Dialog */}
      <CreateRecordDialog
        open={showCreateDialog}
        onOpenChange={handleCreateDialogChange}
        createUrl={createUrl}
        modelName={modelName}
        onSuccess={handleCreateSuccess}
      />
    </div>
  )
}
