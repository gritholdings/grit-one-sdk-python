/**
 * Prebuilt "lego" building blocks for hand-authored detail_components.
 *
 * Compose these inside a <RecordDetail> to lay out a record however you like,
 * using ordinary React + Tailwind, instead of relying on `fieldsets`. They read
 * the surrounding record's data and renderers from RecordDetailContext, so
 * fields keep their read/edit behaviour and related tables render exactly as the
 * default detail view — you only control the layout.
 *
 * Example (see app_frontend/src/account-detail.tsx):
 *   <RecordDetail {...props}>
 *     <DetailSection title="Account">
 *       <DetailGrid cols={2}>
 *         <DetailField name="name" editable />
 *         <DetailField name="owner" />
 *       </DetailGrid>
 *     </DetailSection>
 *     <DetailRelatedTable inline="contact" />
 *   </RecordDetail>
 */
import type { ReactNode } from "react"
import { useRecordDetail } from "@/components/record-detail-context"

interface DetailSectionProps {
  /** Optional card heading. */
  title?: string
  children: ReactNode
}

/** A titled card. Group DetailField / DetailGrid / DetailValue rows inside it. */
export function DetailSection({ title, children }: DetailSectionProps) {
  return (
    <div className="bg-white shadow sm:rounded-lg mb-6">
      {title && (
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg font-medium leading-6 text-gray-900">{title}</h3>
        </div>
      )}
      <div className={title ? "border-t border-gray-200" : ""}>
        <dl className="divide-y divide-gray-200 px-4 sm:px-6">{children}</dl>
      </div>
    </div>
  )
}

interface DetailFieldProps {
  /** Record field name, e.g. "name". */
  name: string
  /**
   * Let the user edit this field. Defaults to false: fields are read-only unless
   * they opt in. Only fields marked editable are saved when the record is
   * submitted. Has no effect on system fields (id, owner, created_at,
   * updated_at, metadata), which are never editable.
   */
  editable?: boolean
}

/**
 * Render one record field by name. Reuses RecordDetail's field renderer, so
 * read display, editing, validation and formatting all match the default detail
 * view — including the edit pencil, shown only when `editable` is set.
 */
export function DetailField({ name, editable = false }: DetailFieldProps) {
  const { renderField } = useRecordDetail()
  return <>{renderField(name, { editable })}</>
}

interface DetailGridProps {
  /** Number of responsive columns (defaults to 2). */
  cols?: 1 | 2 | 3
  children: ReactNode
}

/** Arrange child rows in a responsive column grid (single column on mobile). */
export function DetailGrid({ cols = 2, children }: DetailGridProps) {
  const colClass =
    cols === 3 ? "sm:grid-cols-3" : cols === 1 ? "sm:grid-cols-1" : "sm:grid-cols-2"
  return <div className={`grid grid-cols-1 ${colClass} sm:gap-x-8`}>{children}</div>
}

interface DetailValueProps {
  /** Left-hand label. */
  label: string
  /** Custom/computed read-only content (e.g. a badge, link, or formatted value). */
  children: ReactNode
}

/** A labeled row for custom or computed read-only content. */
export function DetailValue({ label, children }: DetailValueProps) {
  return (
    <div className="py-3 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-4">
      <dt className="text-sm font-medium text-gray-500 sm:pt-1.5">{label}</dt>
      <dd className="mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0">{children}</dd>
    </div>
  )
}

interface DetailRelatedTableProps {
  /**
   * Lowercase related-model name, e.g. "contact" or "opportunity". For a
   * ManyToMany relation you can also use the parent's field name, e.g.
   * "students", which beats naming the generated join model ("course_students").
   */
  inline: string
  /**
   * Columns to show. Defaults to the related model's `list_display`, falling back
   * to its `fieldsets` and then its plain fields. Any field the user is allowed to
   * read may be named here, not just the default ones.
   */
  fields?: string[]
  /** Table heading. Defaults to the related model's plural verbose name. */
  title?: string
}

/**
 * Render a related-model table at this position.
 *
 * The backend discovers the record's relations on its own, so no `inlines` need
 * be declared in metadata.py. Renders nothing if nothing is related under the
 * given name.
 */
export function DetailRelatedTable({ inline, fields, title }: DetailRelatedTableProps) {
  const { renderInline } = useRecordDetail()
  return <>{renderInline(inline, { fields, title })}</>
}

interface DetailTaskTimelineProps {
  /** Lowercase related-model name holding the tasks, e.g. "task". */
  inline: string
  /** Card heading. Defaults to the related model's plural verbose name. */
  title?: string
}

/**
 * Render a record's tasks as an activity timeline instead of a table.
 *
 * Tasks are grouped into "Upcoming & Overdue" (open tasks, soonest first, so
 * anything past due surfaces at the top) followed by month-by-month history, and
 * each row can be completed, expanded, edited or deleted in place.
 *
 * Reads the same auto-discovered payload as <DetailRelatedTable>, so it needs
 * nothing extra in metadata.py — but the related model's metadata should declare
 * `field_choices = {'status': 'task_status'}` so the timeline can tell a done task
 * from an open one without hardcoding a status value.
 */
export function DetailTaskTimeline({ inline, title }: DetailTaskTimelineProps) {
  const { renderTaskTimeline } = useRecordDetail()
  return <>{renderTaskTimeline(inline, { title })}</>
}
