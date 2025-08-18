import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ChevronRight, ChevronLeft, Search, X } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface InlineItem {
  id: string
  [key: string]: unknown
}

interface InlineEditDialogProps {
  isOpen: boolean
  onClose: () => void
  inlineConfig: {
    model_name: string
    verbose_name: string
    verbose_name_plural: string
    fields: string[]
    items: InlineItem[]
  }
  onSave: (addIds: string[], removeIds: string[]) => Promise<void>
  modelName: string
  recordId: string
}

function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null
  }
  return null
}

export function InlineEditDialog({
  isOpen,
  onClose,
  inlineConfig,
  onSave,
  modelName,
  recordId
}: InlineEditDialogProps) {
  const [selectedItems, setSelectedItems] = useState<InlineItem[]>([])
  const [availableItems, setAvailableItems] = useState<InlineItem[]>([])
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedAvailable, setSelectedAvailable] = useState<Set<string>>(new Set())
  const [selectedCurrent, setSelectedCurrent] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [originalItemIds, setOriginalItemIds] = useState<Set<string>>(new Set())

  // Helper to get the actual item ID
  const getItemId = (item: InlineItem): string => {
    if (item.student && typeof item.student === 'object') {
      return (item.student as any).id
    } else if (item.teacher && typeof item.teacher === 'object') {
      return (item.teacher as any).id
    }
    return item.id
  }

  // Initialize selected items from inline config
  useEffect(() => {
    if (isOpen && inlineConfig) {
      const items = inlineConfig.items || []
      setSelectedItems(items)
      // Use getItemId helper to get the correct ID for both direct and through models
      setOriginalItemIds(new Set(items.map(item => getItemId(item))))
      setSelectedAvailable(new Set())
      setSelectedCurrent(new Set())
      fetchAvailableItems()
    }
  }, [isOpen, inlineConfig])

  // Fetch available items from the backend
  const fetchAvailableItems = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      // Determine the related model to fetch based on inline model name
      let endpoint = ""
      const inlineModelName = inlineConfig.model_name.toLowerCase()
      
      // For Course students/teachers, we need to fetch from a special endpoint
      // that returns all available students/teachers
      const modelNameLower = modelName.toLowerCase()
      
      if (inlineModelName.includes("student") || inlineModelName.includes("teacher")) {
        // Use a special endpoint to get available students/teachers for the course
        const inlineType = inlineModelName.includes("student") ? "students" : "teachers"
        endpoint = `/r/Course/${recordId}/available_${inlineType}/`
      } else {
        // Generic fallback - try to extract the related model name
        const relatedModel = inlineConfig.fields[0]?.replace(/_/g, "")
        if (relatedModel) {
          endpoint = `/m/${relatedModel.charAt(0).toUpperCase() + relatedModel.slice(1)}/list`
        }
      }

      if (!endpoint) {
        // If no endpoint found, return empty list (no available items to add)
        setAvailableItems([])
        return
      }

      const response = await fetch(endpoint, {
        headers: {
          'X-CSRFToken': getCookie('csrftoken') || '',
        }
      })

      if (!response.ok) {
        // For now, if the endpoint doesn't exist, just show no available items
        if (response.status === 404) {
          setAvailableItems([])
          return
        }
        throw new Error(`Failed to fetch available items: ${response.statusText}`)
      }

      const data = await response.json()
      const allItems = data.objects || data.items || []
      
      // Filter out already selected items
      const selectedIds = new Set(selectedItems.map(item => {
        // For through models, get the actual related object ID
        if (item.student && typeof item.student === 'object') {
          return (item.student as any).id
        } else if (item.teacher && typeof item.teacher === 'object') {
          return (item.teacher as any).id
        }
        return item.id
      }))
      
      const available = allItems.filter((item: InlineItem) => !selectedIds.has(item.id))
      setAvailableItems(available)
    } catch (err) {
      console.error("Error fetching available items:", err)
      // Don't show error for missing endpoints, just show empty list
      setAvailableItems([])
    } finally {
      setIsLoading(false)
    }
  }

  // Filter available items based on search
  const filteredAvailable = availableItems.filter(item => {
    if (!searchTerm) return true
    const searchLower = searchTerm.toLowerCase()
    return Object.values(item).some(value => 
      String(value).toLowerCase().includes(searchLower)
    )
  })

  // Handle moving items between lists
  const moveToSelected = () => {
    const itemsToMove = availableItems.filter(item => selectedAvailable.has(item.id))
    setSelectedItems([...selectedItems, ...itemsToMove])
    setAvailableItems(availableItems.filter(item => !selectedAvailable.has(item.id)))
    setSelectedAvailable(new Set())
  }

  const moveToAvailable = () => {
    const itemsToMove = selectedItems.filter(item => {
      // For through models, check the actual related object ID
      const itemId = getItemId(item)
      return selectedCurrent.has(itemId)
    })
    setAvailableItems([...availableItems, ...itemsToMove])
    setSelectedItems(selectedItems.filter(item => {
      const itemId = getItemId(item)
      return !selectedCurrent.has(itemId)
    }))
    setSelectedCurrent(new Set())
  }

  // Helper to get display name for an item
  const getItemDisplay = (item: InlineItem): string => {
    // For through models, display the related object
    if (item.student && typeof item.student === 'object') {
      return (item.student as any).name || String(item.student)
    } else if (item.teacher && typeof item.teacher === 'object') {
      return (item.teacher as any).name || String(item.teacher)
    }
    // For direct items
    return item.name ? String(item.name) : (item.email ? String(item.email) : String(item.id))
  }

  // Toggle selection
  const toggleAvailableSelection = (id: string) => {
    const newSelected = new Set(selectedAvailable)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedAvailable(newSelected)
  }

  const toggleCurrentSelection = (item: InlineItem) => {
    const itemId = getItemId(item)
    const newSelected = new Set(selectedCurrent)
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId)
    } else {
      newSelected.add(itemId)
    }
    setSelectedCurrent(newSelected)
  }

  // Handle save
  const handleSave = async () => {
    setIsSaving(true)
    setError(null)

    try {
      // Calculate changes
      const currentIds = new Set(selectedItems.map(item => getItemId(item)))
      const addIds: string[] = []
      const removeIds: string[] = []

      // Find items to add (in current but not in original)
      currentIds.forEach(id => {
        if (!originalItemIds.has(id)) {
          addIds.push(id)
        }
      })

      // Find items to remove (in original but not in current)
      originalItemIds.forEach(id => {
        if (!currentIds.has(id)) {
          removeIds.push(id)
        }
      })

      // Call the save handler and reload immediately without updating UI
      await onSave(addIds, removeIds)
      
      // Reload the page immediately without closing dialog or updating state
      window.location.reload()
    } catch (err) {
      console.error("Error saving changes:", err)
      setError(err instanceof Error ? err.message : "Failed to save changes")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Edit {inlineConfig.verbose_name_plural}</DialogTitle>
          <DialogDescription>
            Add or remove {inlineConfig.verbose_name_plural.toLowerCase()} for this {modelName.toLowerCase()}.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-[1fr,auto,1fr] gap-4 flex-1 min-h-0 overflow-hidden">
          {/* Available Items */}
          <div className="border rounded-lg p-4 flex flex-col min-h-0">
            <div className="mb-3">
              <Label>Available {inlineConfig.verbose_name_plural}</Label>
              <div className="relative mt-2">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
            <ScrollArea className="flex-1 border rounded p-2">
              {isLoading ? (
                <div className="text-center py-4 text-muted-foreground">Loading...</div>
              ) : filteredAvailable.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground">
                  No available items
                </div>
              ) : (
                <div className="space-y-1">
                  {filteredAvailable.map((item) => (
                    <div
                      key={item.id}
                      className={`p-2 rounded cursor-pointer hover:bg-accent ${
                        selectedAvailable.has(item.id) ? 'bg-accent' : ''
                      }`}
                      onClick={() => toggleAvailableSelection(item.id)}
                    >
                      {getItemDisplay(item)}
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-center px-4">
            <div className="flex flex-col gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={moveToSelected}
                disabled={selectedAvailable.size === 0}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={moveToAvailable}
                disabled={selectedCurrent.size === 0}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Selected Items */}
          <div className="border rounded-lg p-4 flex flex-col min-h-0">
            <div className="mb-3">
              <Label>Selected {inlineConfig.verbose_name_plural}</Label>
              <div className="text-sm text-muted-foreground mt-1">
                {selectedItems.length} item{selectedItems.length !== 1 ? 's' : ''} selected
              </div>
            </div>
            <ScrollArea className="flex-1 border rounded p-2">
              {selectedItems.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground">
                  No items selected
                </div>
              ) : (
                <div className="space-y-1">
                  {selectedItems.map((item) => {
                    const itemId = getItemId(item)
                    return (
                      <div
                        key={itemId}
                        className={`p-2 rounded cursor-pointer hover:bg-accent ${
                          selectedCurrent.has(itemId) ? 'bg-accent' : ''
                        }`}
                        onClick={() => toggleCurrentSelection(item)}
                      >
                        {getItemDisplay(item)}
                      </div>
                    )
                  })}
                </div>
              )}
            </ScrollArea>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}