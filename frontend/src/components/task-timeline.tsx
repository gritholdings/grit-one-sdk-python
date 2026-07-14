/**
 * Activity timeline for a record's tasks — the specialized alternative to the
 * generic related table, placed with <DetailTaskTimeline inline="task" />.
 *
 * Tasks are grouped into "Upcoming & Overdue" plus month-by-month history (see
 * lib/task-timeline.ts for the rules). Rows can be completed in place, expanded for
 * their description, and edited or deleted.
 *
 * Writes go straight to the task's own record URLs, which the server templates into
 * the inline payload as `url_templates`. They must be the app-prefixed ones: the
 * legacy /r/<model>/... paths are redirects, and a browser turns a redirected POST
 * into a GET.
 */
import { useState } from "react"
import {
  ChevronDown,
  ChevronRight,
  Flag,
  ListChecks,
  MoreHorizontal,
  Plus,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import {
  buildTimelineSections,
  formatDueLabel,
  isOverdue,
  isTaskClosed,
  parseDue,
  statusKeyFor,
} from "@/lib/task-timeline"
import type { FieldChoices, TimelineTask } from "@/lib/task-timeline"

export interface TaskTimelineProps {
  /** Card heading, defaults to the inline's plural verbose name. */
  title: string
  tasks: TimelineTask[]
  /** Per-field choice groups, used to tell an open task from a closed one. */
  choices?: FieldChoices
  /** `{id}`-templated record URLs for a task row. */
  urlTemplates?: { view?: string; update?: string; delete?: string }
  canDelete?: boolean
  /** True while the *parent* record is being edited; writes are held back. */
  disabled?: boolean
  /** Opens RecordDetail's create dialog, pre-filled with the generic FK. */
  onCreate?: () => void
  /** Merge a saved change back into the parent's inline state. */
  onTaskChange: (taskId: string, changes: Partial<TimelineTask>) => void
  onTaskDelete: (taskId: string) => void
}

function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null
  }
  return null
}

function buildUrl(template: string | undefined, id: string): string | undefined {
  return template ? template.replace('{id}', id) : undefined
}

