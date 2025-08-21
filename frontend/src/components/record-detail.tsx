/**
 * RecordDetail component displays and edits a record's details.
 * Widgets: TextInput, Textarea, Select
 */
import { AppSidebar } from "@app_frontend/components/app-sidebar"
import { NavActions } from "@/components/nav-actions"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useState, useEffect } from "react"
import { Pencil, Save, X, Edit } from "lucide-react"
import { InlineEditDialog } from "@/components/inline-edit-dialog"

interface FieldConfig {
  widget: "TextInput" | "Textarea" | "Select"
  help_text?: string
  required?: boolean
  choices?: Array<{ value: string; label: string }>
}

interface InlineItem {
  id: string
  [key: string]: unknown
}

interface InlineConfig {
  model_name: string
  verbose_name: string
  verbose_name_plural: string
  fields: string[]
  readonly_fields: string[]
  can_delete: boolean
  items: InlineItem[]
}

interface RecordDetailProps {
  data?: Record<string, unknown>
  fieldsets?: Array<[string, { fields: string[] }]>
  form?: Record<string, FieldConfig>
  inlines?: InlineConfig[]
  updateUrl: string
}

// Helper function to get CSRF token
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null
  }
  return null
}

export default function RecordDetail({
  data: record = {},
  fieldsets = [],
  form = {},
  inlines = [],
  updateUrl
}: RecordDetailProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState<Record<string, unknown>>(record)
  const [errors, setErrors] = useState<Record<string, string[]>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [generalError, setGeneralError] = useState<string | null>(null)
  const [hasInitialized, setHasInitialized] = useState(false)
  const [editingInline, setEditingInline] = useState<InlineConfig | null>(null)
  const [inlinesData, setInlinesData] = useState<InlineConfig[]>(() => inlines || [])
  
  // Derive delete URL and model name from update URL
  const deleteUrl = updateUrl ? updateUrl.replace('/update', '/delete') : undefined
  const modelName = updateUrl ? updateUrl.split('/')[2] : undefined

  // Initialize form data from record only once or when record ID changes
  useEffect(() => {
    // Only update if we haven't initialized yet or if the record ID has changed
    const recordId = record.id as string | undefined
    if (!hasInitialized || (recordId && formData.id !== recordId)) {
      setFormData(record)
      setHasInitialized(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [record.id, hasInitialized])

  // Update inlines data when inlines prop changes
  useEffect(() => {
    if (inlines) {
      setInlinesData(inlines)
    }
  }, [inlines])

  // Get fields to display (either from fieldsets or all form fields)
  const getFieldsToDisplay = (): string[] => {
    if (fieldsets.length > 0) {
      const fields: string[] = []
      fieldsets.forEach(([, config]) => {
        fields.push(...config.fields)
      })
      return fields
    }
    return Object.keys(form).length > 0 ? Object.keys(form) : Object.keys(record)
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
  }

  const handleSubmit = async () => {
    setIsSubmitting(true)
    setErrors({})
    setGeneralError(null)

    try {
      // Get the course ID from the record
      const courseId = record.id
      if (!courseId) {
        throw new Error("Course ID not found")
      }

      // Prepare form data
      const formDataToSend = new FormData()
      Object.keys(form).forEach(field => {
        const value = formData[field]
        if (value !== undefined && value !== null) {
          // Handle foreign key objects - send just the ID
          if (typeof value === 'object' && 'id' in value) {
            formDataToSend.append(field, String(value.id))
          } else {
            formDataToSend.append(field, String(value))
          }
        }
      })

      // Get CSRF token
      const csrfToken = getCookie('csrftoken')
      if (!csrfToken) {
        throw new Error("CSRF token not found")
      }

      // Submit the form
      const url = updateUrl
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
        },
        body: formDataToSend,
        credentials: 'same-origin'
      })

      const result = await response.json()

      if (result.success) {
        // Redirect on success
        if (result.redirect_url) {
          window.location.href = result.redirect_url
        } else {
          window.location.reload()
        }
      } else {
        // Handle validation errors
        if (result.errors) {
          if (result.errors.__all__) {
            setGeneralError(result.errors.__all__.join(' '))
          }
          setErrors(result.errors)
        }
      }
    } catch (error) {
      console.error('Error submitting form:', error)
      setGeneralError('An error occurred while saving. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    setFormData(record)
    setErrors({})
    setGeneralError(null)
  }

  const handleInlineSave = async (addIds: string[], removeIds: string[]) => {
    if (!editingInline) return
    
    const modelName = (record.id as string).split('-')[0] || 'Model'
    const inlineModelName = editingInline.model_name
    const recordId = record.id as string
    
    // Build the URL for inline update
    const inlineUpdateUrl = updateUrl.replace('/update', `/inline/${inlineModelName}/update`)
    
    const response = await fetch(inlineUpdateUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') || '',
      },
      body: JSON.stringify({
        add: addIds,
        remove: removeIds
      })
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Failed to update')
    }
    
    // Don't update local state since we're going to reload the page
    // This prevents the UI from showing temporary "-" values
    await response.json() // Still consume the response to complete the request
  }

  const renderField = (field: string) => {
    const fieldConfig = form[field]
    const value = formData[field]
    
    // Handle objects (like foreign keys) by extracting their display value
    let displayValue = ''
    let selectValue = '' // For Select widget, we need the ID
    
    if (value === null || value === undefined) {
      displayValue = ''
      selectValue = ''
    } else if (typeof value === 'object' && 'name' in value) {
      // Foreign key object with name property
      displayValue = String(value.name)
      // For Select widgets, use the ID as the value
      selectValue = 'id' in value ? String(value.id) : String(value.name)
    } else if (typeof value === 'object' && 'id' in value) {
      // Foreign key object with only id
      displayValue = String(value.id)
      selectValue = String(value.id)
    } else {
      displayValue = String(value)
      selectValue = String(value)
    }
    
    const fieldErrors = errors[field]

    if (!isEditing || !fieldConfig) {
      // Read-only mode
      // For Select widgets, show the label instead of the value
      let displayText = displayValue || '-'
      if (fieldConfig?.widget === 'Select' && fieldConfig.choices && displayValue) {
        const choice = fieldConfig.choices.find(c => c.value === displayValue)
        displayText = choice ? choice.label : displayValue
      }
      
      return (
        <div key={field} className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5">
          <dt className="text-sm font-medium text-gray-500">
            {field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </dt>
          <dd className="mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0">
            {displayText}
          </dd>
        </div>
      )
    }

    // Edit mode
    return (
      <div key={field} className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5">
        <Label htmlFor={field} className="text-sm font-medium text-gray-500 sm:pt-1.5">
          {field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          {fieldConfig.required && <span className="text-red-500 ml-1">*</span>}
        </Label>
        <div className="mt-1 sm:col-span-2 sm:mt-0">
          {fieldConfig.widget === 'Select' && fieldConfig.choices ? (
            <Select
              value={selectValue}
              onValueChange={(value) => handleInputChange(field, value)}
              disabled={isSubmitting}
            >
              <SelectTrigger className={fieldErrors ? 'border-red-500' : ''}>
                <SelectValue placeholder="Select an option..." />
              </SelectTrigger>
              <SelectContent>
                {fieldConfig.choices.map((choice) => (
                  <SelectItem key={choice.value} value={choice.value}>
                    {choice.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : fieldConfig.widget === 'Textarea' ? (
            <Textarea
              id={field}
              value={displayValue}
              onChange={(e) => handleInputChange(field, e.target.value)}
              className={fieldErrors ? 'border-red-500' : ''}
              rows={4}
              disabled={isSubmitting}
            />
          ) : (
            <Input
              id={field}
              type="text"
              value={displayValue}
              onChange={(e) => handleInputChange(field, e.target.value)}
              className={fieldErrors ? 'border-red-500' : ''}
              disabled={isSubmitting}
            />
          )}
          {fieldConfig.help_text && (
            <p className="mt-1 text-sm text-gray-500">{fieldConfig.help_text}</p>
          )}
          {fieldErrors && fieldErrors.map((error, index) => (
            <p key={index} className="mt-1 text-sm text-red-600">{error}</p>
          ))}
        </div>
      </div>
    )
  }

  const fieldsToDisplay = getFieldsToDisplay()
  const hasFormConfig = Object.keys(form).length > 0

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2">
          <div className="flex flex-1 items-center gap-2 px-3">
            <SidebarTrigger />
            <Separator
              orientation="vertical"
              className="mr-2 data-[orientation=vertical]:h-4"
            />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbPage className="line-clamp-1">
                    {record.name ? String(record.name) : 'Record Detail'}
                  </BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
          <div className="ml-auto px-3">
            <NavActions deleteUrl={deleteUrl} modelName={modelName} />
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 px-4 py-10">
          <div className="max-w-4xl">
            {generalError && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{generalError}</AlertDescription>
              </Alert>
            )}
            
            {/* Edit button at the top */}
            {hasFormConfig && (
              <div className="flex justify-end mb-4">
                {!isEditing ? (
                  <Button
                    onClick={() => setIsEditing(true)}
                    size="sm"
                    variant="outline"
                  >
                    <Pencil className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                ) : (
                  <div className="flex gap-2">
                    <Button
                      onClick={handleCancel}
                      size="sm"
                      variant="outline"
                      disabled={isSubmitting}
                    >
                      <X className="h-4 w-4 mr-1" />
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSubmit}
                      size="sm"
                      disabled={isSubmitting}
                    >
                      <Save className="h-4 w-4 mr-1" />
                      {isSubmitting ? 'Saving...' : 'Save'}
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Render all fieldsets */}
            {fieldsets.length > 0 ? (
              fieldsets.map(([title, config], index) => (
                <div key={index} className="bg-white shadow sm:rounded-lg mb-6">
                  <div className="px-4 py-5 sm:px-6">
                    <h3 className="text-lg font-medium leading-6 text-gray-900">
                      {title}
                    </h3>
                  </div>
                  <div className="border-t border-gray-200">
                    <dl className="divide-y divide-gray-200 px-4 sm:px-6">
                      {config.fields.map(field => renderField(field))}
                    </dl>
                  </div>
                </div>
              ))
            ) : (
              <div className="bg-white shadow sm:rounded-lg">
                <div className="px-4 py-5 sm:px-6">
                  <h3 className="text-lg font-medium leading-6 text-gray-900">
                    Information
                  </h3>
                </div>
                <div className="border-t border-gray-200">
                  <dl className="divide-y divide-gray-200 px-4 sm:px-6">
                    {fieldsToDisplay.map(field => renderField(field))}
                  </dl>
                </div>
              </div>
            )}

            {/* Render inline models */}
            {inlinesData && inlinesData.length > 0 && (
              <div className="mt-8">
                {inlinesData.map((inline, inlineIndex) => (
                  <div key={inlineIndex} className="bg-white shadow sm:rounded-lg mb-6">
                    <div className="px-4 py-5 sm:px-6 flex justify-between items-center">
                      <h3 className="text-lg font-medium leading-6 text-gray-900">
                        {inline.verbose_name_plural}
                      </h3>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setEditingInline(inline)}
                      >
                        <Edit className="h-4 w-4 mr-1" />
                        Edit
                      </Button>
                    </div>
                    <div className="border-t border-gray-200">
                      {inline.items.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                              <tr>
                                {inline.fields.map((field) => (
                                  <th
                                    key={field}
                                    scope="col"
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                                  >
                                    {field === 'object_link' 
                                      ? inline.verbose_name 
                                      : field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                              {inline.items.map((item) => (
                                <tr key={item.id}>
                                  {inline.fields.map((field) => {
                                    const value = item[field]
                                    let displayValue = ''
                                    
                                    if (value === null || value === undefined) {
                                      displayValue = '-'
                                    } else if (typeof value === 'object' && 'name' in value) {
                                      displayValue = String(value.name)
                                    } else if (typeof value === 'object' && 'id' in value) {
                                      displayValue = String(value.id)
                                    } else {
                                      displayValue = String(value)
                                    }
                                    
                                    return (
                                      <td key={field} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {displayValue}
                                      </td>
                                    )
                                  })}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="px-4 py-5 sm:px-6 text-sm text-gray-500">
                          No {inline.verbose_name_plural.toLowerCase()} found.
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Edit button at the bottom - only show when there are many fields */}
            {hasFormConfig && fieldsToDisplay.length > 5 && (
              <div className="flex justify-end mt-6 pt-4 border-t">
                {!isEditing ? (
                  <Button
                    onClick={() => setIsEditing(true)}
                    size="sm"
                    variant="outline"
                  >
                    <Pencil className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                ) : (
                  <div className="flex gap-2">
                    <Button
                      onClick={handleCancel}
                      size="sm"
                      variant="outline"
                      disabled={isSubmitting}
                    >
                      <X className="h-4 w-4 mr-1" />
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSubmit}
                      size="sm"
                      disabled={isSubmitting}
                    >
                      <Save className="h-4 w-4 mr-1" />
                      {isSubmitting ? 'Saving...' : 'Save'}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </SidebarInset>
      
      {/* Inline Edit Dialog */}
      {editingInline && (
        <InlineEditDialog
          isOpen={!!editingInline}
          onClose={() => setEditingInline(null)}
          inlineConfig={editingInline}
          onSave={handleInlineSave}
          modelName={record.name ? String(record.name) : 'Record'}
          recordId={record.id as string}
        />
      )}
    </SidebarProvider>
  )
}