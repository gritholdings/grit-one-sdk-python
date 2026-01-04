import { useEffect, useState, useMemo } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { NavActions } from "@/components/nav-actions"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { apiClient } from "@/chat/lib/api-client"
import { Loader2, Play, CheckCircle2, XCircle, ArrowRight } from "lucide-react"


interface WorkflowNode {
  name: string
  position: { x: number; y: number }
  type: string
  type_version?: number
  py_code?: string
}

interface WorkflowEdge {
  source_node_id: string
  target_node_id: string
}

interface WorkflowConfig {
  meta: { name: string }
  nodes: Record<string, WorkflowNode>
  edges: Record<string, WorkflowEdge>
}

// =============================================================================
// Workflow Graph Component
// =============================================================================

interface WorkflowGraphProps {
  nodes: Record<string, WorkflowNode>
  edges: Record<string, WorkflowEdge>
}

function WorkflowGraph({ nodes, edges }: WorkflowGraphProps) {
  // Compute topological order of nodes for vertical layout
  const orderedNodes = useMemo(() => {
    const nodeIds = Object.keys(nodes)
    const edgeList = Object.values(edges)

    // Build adjacency list and in-degree count
    const inDegree: Record<string, number> = {}
    const adjacency: Record<string, string[]> = {}

    nodeIds.forEach(id => {
      inDegree[id] = 0
      adjacency[id] = []
    })

    edgeList.forEach(edge => {
      if (adjacency[edge.source_node_id]) {
        adjacency[edge.source_node_id].push(edge.target_node_id)
      }
      if (inDegree[edge.target_node_id] !== undefined) {
        inDegree[edge.target_node_id]++
      }
    })

    // Kahn's algorithm for topological sort
    const queue: string[] = nodeIds.filter(id => inDegree[id] === 0)
    const result: string[] = []

    while (queue.length > 0) {
      const current = queue.shift()!
      result.push(current)

      adjacency[current]?.forEach(neighbor => {
        inDegree[neighbor]--
        if (inDegree[neighbor] === 0) {
          queue.push(neighbor)
        }
      })
    }

    // Add any remaining nodes (in case of cycles or disconnected nodes)
    nodeIds.forEach(id => {
      if (!result.includes(id)) {
        result.push(id)
      }
    })

    return result
  }, [nodes, edges])

  // Graph layout constants
  const nodeRadius = 28
  const verticalSpacing = 100
  const svgWidth = 300
  const svgHeight = orderedNodes.length * verticalSpacing + 80 // Extra space for lightning bolt
  const centerX = svgWidth / 2

  // Check if node is a trigger
  function isTrigger(nodeType: string): boolean {
    return nodeType.includes('trigger')
  }

  // Check if node is a code action
  function isCodeAction(nodeType: string): boolean {
    return nodeType.includes('code')
  }

  // Calculate node positions
  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {}
    orderedNodes.forEach((nodeId, index) => {
      positions[nodeId] = {
        x: centerX,
        y: 70 + index * verticalSpacing // Extra top space for lightning bolt
      }
    })
    return positions
  }, [orderedNodes, centerX])

  // Get short type name for display
  function getShortType(fullType: string): string {
    const parts = fullType.split('.')
    const typeName = parts[parts.length - 1]
    // Return first letter capitalized
    return typeName.charAt(0).toUpperCase()
  }

  // Determine node color based on type
  function getNodeColor(): string {
    return '#f5f5f4' // neutral light background for all nodes
  }

  return (
    <div className="flex justify-center">
      <svg
        width={svgWidth}
        height={svgHeight}
        className="overflow-visible"
      >
        {/* Draw edges first (so they appear behind nodes) */}
        {Object.entries(edges).map(([edgeId, edge]) => {
          const sourcePos = nodePositions[edge.source_node_id]
          const targetPos = nodePositions[edge.target_node_id]

          if (!sourcePos || !targetPos) return null

          return (
            <g key={edgeId}>
              {/* Edge line */}
              <line
                x1={sourcePos.x}
                y1={sourcePos.y + nodeRadius}
                x2={targetPos.x}
                y2={targetPos.y - nodeRadius}
                stroke="#94a3b8"
                strokeWidth={2}
                markerEnd="url(#arrowhead)"
              />
            </g>
          )
        })}

        {/* Arrow marker definition */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon
              points="0 0, 10 3.5, 0 7"
              fill="#94a3b8"
            />
          </marker>
        </defs>

        {/* Draw nodes */}
        {orderedNodes.map((nodeId, index) => {
          const node = nodes[nodeId]
          const pos = nodePositions[nodeId]
          const color = getNodeColor()
          const isNodeTrigger = isTrigger(node.type)

          return (
            <g key={nodeId}>
              {/* Lightning bolt for trigger nodes - centered above node */}
              {isNodeTrigger && (
                <g transform={`translate(${pos.x - 10}, ${pos.y - nodeRadius - 28})`}>
                  {/* Lightning bolt icon */}
                  <path
                    d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"
                    fill="#f97316"
                    stroke="#ea580c"
                    strokeWidth={1}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </g>
              )}
              {/* Node circle - light background with border */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={nodeRadius}
                fill={color}
                stroke="#d4d4d4"
                strokeWidth={2}
                className="drop-shadow-sm"
              />
              {/* Node content - Mouse cursor for triggers, code icon for code actions, number for others */}
              {isNodeTrigger ? (
                /* Mouse cursor icon */
                <g transform={`translate(${pos.x - 10}, ${pos.y - 12})`}>
                  <path
                    d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z"
                    fill="#6b7280"
                    stroke="#6b7280"
                    strokeWidth={1}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    transform="scale(0.9)"
                  />
                </g>
              ) : isCodeAction(node.type) ? (
                /* Code icon for code action nodes - shows <> */
                <g transform={`translate(${pos.x - 10}, ${pos.y - 10})`}>
                  <path
                    d="m18 16 4-4-4-4"
                    fill="none"
                    stroke="#6b7280"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    transform="scale(0.85)"
                  />
                  <path
                    d="m6 8-4 4 4 4"
                    fill="none"
                    stroke="#6b7280"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    transform="scale(0.85)"
                  />
                </g>
              ) : (
                /* Node number for other nodes */
                <text
                  x={pos.x}
                  y={pos.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill="#6b7280"
                  fontSize="14"
                  fontWeight="bold"
                >
                  {index + 1}
                </text>
              )}
              {/* Node label */}
              <text
                x={pos.x + nodeRadius + 12}
                y={pos.y}
                textAnchor="start"
                dominantBaseline="central"
                fill="currentColor"
                fontSize="13"
                className="font-medium"
              >
                {node.name}
              </text>
              {/* Node type indicator */}
              <text
                x={pos.x + nodeRadius + 12}
                y={pos.y + 16}
                textAnchor="start"
                dominantBaseline="central"
                fill="#6b7280"
                fontSize="11"
              >
                {getShortType(node.type)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

interface WorkflowDetailResponse {
  id: string
  config: WorkflowConfig
}

interface NodeExecutionResult {
  node_id: string
  node_name: string
  data: Record<string, unknown>
  executed_at: string
}

interface ExecutionResult {
  success: boolean
  workflow_id: string
  workflow_name: string
  wf: {
    data: Record<string, unknown>
    started_at: string
  }
  nodes: Record<string, NodeExecutionResult>
  error?: string
}

interface AppWorkflowDetailProps {
  workflowId: string
  appConfigurations?: string | Record<string, unknown>
}

export default function AppWorkflowDetail({ workflowId, appConfigurations }: AppWorkflowDetailProps) {
  const [workflow, setWorkflow] = useState<WorkflowDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [executing, setExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null)

  useEffect(() => {
    async function fetchWorkflow() {
      try {
        const response = await apiClient.get<WorkflowDetailResponse>(`/api/workflows/${workflowId}/`)
        setWorkflow(response.data)
      } catch (err) {
        setError('Failed to load workflow')
        console.error('Error fetching workflow:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchWorkflow()
  }, [workflowId])

  async function executeWorkflow() {
    setExecuting(true)
    setExecutionResult(null)
    try {
      const response = await apiClient.post<ExecutionResult>(`/api/workflows/${workflowId}/run/`)
      setExecutionResult(response.data)
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: ExecutionResult } }
      if (axiosError.response?.data) {
        setExecutionResult(axiosError.response.data)
      } else {
        setExecutionResult({
          success: false,
          workflow_id: workflowId,
          workflow_name: workflow?.config.meta.name || workflowId,
          wf: { data: {}, started_at: new Date().toISOString() },
          nodes: {},
          error: 'Failed to execute workflow'
        })
      }
    } finally {
      setExecuting(false)
    }
  }

  // Extract node type short name for display
  function getNodeTypeShortName(fullType: string): string {
    const parts = fullType.split('.')
    return parts[parts.length - 1]
  }

  if (loading) {
    return (
      <SidebarProvider>
        <AppSidebar appConfigurations={appConfigurations} />
        <SidebarInset>
          <div className="flex items-center justify-center h-screen">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </SidebarInset>
      </SidebarProvider>
    )
  }

  if (error || !workflow) {
    return (
      <SidebarProvider>
        <AppSidebar appConfigurations={appConfigurations} />
        <SidebarInset>
          <div className="flex items-center justify-center h-screen">
            <div className="text-destructive">{error || 'Workflow not found'}</div>
          </div>
        </SidebarInset>
      </SidebarProvider>
    )
  }

  const { config } = workflow
  const nodes = Object.entries(config.nodes)
  const edges = Object.entries(config.edges)

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
                  <BreadcrumbLink href="/workflows/">Workflows</BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage className="line-clamp-1">
                    {config.meta.name}
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
          {/* Workflow Header with Execute Button */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">{config.meta.name}</h1>
              <p className="text-muted-foreground">
                {nodes.length} node{nodes.length !== 1 ? 's' : ''} | {edges.length} edge{edges.length !== 1 ? 's' : ''}
              </p>
            </div>
            <Button onClick={executeWorkflow} disabled={executing} size="lg">
              {executing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Executing...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Execute
                </>
              )}
            </Button>
          </div>

          {/* Workflow Graph Visualization */}
          <Card>
            <CardHeader>
              <CardTitle>Workflow Graph</CardTitle>
              <CardDescription>
                Visual representation of the workflow flow
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="py-4">
                <WorkflowGraph nodes={config.nodes} edges={config.edges} />
              </div>
            </CardContent>
          </Card>

          {/* Execution Results */}
          {executionResult && (
            <Card className={executionResult.success ? "border-green-500" : "border-destructive"}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {executionResult.success ? (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-destructive" />
                  )}
                  Execution {executionResult.success ? 'Successful' : 'Failed'}
                </CardTitle>
                <CardDescription>
                  Started at: {new Date(executionResult.wf.started_at).toLocaleString()}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {executionResult.error && (
                  <div className="mb-4 p-3 bg-destructive/10 text-destructive rounded-md">
                    {executionResult.error}
                  </div>
                )}
                {Object.entries(executionResult.nodes).length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium">Node Execution Results:</h4>
                    {Object.entries(executionResult.nodes).map(([nodeId, nodeResult]) => (
                      <div key={nodeId} className="p-3 bg-muted rounded-md">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">{nodeResult.node_name}</span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(nodeResult.executed_at).toLocaleTimeString()}
                          </span>
                        </div>
                        {Object.keys(nodeResult.data).length > 0 && (
                          <pre className="text-xs bg-background p-2 rounded overflow-x-auto">
                            {JSON.stringify(nodeResult.data, null, 2)}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Nodes Section */}
          <Card>
            <CardHeader>
              <CardTitle>Nodes</CardTitle>
              <CardDescription>
                Workflow nodes define the steps in your workflow
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {nodes.map(([nodeId, node]) => (
                  <div key={nodeId} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{node.name}</span>
                      <span className="inline-flex items-center rounded-md bg-secondary px-2 py-1 text-xs font-medium text-secondary-foreground">
                        {getNodeTypeShortName(node.type)}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground space-y-1">
                      <div>ID: <code className="bg-muted px-1 rounded">{nodeId}</code></div>
                      <div>Type: <code className="bg-muted px-1 rounded">{node.type}</code></div>
                      {node.type_version && (
                        <div>Version: {node.type_version}</div>
                      )}
                      {node.py_code && (
                        <div className="mt-2">
                          <div className="mb-1">Code:</div>
                          <pre className="bg-muted p-2 rounded text-xs overflow-x-auto">
                            {node.py_code.trim()}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Edges Section */}
          {edges.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Edges</CardTitle>
                <CardDescription>
                  Edges define the connections between nodes
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {edges.map(([edgeId, edge]) => {
                    const sourceNode = config.nodes[edge.source_node_id]
                    const targetNode = config.nodes[edge.target_node_id]
                    return (
                      <div key={edgeId} className="flex items-center gap-2 p-3 border rounded-lg">
                        <span className="inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium">
                          {sourceNode?.name || edge.source_node_id}
                        </span>
                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                        <span className="inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium">
                          {targetNode?.name || edge.target_node_id}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
