import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"

export interface FormFieldConfig {
  name: string
  label: string
  type?: string
  widget?: string
  required?: boolean
  choices?: Array<{ value: string; label: string }>
  help_text?: string
  default?: any
  readonly?: boolean
}

interface FormFieldRendererProps {
  field: FormFieldConfig
  value: any
  onChange: (fieldName: string, value: any) => void
  errors?: string[]
  disabled?: boolean
}

export function FormFieldRenderer({
  field,
  value,
  onChange,
  errors,
  disabled = false
}: FormFieldRendererProps) {
  // Determine the actual value to display
  let displayValue = value
  let selectValue = value
  
  // Handle foreign key objects
  if (value && typeof value === 'object') {
    if ('id' in value) {
      selectValue = String(value.id)
      displayValue = 'name' in value ? String(value.name) : String(value.id)
    }
  } else if (value !== null && value !== undefined) {
    displayValue = String(value)
    selectValue = String(value)
  } else {
    displayValue = ''
    selectValue = ''
  }

  // Determine the widget type
  const widgetType = field.widget || field.type || 'text'
  const hasError = errors && errors.length > 0

  const renderWidget = () => {
    // Handle Select widget or select type
    if (widgetType === 'Select' || widgetType === 'select') {
      return (
        <Select
          value={selectValue}
          onValueChange={(newValue) => onChange(field.name, newValue)}
          disabled={disabled || field.readonly}
        >
          <SelectTrigger className={hasError ? 'border-red-500' : ''}>
            <SelectValue placeholder={`Select ${field.label.toLowerCase()}...`} />
          </SelectTrigger>
          <SelectContent>
            {field.choices?.filter(choice => 
              choice.value !== '' && choice.value !== null && choice.value !== undefined
            ).map((choice) => (
              <SelectItem key={choice.value} value={choice.value}>
                {choice.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )
    }

    // Handle Textarea widget
    if (widgetType === 'Textarea' || widgetType === 'textarea') {
      return (
        <Textarea
          id={field.name}
          value={displayValue}
          onChange={(e) => onChange(field.name, e.target.value)}
          className={hasError ? 'border-red-500' : ''}
          rows={4}
          disabled={disabled || field.readonly}
        />
      )
    }

    // Handle checkbox type
    if (widgetType === 'checkbox') {
      return (
        <div className="flex items-center space-x-2">
          <Checkbox
            id={field.name}
            checked={!!value}
            onCheckedChange={(checked) => onChange(field.name, checked)}
            disabled={disabled || field.readonly}
          />
          <label
            htmlFor={field.name}
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            {field.label}
          </label>
        </div>
      )
    }

    // Handle date input
    if (widgetType === 'date') {
      return (
        <Input
          id={field.name}
          type="date"
          value={displayValue}
          onChange={(e) => onChange(field.name, e.target.value)}
          className={hasError ? 'border-red-500' : ''}
          disabled={disabled || field.readonly}
        />
      )
    }

    // Handle datetime-local input
    if (widgetType === 'datetime-local') {
      return (
        <Input
          id={field.name}
          type="datetime-local"
          value={displayValue}
          onChange={(e) => onChange(field.name, e.target.value)}
          className={hasError ? 'border-red-500' : ''}
          disabled={disabled || field.readonly}
        />
      )
    }

    // Handle number input
    if (widgetType === 'number') {
      return (
        <Input
          id={field.name}
          type="number"
          value={displayValue}
          onChange={(e) => onChange(field.name, e.target.value)}
          className={hasError ? 'border-red-500' : ''}
          disabled={disabled || field.readonly}
        />
      )
    }

    // Handle email input
    if (widgetType === 'email') {
      return (
        <Input
          id={field.name}
          type="email"
          value={displayValue}
          onChange={(e) => onChange(field.name, e.target.value)}
          className={hasError ? 'border-red-500' : ''}
          disabled={disabled || field.readonly}
        />
      )
    }

    // Handle url input
    if (widgetType === 'url') {
      return (
        <Input
          id={field.name}
          type="url"
          value={displayValue}
          onChange={(e) => onChange(field.name, e.target.value)}
          className={hasError ? 'border-red-500' : ''}
          disabled={disabled || field.readonly}
        />
      )
    }

    // Default to text input
    return (
      <Input
        id={field.name}
        type="text"
        value={displayValue}
        onChange={(e) => onChange(field.name, e.target.value)}
        className={hasError ? 'border-red-500' : ''}
        disabled={disabled || field.readonly}
      />
    )
  }

  // Special case for checkbox - render differently
  if (widgetType === 'checkbox') {
    return (
      <div className="grid grid-cols-4 items-center gap-4">
        <div className="col-span-1"></div>
        <div className="col-span-3">
          {renderWidget()}
          {field.help_text && (
            <p className="mt-1 text-sm text-gray-500">{field.help_text}</p>
          )}
          {errors?.map((error, index) => (
            <p key={index} className="mt-1 text-sm text-red-600">{error}</p>
          ))}
        </div>
      </div>
    )
  }

  // Default grid layout for CreateRecordDialog
  return (
    <div className="grid grid-cols-4 items-center gap-4">
      <Label htmlFor={field.name} className="text-right">
        {field.label}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </Label>
      <div className="col-span-3">
        {renderWidget()}
        {field.help_text && (
          <p className="mt-1 text-sm text-gray-500">{field.help_text}</p>
        )}
        {errors?.map((error, index) => (
          <p key={index} className="mt-1 text-sm text-red-600">{error}</p>
        ))}
      </div>
    </div>
  )
}

