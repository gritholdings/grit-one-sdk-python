/**
 * Shared context published by RecordDetail and consumed by the detail "lego"
 * components (DetailSection, DetailField, DetailGrid, DetailValue,
 * DetailRelatedTable). It exposes the record data plus RecordDetail's own field
 * and inline renderers, so a hand-authored `detail_component` gets read/edit,
 * validation, formatting and inline tables for free — the same code path the
 * default fieldsets view uses.
 */
import { createContext, useContext } from "react"
import type { ReactNode } from "react"

export interface RecordDetailContextValue {
  /** The record's current (form) values. */
  record: Record<string, unknown>
  /** True while the record is in edit mode. */
  isEditing: boolean
  /**
   * Render a single field by name, exactly as the default detail view does.
   * Pass `editable: true` to let the field be edited; it is read-only otherwise.
   */
  renderField: (field: string, options?: { editable?: boolean }) => ReactNode
  /**
   * Render a related-model table by (lowercase) model name, e.g. "contact", or by
   * the parent's ManyToMany field name, e.g. "students".
   *
   * `fields` overrides the default columns and `title` the heading. Column
   * selection is purely local: the server already sent every field the user may
   * read, so naming one here selects among vetted data rather than requesting
   * more of it.
   */
  renderInline: (
    modelName: string,
    options?: { fields?: string[]; title?: string }
  ) => ReactNode
  /**
   * Render a related table of tasks as an activity timeline rather than a grid:
   * grouped into "Upcoming & Overdue" and month-by-month history, completable in
   * place. Reads the same inline payload as renderInline.
   */
  renderTaskTimeline: (
    modelName: string,
    options?: { title?: string }
  ) => ReactNode
}

export const RecordDetailContext = createContext<RecordDetailContextValue | null>(null)

/**
 * Access the surrounding RecordDetail's data and renderers. Must be called from
 * a component rendered inside a <RecordDetail> (i.e. within a custom
 * `detail_component`).
 */
export function useRecordDetail(): RecordDetailContextValue {
  const context = useContext(RecordDetailContext)
  if (!context) {
    throw new Error(
      "useRecordDetail must be used within a <RecordDetail>. " +
      "Wrap your detail_component's slot components in <RecordDetail>."
    )
  }
  return context
}
