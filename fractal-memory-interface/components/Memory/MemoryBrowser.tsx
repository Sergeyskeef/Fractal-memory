import React, { useState } from 'react';
import { MemoryNode } from '../../types';
import { Search, ChevronDown, Network } from 'lucide-react';
import { MEMORY_COLORS } from '../../constants';

interface MemoryBrowserProps {
  nodes: MemoryNode[];
  onNodeClick: (node: MemoryNode) => void;
}

const MemoryBrowser: React.FC<MemoryBrowserProps> = ({ nodes, onNodeClick }) => {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const filteredNodes = nodes.filter(node => {
    const matchesFilter = filter === 'all' || node.level === filter;
    const matchesSearch = node.content.toLowerCase().includes(search.toLowerCase()) || 
                          node.label.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-slate-900">
        {/* Controls */}
      <div className="p-4 border-b border-slate-800 space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
          <input 
            type="text"
            placeholder="Search memory..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors placeholder-slate-600"
          />
        </div>
        
        <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
            {['all', 'l0', 'l1', 'l2', 'l3'].map(l => (
                <button
                    key={l}
                    onClick={() => setFilter(l)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors whitespace-nowrap
                        ${filter === l 
                            ? 'bg-slate-800 text-white border-slate-600' 
                            : 'bg-transparent text-slate-500 border-slate-800 hover:border-slate-700'
                        }`}
                >
                    {l.toUpperCase()}
                </button>
            ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
        {filteredNodes.length === 0 ? (
            <div className="text-center py-10 text-slate-600 text-sm">
                No memories found.
            </div>
        ) : (
            filteredNodes.map(node => (
            <div 
                key={node.id}
                onClick={() => onNodeClick(node)}
                className="bg-slate-800/40 border border-slate-800/60 p-3 rounded-lg hover:bg-slate-800 hover:border-slate-700 cursor-pointer transition-all group"
            >
                <div className="flex justify-between items-start mb-1">
                    <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-opacity-20 text-opacity-90 font-semibold"
                        style={{ backgroundColor: `${MEMORY_COLORS[node.level]}33`, color: MEMORY_COLORS[node.level] }}
                    >
                        {node.level.toUpperCase()}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                        Imp: {node.importance.toFixed(2)}
                    </span>
                </div>
                <div className="text-sm text-slate-200 font-medium mb-1 line-clamp-1">{node.label}</div>
                <div className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{node.content}</div>
                
                <div className="mt-2 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-blue-400" title="View in Graph">
                        <Network size={14} />
                    </button>
                </div>
            </div>
            ))
        )}
      </div>
    </div>
  );
};

export default MemoryBrowser;