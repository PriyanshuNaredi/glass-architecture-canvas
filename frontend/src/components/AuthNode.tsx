import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { KeyRound } from 'lucide-react'

export type AuthNodeData = {
  strategy: string
  provider: string
}

function AuthNode({ data, selected }: NodeProps) {
  const nodeData = data as unknown as AuthNodeData

  return (
    <div className={`glass-node ${selected ? 'selected' : ''}`}>
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-500/20 shadow-glow">
          <KeyRound className="h-5 w-5 text-violet-300" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-violet-300/80">
            Auth
          </p>
          <p className="text-sm font-medium text-white/90">
            {(nodeData.strategy || 'jwt').toUpperCase()}
          </p>
          <p className="text-[10px] text-white/40">
            {nodeData.provider || 'self-hosted'}
          </p>
        </div>
      </div>
      <Handle
        type="target"
        position={Position.Left}
        className="!-left-[6px]"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!-right-[6px]"
      />
    </div>
  )
}

export default memo(AuthNode)
