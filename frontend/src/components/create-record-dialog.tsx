import React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"
import { FormFieldRenderer } from "@/components/form-field-renderer"
import type { FormFieldConfig } from "@/components/form-field-renderer"


interface CreateRecordDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  createUrl: string
  modelName?: string
  onSuccess?: (data: any) => void
  onError?: (error: any) => void
  initialData?: Record<string, any>
  hiddenFields?: Record<string, any>
}

export function CreateRecordDialog({
  open,
  onOpenChange,
  createUrl,
  modelName = "Record",
  onSuccess,
  onError,
  initialData = {},
  hiddenFields = {}
}: CreateRecordDialogProps) {
  const [isCreating, setIsCreating] = React.useState(false)
  const [loadingForm, setLoadingForm] = React.useState(false)
  const [formFields, setFormFields] = React.useState<FormFieldConfig[]>([])
  const [formData, setFormData] = React.useState<Record<string, any>>({})
  const [errors, setErrors] = React.useState<Record<string, string>>({})

  React.useEffect(() => {
    if (open && createUrl) {
      loadCreateForm()
    }
  }, [open, createUrl])

  const loadCreateForm = async () => {
    setLoadingForm(true)
    setErrors({})
    
    try {
      const getCookie = (name: string) => {
        const value = `; ${document.cookie}`
        const parts = value.split(`; ${name}=`)
        if (parts.length === 2) return parts.pop()?.split(';').shift()
        return null
      }
      
      const csrfToken = getCookie('csrftoken') || ''
      
      const response = await fetch(createUrl, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        
        if (data.form_fields && Array.isArray(data.form_fields)) {
          const fields: FormFieldConfig[] = data.form_fields.map((field: any) => {
            const fieldConfig: FormFieldConfig = {
              name: field.name,
              label: field.label || field.name.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()),
              type: field.type || 'text',
              required: field.required || false,
              choices: field.choices,
              help_text: field.help_text,
              default: field.default,
              readonly: hiddenFields[field.name] !== undefined
            }
            return fieldConfig
          })
          
          const initialFormData: Record<string, any> = { ...hiddenFields }
          
          fields.forEach(field => {
            if (hiddenFields[field.name] !== undefined) {
              initialFormData[field.name] = hiddenFields[field.name]
            } else if (initialData[field.name] !== undefined) {
              initialFormData[field.name] = initialData[field.name]
            } else if (field.default !== undefined) {
              initialFormData[field.name] = field.default
            } else {
              initialFormData[field.name] = ''
            }
          })
          
          setFormFields(fields)
          setFormData(initialFormData)
        } else {
          // Fallback to default fields if response doesn't have form_fields
          setFormFields([
            { name: 'name', label: 'Name', type: 'text', required: true },
            { name: 'description', label: 'Description', type: 'textarea', required: false }
          ])
          setFormData({ ...hiddenFields, name: '', description: '', ...initialData })
        }
      } else {
        setFormFields([
          { name: 'name', label: 'Name', type: 'text', required: true },
          { name: 'description', label: 'Description', type: 'textarea', required: false }
        ])
        setFormData({ ...hiddenFields, name: '', description: '', ...initialData })
      }
    } catch (error) {
      console.error('Error loading form:', error)
      setFormFields([
        { name: 'name', label: 'Name', type: 'text', required: true },
        { name: 'description', label: 'Description', type: 'textarea', required: false }
      ])
      setFormData({ ...hiddenFields, name: '', description: '', ...initialData })
    } finally {
      setLoadingForm(false)
    }
  }

  const handleCreate = async () => {
    if (!createUrl) return
    
    setIsCreating(true)
    setErrors({})
    
    try {
      const getCookie = (name: string) => {
        const value = `; ${document.cookie}`
        const parts = value.split(`; ${name}=`)
        if (parts.length === 2) return parts.pop()?.split(';').shift()
        return null
      }
      
      const csrfToken = getCookie('csrftoken') || ''
      
      const formDataToSend = new FormData()
      Object.keys(formData).forEach(key => {
        if (formData[key] !== null && formData[key] !== undefined) {
          formDataToSend.append(key, formData[key])
        }
      })
      
      const response = await fetch(createUrl, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken
        },
        body: formDataToSend
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.redirect_url) {
          if (onSuccess) {
            onSuccess(data)
          } else {
            window.location.href = data.redirect_url
          }
        } else {
          onSuccess?.(data)
        }
        onOpenChange(false)
        setFormData({})
      } else {
        const data = await response.json()
        if (data.errors) {
          setErrors(data.errors)
        } else {
          alert('An error occurred while creating the record')
        }
        onError?.(data)
      }
    } catch (error) {
      console.error('Error creating record:', error)
      alert('An error occurred while creating the record')
      onError?.(error)
    } finally {
      setIsCreating(false)
    }
  }

  const handleFieldChange = (fieldName: string, value: any) => {
    setFormData({
      ...formData,
      [fieldName]: value
    })
  }

  const renderField = (field: FormFieldConfig) => {
    if (field.type === 'hidden') {
      return null
    }

    const fieldErrors = errors[field.name] ? [errors[field.name]] : undefined

    return (
      <FormFieldRenderer
        key={field.name}
        field={field}
        value={formData[field.name]}
        onChange={handleFieldChange}
        errors={fieldErrors}
        disabled={isCreating || field.readonly}
      />
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Create New {modelName}</DialogTitle>
          <DialogDescription>
            Fill in the form below to create a new {modelName.toLowerCase()}.
          </DialogDescription>
        </DialogHeader>
        {loadingForm ? (
          <div className="py-4">Loading form...</div>
        ) : (
          <form onSubmit={(e) => { e.preventDefault(); handleCreate(); }} className="flex flex-col flex-1 min-h-0 overflow-hidden">
            <div className="flex-1 overflow-y-auto px-1">
              {Object.keys(errors).length > 0 && !Object.keys(errors).every(key => formFields.some(f => f.name === key)) && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Please correct the errors below and try again.
                  </AlertDescription>
                </Alert>
              )}
              <div className="grid gap-4 py-4">
                {formFields.map(renderField)}
              </div>
            </div>
            <DialogFooter className="mt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isCreating}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isCreating || loadingForm}
              >
                {isCreating ? 'Creating...' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}