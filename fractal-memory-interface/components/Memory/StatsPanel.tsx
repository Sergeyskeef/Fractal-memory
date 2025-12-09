import React from 'react';
import { MemoryStats } from '../../types';
import { LEVEL_LABELS, MEMORY_COLORS } from '../../constants';
import { RefreshCw, Database } from 'lucide-react';

interface StatsPanelProps {
  stats: MemoryStats | null;
  onConsolidate: () => void;
  isConsolidating: boolean;
}

const StatsPanel: React.FC<StatsPanelProps> = ({ stats, onConsolidate, isConsolidating }) => {
  if (!stats) return <div className="p-4 text-slate-500 animate-pulse">Loading stats...</div>;

  const total = (stats.l0_count || 0) + (stats.l1_count || 0) + (stats.l2_count || 0) + (stats.l3_count || 0);

  const LevelRow = ({ level, count, color, label }: { level: string, count: number, color: string, label: string }) => (
    <div className="flex items-center justify-between py-2 group cursor-pointer hover:bg-slate-800/50 rounded px-1 transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-2.5 h-2.5 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.3)]" style={{ backgroundColor: color }} />
        <span className="text-xs font-mono font-medium text-slate-400 uppercase w-6">{level.toUpperCase()}</span>
        <span className="text-sm text-slate-300">{label}</span>
      </div>
      <span className="font-mono text-sm font-semibold text-slate-100">{count}</span>
    </div>
  );

  return (
    <div className="bg-slate-900 border-b border-slate-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Database size={14} />
            Memory Stats
        </h3>
        {stats.last_consolidation && (
            <span className="text-[10px] text-slate-600">
                Last: {new Date(stats.last_consolidation).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}
            </span>
        )}
      </div>

      <div className="space-y-1 mb-6">
        <LevelRow level="l0" label={LEVEL_LABELS.l0} count={stats.l0_count} color={MEMORY_COLORS.l0} />
        <LevelRow level="l1" label={LEVEL_LABELS.l1} count={stats.l1_count} color={MEMORY_COLORS.l1} />
        <LevelRow level="l2" label={LEVEL_LABELS.l2} count={stats.l2_count} color={MEMORY_COLORS.l2} />
        <LevelRow level="l3" label={LEVEL_LABELS.l3} count={stats.l3_count} color={MEMORY_COLORS.l3} />
        
        <div className="pt-3 mt-3 border-t border-slate-800 flex justify-between items-center text-slate-400">
            <span className="text-xs">Total Nodes</span>
            <span className="font-mono font-bold text-slate-200">{total}</span>
        </div>
      </div>

      <button
        onClick={onConsolidate}
        disabled={isConsolidating}
        className="w-full flex items-center justify-center gap-2 py-2.5 bg-slate-800 hover:bg-blue-600/20 hover:text-blue-400 hover:border-blue-500/30 border border-slate-700 rounded-lg text-sm text-slate-300 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <RefreshCw size={14} className={isConsolidating ? 'animate-spin' : ''} />
        {isConsolidating ? 'Consolidating...' : 'Force Consolidation'}
      </button>
    </div>
  );
};

export default StatsPanel;