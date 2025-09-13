import { useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Upload, Loader2 } from 'lucide-react'

interface FileUploadButtonProps {
  fetchUrl?: string
  buttonLabel?: string
  fileFieldName?: string
  onSuccess?: (data: any) => void
  onError?: (error: string) => void
  // Support for component-based actions
  label?: string
  props?: {
    endpoint?: string
    acceptedFileTypes?: string
    maxSize?: string
    buttonText?: string
    fieldName?: string
  }
}

function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null
  }
  return null
}

export default function FileUploadButton({
  fetchUrl,
  buttonLabel = 'Upload File',
  fileFieldName = 'file',
  onSuccess,
  onError,
  label,
  props
}: FileUploadButtonProps) {
  // Use props from component-based action if provided
  const url = fetchUrl || props?.endpoint || ''
  const buttonText = label || buttonLabel || props?.buttonText || 'Upload File'
  const fieldName = fileFieldName || props?.fieldName || 'file'
  const acceptedTypes = props?.acceptedFileTypes
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [status, setStatus] = useState<{ type: 'success' | 'error' | null; message: string }>({
    type: null,
    message: ''
  })
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null
    setSelectedFile(file)
    setStatus({ type: null, message: '' })
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setStatus({ type: 'error', message: 'Please select a file first' })
      return
    }

    setIsUploading(true)
    setStatus({ type: null, message: '' })

    try {
      const csrfToken = getCookie('csrftoken')
      const formData = new FormData()
      formData.append(fieldName, selectedFile)
      if (csrfToken) {
        formData.append('csrfmiddlewaretoken', csrfToken)
      }

      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': csrfToken || ''
        }
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = 'Upload failed'
        
        try {
          const errorJson = JSON.parse(errorText)
          errorMessage = errorJson.error || errorJson.message || errorMessage
        } catch {
          errorMessage = errorText || errorMessage
        }
        
        throw new Error(errorMessage)
      }

      const data = await response.json()
      setStatus({ 
        type: 'success', 
        message: data.message || 'Upload successful' 
      })

      if (onSuccess) {
        onSuccess(data)
      }

      if (data.redirect_url) {
        setTimeout(() => {
          window.location.href = data.redirect_url
        }, 1500)
      } else {
        setTimeout(() => {
          window.location.reload()
        }, 1500)
      }

      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload error'
      setStatus({ type: 'error', message: errorMessage })
      
      if (onError) {
        onError(errorMessage)
      }
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Input
          ref={fileInputRef}
          type="file"
          accept={acceptedTypes}
          onChange={handleFileSelect}
          disabled={isUploading}
          className="flex-1"
        />
        <Button
          onClick={handleUpload}
          disabled={isUploading || !selectedFile}
          className="min-w-[120px]"
        >
          {isUploading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              {buttonText}
            </>
          )}
        </Button>
      </div>
      
      {status.type && (
        <Alert variant={status.type === 'error' ? 'destructive' : 'default'}>
          <AlertDescription>{status.message}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}