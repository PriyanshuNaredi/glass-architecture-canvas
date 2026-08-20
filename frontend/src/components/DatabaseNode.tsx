import { memo } from 'react'
import { Handle, Position, type NodeProps, useReactFlow } from '@xyflow/react'
import { Database, Plus, Trash2 } from 'lucide-react'

export type ColumnDef = {
  name: string
  type: string
}

export type DatabaseNodeData = {
  tableName: string
  engine: string
  columns: ColumnDef[]
}

const COLUMN_TYPES = ['String', 'Integer', 'Boolean', 'UUID']

function DatabaseNode({ id, data, selected }: NodeProps) {
  const nodeData = data as unknown as DatabaseNodeData
  const columns = nodeData.columns ?? []
  const { setNodes } = useReactFlow()

  const updateData = (patch: Partial<DatabaseNodeData>) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, ...patch } } : n,
      ),
    )
  }

  const updateColumn = (index: number, patch: Partial<ColumnDef>) => {
    updateData({
      columns: columns.map((c, i) => (i === index ? { ...c, ...patch } : c)),
    })
  }

  const addColumn = () => {
    updateData({ columns: [...columns, { name: '', type: 'String' }] })
  }

  const removeColumn = (index: number) => {
    updateData({ columns: columns.filter((_, i) => i !== index) })
  }

  return (
    <div className={`glass-node ${selected ? 'selected' : ''}`}>
      <div className="flex items-center gap-3 px-4 pt-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/20 shadow-glow-emerald">
          <Database className="h-5 w-5 text-emerald-300" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-300/80">
            Database
          </p>
          <p className="text-[10px] text-white/40">{nodeData.engine || 'postgres'}</p>
        </div>
      </div>

      <div className="nodrag nopan flex flex-col gap-1.5 px-4 pb-3 pt-2">
        <label className="text-[10px] uppercase tracking-wider text-white/40">
          Table Name
        </label>
        <input
          className="glass-input"
          value={nodeData.tableName || ''}
          placeholder="users"
          onChange={(e) => updateData({ tableName: e.target.value })}
        />

        <div className="mt-1 flex items-center justify-between">
          <label className="text-[10px] uppercase tracking-wider text-white/40">
            Columns
          </label>
          <button onClick={addColumn} className="glass-mini-btn">
            <Plus className="h-3 w-3" />
            Add Column
          </button>
        </div>

        {columns.length > 0 && (
          <div className="nowheel glass-scroll flex max-h-36 flex-col gap-1.5 overflow-y-auto pr-1">
            {columns.map((col, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <input
                  className="glass-input flex-1"
                  value={col.name}
                  placeholder="email"
                  onChange={(e) => updateColumn(i, { name: e.target.value })}
                />
                <select
                  className="glass-select w-[88px]"
                  value={col.type}
                  onChange={(e) => updateColumn(i, { type: e.target.value })}
                >
                  {COLUMN_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => removeColumn(i)}
                  className="shrink-0 text-white/30 transition-colors hover:text-rose-400"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <Handle type="target" position={Position.Left} className="!-left-[6px]" />
      <Handle type="source" position={Position.Right} className="!-right-[6px]" />
    </div>
  )
}

export default memo(DatabaseNode)
