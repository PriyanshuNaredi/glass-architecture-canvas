import { useCallback, useRef, useState } from 'react'
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
  type Node,
  type NodeTypes,
} from '@xyflow/react'
import { Sparkles, Database, Server, KeyRound, Loader2 } from 'lucide-react'
import DatabaseNode from './components/DatabaseNode'
import APIEndpointNode from './components/APIEndpointNode'
import AuthNode from './components/AuthNode'

const nodeTypes: NodeTypes = {
  databaseNode: DatabaseNode,
  apiEndpointNode: APIEndpointNode,
  authNode: AuthNode,
}

const initialNodes: Node[] = [
  {
    id: 'db-1',
    type: 'databaseNode',
    position: { x: 500, y: 200 },
    data: {
      tableName: 'users',
      engine: 'postgres',
      columns: [
        { name: 'email', type: 'String' },
        { name: 'age', type: 'Integer' },
      ],
    },
  },
  {
    id: 'api-1',
    type: 'apiEndpointNode',
    position: { x: 100, y: 200 },
    data: { method: 'GET', path: '/api/v1/users' },
  },
]

const initialEdges: Edge[] = [
  {
    id: 'e-api1-db1',
    source: 'api-1',
    target: 'db-1',
    animated: true,
  },
]

let idCounter = 2

function getId(prefix: string) {
  return `${prefix}-${idCounter++}`
}

const sidebarItems = [
  {
    type: 'databaseNode',
    label: 'Database Table',
    icon: Database,
    color: 'text-emerald-300',
    data: { tableName: 'new_table', engine: 'postgres', columns: [] },
  },
  {
    type: 'apiEndpointNode',
    label: 'API Endpoint',
    icon: Server,
    color: 'text-cyan-300',
    data: { method: 'GET', path: '/items' },
  },
  {
    type: 'authNode',
    label: 'Auth Provider',
    icon: KeyRound,
    color: 'text-violet-300',
    data: { strategy: 'jwt', provider: 'self-hosted' },
  },
]

export default function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [generating, setGenerating] = useState(false)
  const reactFlowWrapper = useRef<HTMLDivElement>(null)

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, animated: true }, eds))
    },
    [setEdges],
  )

  const onDragStart = (event: React.DragEvent, itemType: (typeof sidebarItems)[0]) => {
    event.dataTransfer.setData('application/glass-node', JSON.stringify(itemType))
    event.dataTransfer.effectAllowed = 'move'
  }

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      const raw = event.dataTransfer.getData('application/glass-node')
      if (!raw) return

      const item = JSON.parse(raw)
      const bounds = reactFlowWrapper.current?.getBoundingClientRect()
      if (!bounds) return

      const position = {
        x: event.clientX - bounds.left - 100,
        y: event.clientY - bounds.top - 30,
      }

      const newNode: Node = {
        id: getId(item.type.replace('Node', '')),
        type: item.type,
        position,
        data: item.data,
      }

      setNodes((nds) => [...nds, newNode])
    },
    [setNodes],
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const payload = {
        nodes: nodes.map((n) => ({
          id: n.id,
          type: n.type,
          position: n.position,
          data: n.data,
        })),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
        })),
      }

      const response = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const err = await response.json()
        const details = Array.isArray(err.details) && err.details.length
          ? `\n\n${err.details.map((d: string) => `• ${d}`).join('\n')}`
          : ''
        alert(`Generation failed: ${err.error || response.statusText}${details}`)
        return
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'glass-backend.zip'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert('Could not reach the Glass backend. Is it running on port 8001?')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="flex h-screen w-screen bg-charcoal">
      {/* Sidebar */}
      <aside className="z-10 flex w-64 flex-col border-r border-white/10 bg-black/40 p-5 backdrop-blur-xl">
        <div className="mb-8">
          <h1 className="text-xl font-bold tracking-tight text-white">
            <span className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              Glass
            </span>
          </h1>
          <p className="mt-1 text-xs text-white/40">
            Drag components onto the canvas
          </p>
        </div>

        <div className="flex flex-col gap-3">
          {sidebarItems.map((item) => (
            <div
              key={item.type}
              className="sidebar-item"
              draggable
              onDragStart={(e) => onDragStart(e, item)}
            >
              <item.icon className={`h-5 w-5 ${item.color}`} />
              <span className="text-sm text-white/80">{item.label}</span>
            </div>
          ))}
        </div>

        <div className="mt-auto rounded-lg border border-white/5 bg-white/5 p-3">
          <p className="text-[10px] leading-relaxed text-white/30">
            Connect endpoints to databases with wires. Hit Generate to compile
            your architecture into a downloadable backend.
          </p>
        </div>
      </aside>

      {/* Canvas */}
      <div className="relative flex-1" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          fitView
          proOptions={{ hideAttribution: true }}
          defaultEdgeOptions={{ animated: true }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={24}
            size={1.5}
            color="rgba(99, 102, 241, 0.25)"
          />
          <Controls
            className="!border-white/10 !bg-white/5 !backdrop-blur-md [&>button]:!border-white/10 [&>button]:!bg-transparent [&>button]:!text-white/60 [&>button:hover]:!bg-white/10"
          />
          <MiniMap
            className="!bg-black/60 !backdrop-blur-md"
            nodeColor="rgba(99, 102, 241, 0.6)"
            maskColor="rgba(0, 0, 0, 0.7)"
          />
        </ReactFlow>

        {/* Floating action bar */}
        <div className="absolute bottom-6 left-1/2 z-20 -translate-x-1/2">
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="btn-generate flex items-center gap-2 rounded-full border border-indigo-400/40 bg-indigo-600/80 px-6 py-3 text-sm font-semibold text-white backdrop-blur-md transition-all hover:bg-indigo-500/90 disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {generating ? 'Compiling…' : 'Generate Backend'}
          </button>
        </div>
      </div>
    </div>
  )
}
