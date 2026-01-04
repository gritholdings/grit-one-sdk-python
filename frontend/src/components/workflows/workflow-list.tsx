import { useEffect, useState } from "react"
import { AppSidebar } from "@/components/app-sidebar"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { apiClient } from "@/chat/lib/api-client"
import { Loader2 } from "lucide-react"


interface Workflow {
  id: string
  name: string
  node_count: number
  edge_count: number
}

interface WorkflowListResponse {
  workflows: Workflow[]
}

interface AppWorkflowListProps {
  appConfigurations?: string | Record<string, unknown>
}

export default function AppWorkflowList({ appConfigurations }: AppWorkflowListProps) {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchWorkflows() {
      try {
        const response = await apiClient.get<WorkflowListResponse>('/api/workflows/')
        setWorkflows(response.data.workflows)
      } catch (err) {
        setError('Failed to load workflows')
        console.error('Error fetching workflows:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchWorkflows()
  }, [])

  return (
    <SidebarProvider>
      <AppSidebar appConfigurations={appConfigurations} />
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
                    Workflows
                  </BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
          <div className="ml-auto px-3">
            <NavActions />
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 px-4 py-10">
          <Card>
            <CardHeader>
              <CardTitle>All Workflows</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : error ? (
                <div className="text-center py-8 text-destructive">{error}</div>
              ) : workflows.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No workflows configured
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead className="text-right">Nodes</TableHead>
                      <TableHead className="text-right">Edges</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {workflows.map((workflow) => (
                      <TableRow key={workflow.id}>
                        <TableCell>
                          <a
                            href={`/workflows/${workflow.id}/`}
                            className="font-medium text-primary hover:underline"
                          >
                            {workflow.name}
                          </a>
                        </TableCell>
                        <TableCell className="text-right">
                          {workflow.node_count}
                        </TableCell>
                        <TableCell className="text-right">
                          {workflow.edge_count}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
