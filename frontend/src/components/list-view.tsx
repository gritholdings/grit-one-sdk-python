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
import { DataTable } from "@/components/data-table"
import { type ColumnDef } from "@tanstack/react-table"
import { ArrowUpDown, MoreHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { FileText } from "lucide-react"
import { useMemo } from "react"


interface ColumnConfig {
  id?: string
  fieldName?: string
  label?: string
  type?: "text" | "number" | "currency" | "select" | "actions" | "link"
  sortable?: boolean
  align?: "left" | "center" | "right"
  actions?: Array<{ label: string; action: string }>
  href?: string | ((row: Record<string, unknown>) => string)
  linkText?: string | ((row: Record<string, unknown>) => string)
}

function createColumns(columnsConfig: ColumnConfig[]): ColumnDef<Record<string, unknown>>[] {
  return columnsConfig.map((config) => {
    const column: Partial<ColumnDef<Record<string, unknown>>> = {}
    
    if (config.type === "select") {
      column.id = "select"
      column.header = ({ table }) => (
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      )
      column.cell = ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      )
      column.enableSorting = false
      column.enableHiding = false
    } else if (config.type === "actions") {
      column.id = "actions"
      column.enableHiding = false
      column.cell = ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">Open menu</span>
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {config.actions?.map((action, index) => (
              <DropdownMenuItem key={index}>{action.label}</DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )
    } else {
      (column as any).accessorKey = config.fieldName || config.id
      
      if (config.sortable) {
        column.header = ({ column }) => (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {config.label}
            <ArrowUpDown />
          </Button>
        )
      } else {
        column.header = config.align === "right" 
          ? () => <div className="text-right">{config.label}</div>
          : config.label
      }
      
      if (config.type === "currency") {
        column.cell = ({ row }) => {
          const value = row.getValue(config.fieldName || config.id || "")
          const amount = parseFloat(String(value))
          const formatted = new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
          }).format(amount)
          return <div className={`font-medium ${config.align === "right" ? "text-right" : ""}`}>{formatted}</div>
        }
      } else if (config.type === "link") {
        column.cell = ({ row }) => {
          const value = row.getValue(config.fieldName || config.id || "")
          
          // Process href template
          let href = config.href || "#"
          if (typeof href === "string") {
            // Replace template variables like {id} with actual values
            href = href.replace(/\{(\w+)\}/g, (match, key) => {
              return String(row.original[key] || match)
            })
          } else if (typeof href === "function") {
            href = href(row.original)
          }
          
          // Process linkText template
          let linkText = config.linkText || String(value)
          if (typeof linkText === "string") {
            // Replace template variables like {name} with actual values
            linkText = linkText.replace(/\{(\w+)\}/g, (match, key) => {
              return String(row.original[key] || match)
            })
          } else if (typeof linkText === "function") {
            linkText = linkText(row.original)
          }
          
          return (
            <a 
              href={href}
              className={`font-bold hover:underline ${config.align === "right" ? "text-right" : ""}`}
            >
              {linkText}
            </a>
          )
        }
      } else {
        column.cell = ({ row }) => {
          const value = row.getValue(config.fieldName || config.id || "")
          return <div className={config.align === "right" ? "text-right" : ""}>{String(value)}</div>
        }
      }
    }
    
    return column as ColumnDef<Record<string, unknown>>
  })
}


type NavAction = {
  label: string
  href?: string
  icon?: React.ComponentType
}
type NavActionGroup = NavAction[]

interface ListViewProps {
  data: Record<string, unknown>[]
  columns: ColumnConfig[]
  title?: string,
  actions?: NavActionGroup[]
}

export default function ListView({
  data,
  columns,
  title = "All Records",
  actions = []
}: ListViewProps) {
  // Ensure actions is always an array
  const validActions = actions || []
  const columnDefs = useMemo(() => createColumns(columns), [columns])
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
                    {title}
                  </BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
          <div className="ml-auto px-3">
            <NavActions groups={validActions} />
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 px-4 py-10">
            <DataTable columns={columnDefs} data={data} />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
