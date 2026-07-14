/**
 * Grouping and date rules behind the task timeline (see components/task-timeline.tsx).
 *
 * Kept free of React so the rules can be reasoned about — and tested — on their own.
 *
 * Everything here works in the *browser's* timezone on purpose. The server sends
 * `due_datetime` as a tz-aware ISO string, but only the browser knows what "Tomorrow"
 * means to the person reading the page, so the server never pre-computes these labels.
 */

/** One serialized row of the `task` inline payload. */
export interface TimelineTask {
  id: string
  title?: string
  description?: string
  status?: string
  is_high_priority?: boolean
  due_datetime?: string | null
  created_at?: string | null
  [key: string]: unknown
}

/**
 * One APP_METADATA_SETTINGS['CHOICES'] group, keyed by the value stored on the
 * record. Carries the semantic flags a Django (value, label) choices tuple drops —
 * `is_closed` is the one the timeline needs.
 */
export type ChoiceGroup = Record<string, { label?: string; is_closed?: boolean }>

/** The `choices` map an inline ships when its metadata declares `field_choices`. */
export type FieldChoices = Record<string, ChoiceGroup>

export interface TimelineSection {
  /** Stable identity for React keys and open/closed state. */
  key: string
  title: string
  /** Right-aligned tag on the section header, e.g. "This Month". */
  badge?: string
  tasks: TimelineTask[]
}

export const UPCOMING_KEY = 'upcoming_overdue'
export const NO_DUE_DATE_KEY = 'no_due_date'

/**
 * Is this task done? Answered from the `task_status` choices rather than by
 * comparing against the string "completed", because the status vocabulary is
 * defined in APP_METADATA_SETTINGS and projects are free to rename it.
 *
 * Unknown or missing statuses count as open: a task the timeline cannot classify
 * is better surfaced as actionable than silently buried in history.
 */
export function isTaskClosed(task: TimelineTask, choices?: FieldChoices): boolean {
  const status = task.status
  if (!status) return false
  return choices?.status?.[status]?.is_closed === true
}

/** The status value to write when a task is checked off (or unchecked). */
export function statusKeyFor(closed: boolean, choices?: FieldChoices): string | undefined {
  const statuses = choices?.status
  if (!statuses) return undefined
  return Object.keys(statuses).find(key => (statuses[key]?.is_closed === true) === closed)
}

/** Parse `due_datetime`, tolerating null and malformed values. */
export function parseDue(task: TimelineTask): Date | null {
  if (!task.due_datetime) return null
  const date = new Date(task.due_datetime)
  return Number.isNaN(date.getTime()) ? null : date
}

/** An open task whose due date has already passed. */
export function isOverdue(task: TimelineTask, now: Date, choices?: FieldChoices): boolean {
  const due = parseDue(task)
  if (!due) return false
  return !isTaskClosed(task, choices) && due.getTime() < now.getTime()
}

/** Whole days from `now`'s calendar date to `date`'s, in local time. */
function daysFromToday(date: Date, now: Date): number {
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const MS_PER_DAY = 86_400_000
  return Math.round((startOfDay(date) - startOfDay(now)) / MS_PER_DAY)
}

/**
 * "Tomorrow" for near dates, "25-Oct" otherwise — matching how the reference
 * timeline reads. The year is appended only when it is not the current one, since
 * month sections already carry it in their heading.
 */
export function formatDueLabel(date: Date, now: Date): string {
  const offset = daysFromToday(date, now)
  if (offset === 0) return 'Today'
  if (offset === 1) return 'Tomorrow'
  if (offset === -1) return 'Yesterday'

  const day = String(date.getDate()).padStart(2, '0')
  const month = date.toLocaleString('en-US', { month: 'short' })
  const label = `${day}-${month}`
  return date.getFullYear() === now.getFullYear() ? label : `${label}-${date.getFullYear()}`
}

/** "October • 2022" */
function monthTitle(date: Date): string {
  return `${date.toLocaleString('en-US', { month: 'long' })} • ${date.getFullYear()}`
}

function monthKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

/**
 * Split tasks into the timeline's sections.
 *
 * - "Upcoming & Overdue" holds every *open* task with a due date, soonest first, so
 *   anything already past due floats to the top where it is hardest to ignore.
 * - Everything else that has a due date is history: grouped by the month it fell in,
 *   most recent month first.
 * - Tasks with no due date cannot be placed on a timeline at all, so they get their
 *   own trailing section rather than being dropped — the generic table this widget
 *   replaces did show them.
 *
 * `now` is injected rather than read from the clock so the rules stay pure.
 */
export function buildTimelineSections(
  tasks: TimelineTask[],
  now: Date,
  choices?: FieldChoices
): TimelineSection[] {
  const upcoming: TimelineTask[] = []
  const undated: TimelineTask[] = []
  const byMonth = new Map<string, { title: string; date: Date; tasks: TimelineTask[] }>()

  for (const task of tasks) {
    const due = parseDue(task)

    if (!due) {
      undated.push(task)
    } else if (!isTaskClosed(task, choices)) {
      upcoming.push(task)
    } else {
      const key = monthKey(due)
      const bucket = byMonth.get(key) || { title: monthTitle(due), date: due, tasks: [] }
      bucket.tasks.push(task)
      byMonth.set(key, bucket)
    }
  }

  const dueTime = (task: TimelineTask) => parseDue(task)?.getTime() ?? 0
  const sections: TimelineSection[] = []

  if (upcoming.length > 0) {
    sections.push({
      key: UPCOMING_KEY,
      title: 'Upcoming & Overdue',
      tasks: upcoming.sort((a, b) => dueTime(a) - dueTime(b)),
    })
  }

  const currentMonth = monthKey(now)
  for (const key of [...byMonth.keys()].sort().reverse()) {
    const bucket = byMonth.get(key)!
    sections.push({
      key,
      title: bucket.title,
      badge: key === currentMonth ? 'This Month' : undefined,
      tasks: bucket.tasks.sort((a, b) => dueTime(b) - dueTime(a)),
    })
  }

  if (undated.length > 0) {
    sections.push({ key: NO_DUE_DATE_KEY, title: 'No Due Date', tasks: undated })
  }

  return sections
}
