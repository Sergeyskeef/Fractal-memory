import React from 'react';
import { Brain, BarChart2, Share2, Settings } from 'lucide-react';

interface HeaderProps {
  showStats: boolean;
  toggleStats: () => void;
  showGraph: boolean;
  toggleGraph: () => void;
}

const Header: React.FC<HeaderProps> = ({ showStats, toggleStats, showGraph, toggleGraph }) => {
  return (
    <header className="h-14 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 fixed top-0 w-full z-50 shadow-md">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
          <Brain className="text-white w-5 h-5" />
        </div>
        <h1 className="font-semibold text-lg text-slate-100 tracking-tight">
          Fractal Memory <span className="text-slate-500 text-xs font-normal ml-2 hidden sm:inline-block">v1.0.0</span>
        </h1>
      </div>

      <div className="flex items-center gap-2">
        <button 
          onClick={toggleGraph}
          className={`p-2 rounded-lg transition-all ${showGraph ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800 hover:text-white'}`}
          title="Toggle Graph View"
        >
          <Share2 className="w-5 h-5" />
        </button>
        <button 
          onClick={toggleStats}
          className={`p-2 rounded-lg transition-all ${showStats ? 'bg-slate-800 text-blue-400' : 'text-slate-400 hover:bg-slate-800 hover:text-white'}`}
          title="Toggle Stats Panel"
        >
          <BarChart2 className="w-5 h-5" />
        </button>
        <button className="p-2 text-slate-400 hover:bg-slate-800 hover:text-white rounded-lg transition-all">
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
};

export default Header;