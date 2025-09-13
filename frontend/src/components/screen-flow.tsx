import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { getCsrfToken } from '@/lib/cookies';

export interface ScreenFlowStep {
  field: string;
  label: string;
  widget: 'TextInput' | 'Textarea';
  helpText?: string;
  required?: boolean;
  placeholder?: string;
}

export interface ScreenFlowConfig {
  entity: string;
  createEndpoint: string;
  updateEndpoint: string;
  steps: ScreenFlowStep[];
  onComplete: (entityId: string) => void;
  existingRecord?: Record<string, unknown>;
}

interface ScreenFlowProps {
  config: ScreenFlowConfig;
  open: boolean;
  onClose: () => void;
}

export function ScreenFlow({ config, open, onClose }: ScreenFlowProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [entityId, setEntityId] = useState<string | null>(config.existingRecord?.id ? String(config.existingRecord.id) : null);
  const [values, setValues] = useState<Record<string, string>>(() => {
    if (config.existingRecord) {
      const initialValues: Record<string, string> = {};
      config.steps.forEach(step => {
        if (config.existingRecord?.[step.field] !== undefined) {
          initialValues[step.field] = String(config.existingRecord[step.field]);
        }
      });
      return initialValues;
    }
    return {};
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const currentStepConfig = config.steps[currentStep];
  const isLastStep = currentStep === config.steps.length - 1;



  const handleStart = async () => {
    setLoading(true);
    setErrors({});

    try {
      const csrfToken = getCsrfToken();
      console.log('CSRF Token:', csrfToken ? 'Found' : 'Not found');
      console.log('Creating course at:', config.createEndpoint);
      
      const response = await fetch(config.createEndpoint, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'include',
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        // Handle non-200 responses
        let errorMessage = `Server error: ${response.status}`;
        try {
          const errorData = await response.json();
          console.error('Server error response:', errorData);
          errorMessage = errorData.error || errorData.detail || errorMessage;
        } catch (parseError) {
          console.error('Could not parse error response:', parseError);
        }
        
        if (response.status === 403) {
          setErrors({ general: errorMessage || 'You do not have permission to create courses.' });
        } else if (response.status === 401) {
          setErrors({ general: 'You must be logged in to create courses.' });
        } else {
          setErrors({ general: errorMessage });
        }
        return;
      }

      const data = await response.json();
      console.log('Create response:', data);

      if (data.success) {
        setEntityId(data.course_id);
      } else {
        setErrors({ general: data.error || 'Failed to create entity' });
      }
    } catch (error) {
      console.error('Error creating course - Network or parsing error:', error);
      setErrors({ general: `Network error: ${error instanceof Error ? error.message : 'Please check your connection and try again.'}` });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAndNext = async () => {
    if (!entityId) return;

    const currentValue = values[currentStepConfig.field] || '';
    
    // Basic validation
    if (currentStepConfig.required && !currentValue.trim()) {
      setErrors({ [currentStepConfig.field]: `${currentStepConfig.label} is required` });
      return;
    }

    setLoading(true);
    setErrors({});

    try {
      const formData = new FormData();
      // Send all accumulated values including the current field
      Object.entries(values).forEach(([key, val]) => {
        if (val !== undefined && val !== '') {
          formData.append(key, val);
        }
      });
      // Ensure current field is included (even if empty for optional fields)
      formData.append(currentStepConfig.field, currentValue);

      const response = await fetch(config.updateEndpoint.replace('{id}', entityId), {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
        },
        body: formData,
        credentials: 'same-origin',
      });

      const data = await response.json();

      if (data.success) {
        if (isLastStep) {
          config.onComplete(entityId);
          handleClose();
        } else {
          setCurrentStep(currentStep + 1);
        }
      } else {
        // Handle field-specific errors
        if (data.errors) {
          setErrors(data.errors);
        } else {
          setErrors({ general: 'Failed to save. Please try again.' });
        }
      }
    } catch (updateError) {
      console.error('Error updating course field:', updateError);
      setErrors({ general: 'An error occurred. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleClose = () => {
    // Reset state
    setCurrentStep(0);
    setEntityId(null);
    setValues({});
    setErrors({});
    setLoading(false);
    onClose();
  };

  const renderField = () => {
    const value = values[currentStepConfig.field] || '';
    const error = errors[currentStepConfig.field];

    const fieldProps = {
      id: currentStepConfig.field,
      value,
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setValues({ ...values, [currentStepConfig.field]: e.target.value });
        // Clear error when user starts typing
        if (error) {
          setErrors({ ...errors, [currentStepConfig.field]: '' });
        }
      },
      placeholder: currentStepConfig.placeholder,
      disabled: loading,
      className: error ? 'border-red-500' : '',
    };

    if (currentStepConfig.widget === 'Textarea') {
      return <Textarea {...fieldProps} rows={4} />;
    }
    return <Input {...fieldProps} type="text" />;
  };

  // Start the flow automatically when mounted if no entityId (for new entities)
  // Skip if editing an existing record
  useEffect(() => {
    if (open && !entityId && !config.existingRecord) {
      handleStart();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, entityId, config.existingRecord]);

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-semibold">{config.existingRecord ? `Edit ${config.entity}` : `Create New ${config.entity}`}</h2>
            <span className="text-sm text-muted-foreground">
              Step {currentStep + 1} of {config.steps.length}
            </span>
          </div>

          {errors.general && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{errors.general}</AlertDescription>
            </Alert>
          )}

          {(entityId || config.existingRecord) && currentStepConfig && (
            <div className="space-y-6">
              <div className="py-3 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-4">
                <Label htmlFor={currentStepConfig.field} className="text-sm font-medium text-gray-500 sm:pt-1.5">
                  {currentStepConfig.label || currentStepConfig.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  {currentStepConfig.required && <span className="text-red-500 ml-1">*</span>}
                </Label>
                <div className="mt-1 sm:col-span-2 sm:mt-0">
                  {renderField()}
                  
                  {currentStepConfig.helpText && (
                    <p className="mt-1 text-sm text-gray-500">{currentStepConfig.helpText}</p>
                  )}
                  
                  {errors[currentStepConfig.field] && (
                    <p className="mt-1 text-sm text-red-600">{errors[currentStepConfig.field]}</p>
                  )}
                </div>
              </div>

              <div className="flex justify-between pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={handlePrevious}
                  disabled={currentStep === 0 || loading}
                >
                  Previous
                </Button>
                
                <div className="space-x-2">
                  <Button variant="outline" onClick={handleClose} disabled={loading}>
                    Cancel
                  </Button>
                  <Button onClick={handleSaveAndNext} disabled={loading}>
                    {loading ? 'Saving...' : isLastStep ? 'Complete' : 'Save & Next'}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {!entityId && !config.existingRecord && loading && (
            <div className="text-center py-8">
              <p className="text-muted-foreground">Initializing...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}