export default function TaskTimeline({
  title,
  tasks,
  choices,
  urlTemplates,
  canDelete = true,
  disabled = false,
  onCreate,
  onTaskChange,
  onTaskDelete,
}: TaskTimelineProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [pending, setPending] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)

  // Recomputed each render so a task that was just completed moves out of
  // "Upcoming & Overdue" and into its month section without a page reload.
  const now = new Date()
  const sections = buildTimelineSections(tasks, now, choices)

  const toggleIn = (set: Set<string>, key: string) => {
    const next = new Set(set)
    if (next.has(key)) {
      next.delete(key)
    } else {
      next.add(key)
    }
    return next
  }

  const markPending = (id: string, isPending: boolean) =>
    setPending(prev => {
      const next = new Set(prev)
      if (isPending) {
        next.add(id)
      } else {
        next.delete(id)
      }
      return next
    })

  const postTo = async (url: string, body?: FormData): Promise<Response> =>
    fetch(url, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
      body,
      credentials: 'same-origin',
    })

  const handleToggleComplete = async (task: TimelineTask, closed: boolean) => {
    const updateUrl = buildUrl(urlTemplates?.update, task.id)
    const status = statusKeyFor(closed, choices)

    // No status vocabulary means no way to express "done" — leave the record alone
    // rather than guessing at a value the backend would reject.
    if (!updateUrl || !status) {
      setError('This task cannot be completed from here.')
      return
    }

    const previousStatus = task.status
    setError(null)
    markPending(task.id, true)
    onTaskChange(task.id, { status })

    try {
      const body = new FormData()
      body.append('status', status)
      const response = await postTo(updateUrl, body)
      const result = response.ok ? await response.json() : null

      if (!result?.success) {
        onTaskChange(task.id, { status: previousStatus })
        setError('Could not update the task. Please try again.')
      }
    } catch {
      onTaskChange(task.id, { status: previousStatus })
      setError('Could not update the task. Please try again.')
    } finally {
      markPending(task.id, false)
    }
  }

  const handleDelete = async (task: TimelineTask) => {
    const deleteUrl = buildUrl(urlTemplates?.delete, task.id)
    if (!deleteUrl || !window.confirm(`Delete "${task.title}"?`)) return

    setError(null)
    markPending(task.id, true)

    try {
      const response = await postTo(deleteUrl)
      if (response.ok) {
        onTaskDelete(task.id)
      } else {
        setError('Could not delete the task. Please try again.')
      }
    } catch {
      setError('Could not delete the task. Please try again.')
    } finally {
      markPending(task.id, false)
    }
  }

  const renderRow = (task: TimelineTask) => {
    const closed = isTaskClosed(task, choices)
    const overdue = isOverdue(task, now, choices)
    const due = parseDue(task)
    const viewUrl = buildUrl(urlTemplates?.view, task.id)
    const isExpanded = expanded.has(task.id)
    const isPending = pending.has(task.id)

    return (
      <div key={task.id} className={cn('flex gap-2 px-4 sm:px-6', isPending && 'opacity-50')}>
        {/* Expand toggle, hidden when there is nothing more to show. */}
        <button
          type="button"
          aria-label={isExpanded ? 'Collapse task' : 'Expand task'}
          onClick={() => setExpanded(prev => toggleIn(prev, task.id))}
          className={cn(
            'mt-3 h-5 w-5 shrink-0 text-gray-400 hover:text-gray-600',
            !task.description && 'invisible'
          )}
        >
          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>

        {/* Icon plus the connector line running down the timeline. */}
        <div className="flex shrink-0 flex-col items-center">
          <span className="mt-2 flex h-7 w-7 items-center justify-center rounded bg-green-600 text-white">
            <ListChecks className="h-4 w-4" />
          </span>
          <span className="w-px flex-1 bg-green-600" aria-hidden="true" />
        </div>

        <div className="min-w-0 flex-1 py-2">
          <div className="flex items-center gap-2">
            <Checkbox
              checked={closed}
              disabled={disabled || isPending}
              aria-label={`Mark "${task.title}" complete`}
              onCheckedChange={value => handleToggleComplete(task, value === true)}
            />
            {viewUrl ? (
              <a
                href={viewUrl}
                className={cn(
                  'truncate text-sm font-medium text-blue-600 hover:underline',
                  closed && 'text-gray-500 line-through'
                )}
              >
                {task.title}
              </a>
            ) : (
              <span className="truncate text-sm font-medium text-gray-900">{task.title}</span>
            )}
            {task.is_high_priority && (
              <Flag
                className="h-4 w-4 shrink-0 fill-red-600 text-red-600"
                aria-label="High priority"
              />
            )}

            <div className="ml-auto flex shrink-0 items-center gap-2">
              <span className={cn('text-sm text-gray-500', overdue && 'font-medium text-red-600')}>
                {due ? formatDueLabel(due, now) : 'No due date'}
              </span>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon" className="h-6 w-6" disabled={disabled}>
                    <MoreHorizontal className="h-4 w-4" />
                    <span className="sr-only">Task actions</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {viewUrl && (
                    <DropdownMenuItem asChild>
                      <a href={viewUrl}>Edit</a>
                    </DropdownMenuItem>
                  )}
                  {canDelete && (
                    <DropdownMenuItem
                      className="text-red-600 focus:text-red-600"
                      onSelect={() => handleDelete(task)}
                    >
                      Delete
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          <p className="mt-1 text-sm text-gray-500">
            {closed ? 'You had a task' : 'You have an upcoming task'}
          </p>

          {isExpanded && task.description && (
            <p className="mt-2 whitespace-pre-wrap text-sm text-gray-700">{task.description}</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white shadow sm:rounded-lg mb-6">
      <div className="px-4 py-5 sm:px-6 flex justify-between items-center">
        <h3 className="text-lg font-medium leading-6 text-gray-900">{title}</h3>
        {onCreate && (
          <Button size="sm" variant="outline" onClick={onCreate} disabled={disabled}>
            <Plus className="h-4 w-4 mr-1" />
            New
          </Button>
        )}
      </div>

      {error && (
        <div className="border-t border-gray-200 px-4 py-3 sm:px-6 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="border-t border-gray-200">
        {sections.length === 0 ? (
          <div className="px-4 py-5 sm:px-6 text-sm text-gray-500">No {title.toLowerCase()} found.</div>
        ) : (
          sections.map(section => {
            const isCollapsed = collapsed.has(section.key)
            return (
              <div key={section.key}>
                <button
                  type="button"
                  onClick={() => setCollapsed(prev => toggleIn(prev, section.key))}
                  className="flex w-full items-center gap-2 bg-gray-50 px-4 py-2 sm:px-6 text-left"
                >
                  {isCollapsed ? (
                    <ChevronRight className="h-4 w-4 text-gray-500" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-gray-500" />
                  )}
                  <span className="text-sm font-semibold text-gray-900">{section.title}</span>
                  {section.badge && (
                    <span className="ml-auto text-sm font-semibold text-gray-900">
                      {section.badge}
                    </span>
                  )}
                </button>
                {!isCollapsed && <div className="py-1">{section.tasks.map(renderRow)}</div>}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
