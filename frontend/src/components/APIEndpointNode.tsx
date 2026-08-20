import { memo } from 'react'
import { Handle, Position, type NodeProps, useReactFlow } from '@xyflow/react'
import { Server } from 'lucide-react'

export type APIEndpointNodeData = {
  method: string
  path: string
}

const METHODS = ['GET', 'POST', 'PUT', 'DELETE']

const methodBadge: Record<string, string> = {
  GET: 'text-cyan-300 bg-cyan-500/20',
  POST: 'text-indigo-300 bg-indigo-500/20',
  PUT: 'text-amber-300 bg-amber-500/20',
  DELETE: 'text-rose-300 bg-rose-500/20',
}

function APIEndpointNode({ id, data, selected }: NodeProps) {
  const nodeData = data as unknown as APIEndpointNodeData
  const method = (nodeData.method || 'GET').toUpperCase()
  const { setNodes } = useReactFlow()

  const updateData = (patch: Partial<APIEndpointNodeData>) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, ...patch } } : n,
      ),
    )
  }

  return (
    <div className={`glass-node ${selected ? 'selected' : ''}`}>
      <div className="flex items-center gap-3 px-4 pt-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/20 shadow-glow-cyan">
          <Server className="h-5 w-5 text-cyan-300" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-cyan-300/80">
            Endpoint
          </p>
          <span
            className={`mt-0.5 inline-block rounded px-1.5 py-0.5 text-[10px] font-bold ${methodBadge[method] || methodBadge.GET}`}
          >
            {method}
          </span>
        </div>
      </div>

      <div className="nodrag nopan flex flex-col gap-1.5 px-4 pb-3 pt-2">
        <label className="text-[10px] uppercase tracking-wider text-white/40">
          Method
        </label>
        <select
          className="glass-select"
          value={method}
          onChange={(e) => updateData({ method: e.target.value })}
        >
          {METHODS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>

        <label className="mt-1 text-[10px] uppercase tracking-wider text-white/40">
          Route
        </label>
        <input
          className="glass-input"
          value={nodeData.path || ''}
          placeholder="/api/v1/users"
          onChange={(e) => updateData({ path: e.target.value })}
        />
      </div>

      <Handle type="target" position={Position.Left} className="!-left-[6px]" />
      <Handle type="source" position={Position.Right} className="!-right-[6px]" />
    </div>
  )
}

export default memo(APIEndpointNode)
