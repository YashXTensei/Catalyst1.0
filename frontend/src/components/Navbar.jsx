import React from 'react';
import { 
  GitBranch, 
  Terminal, 
  Compass, 
  HelpCircle, 
  GitPullRequest, 
  Database,
  RefreshCw,
  FolderGit2,
  Award
} from 'lucide-react';

export default function Navbar({ 
  activeTab, 
  setActiveTab, 
  currentRepo, 
  repositories = [], 
  onSelectRepo,
  onOpenConnectModal
}) {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
            <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Compass className="h-5 w-5 text-white animate-spin-slow" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                  DecisionTrail
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  MVP
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">AI Engineering Decision Intelligence</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'dashboard'
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Terminal className="h-4 w-4" />
              <span>Dashboard</span>
            </button>

            <button
              onClick={() => setActiveTab('ask')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'ask'
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <HelpCircle className="h-4 w-4" />
              <span>Ask Memory</span>
            </button>

            <button
              onClick={() => setActiveTab('decisions')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'decisions'
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Database className="h-4 w-4" />
              <span>Decisions</span>
            </button>

            <button
              onClick={() => setActiveTab('pr')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'pr'
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <GitPullRequest className="h-4 w-4" />
              <span>PR Intelligence</span>
            </button>

            <button
              onClick={() => setActiveTab('benchmark')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'benchmark'
                  ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Award className="h-4 w-4 text-emerald-400" />
              <span>PEP Benchmark</span>
            </button>
          </nav>

          {/* Repo Selector & Connect Button */}
          <div className="flex items-center space-x-3">
            {repositories.length > 0 ? (
              <div className="relative flex items-center">
                <FolderGit2 className="h-4 w-4 text-slate-400 absolute left-2.5 pointer-events-none" />
                <select
                  value={currentRepo?.id || ''}
                  onChange={(e) => {
                    const sel = repositories.find(r => r.id === parseInt(e.target.value, 10));
                    if (sel) onSelectRepo(sel);
                  }}
                  className="pl-8 pr-7 py-1.5 bg-slate-800/90 border border-slate-700 rounded-md text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer max-w-[170px] truncate"
                >
                  {repositories.map(r => (
                    <option key={r.id} value={r.id}>{r.full_name}</option>
                  ))}
                </select>
              </div>
            ) : null}

            <button
              onClick={onOpenConnectModal}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white shadow-sm transition-all shadow-indigo-500/20"
            >
              <GitBranch className="h-3.5 w-3.5" />
              <span>+ Connect Repo</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
