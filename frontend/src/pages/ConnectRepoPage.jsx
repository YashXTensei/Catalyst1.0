import React, { useState } from 'react';
import { GitBranch, Star, Terminal, AlertCircle, Loader2, ArrowRight, CheckCircle2, ShieldCheck } from 'lucide-react';
import apiService from '../services/api';

const PRESET_REPOS = [
  { url: 'https://github.com/fastapi/fastapi', name: 'fastapi/fastapi', desc: 'Modern, high-performance web framework for Python' },
  { url: 'https://github.com/tiangolo/sqlmodel', name: 'tiangolo/sqlmodel', desc: 'SQL databases in Python, designed for simplicity and compatibility' },
  { url: 'https://github.com/pallets/flask', name: 'pallets/flask', desc: 'The Python micro framework for building web applications' },
];

export default function ConnectRepoPage({ onConnected, isModal = false, onClose = () => {} }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const repo = await apiService.connectRepository(url.trim());
      onConnected(repo);
      if (isModal) onClose();
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail || err.message || 'Failed to connect repository';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (presetUrl) => {
    setUrl(presetUrl);
    setError(null);
  };

  return (
    <div className={`w-full ${isModal ? 'p-1' : 'max-w-4xl mx-auto py-12 px-4'}`}>
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-10 shadow-2xl relative overflow-hidden">
        {/* Subtle background glow */}
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-cyan-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <GitBranch className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">Connect GitHub Repository</h2>
              <p className="text-sm text-slate-400">
                DecisionTrail extracts hidden engineering decisions, trade-offs, and rejected alternatives.
              </p>
            </div>
          </div>

          {error && (
            <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm flex items-start space-x-3">
              <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Connection Error</p>
                <p className="text-xs text-red-300/90 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                Public Repository URL or slug
              </label>
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://github.com/fastapi/fastapi or owner/repo"
                  className="flex-1 px-4 py-3 bg-slate-950/80 border border-slate-700 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading || !url.trim()}
                  className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-sm rounded-xl transition-all shadow-lg shadow-indigo-600/25 flex items-center justify-center space-x-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Connecting...</span>
                    </>
                  ) : (
                    <>
                      <span>Connect Repo</span>
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-2">
                Question-First Architecture: You can query questions immediately while full indexing runs in the background.
              </p>
            </div>
          </form>

          {/* Quick Preset Repos */}
          <div className="mt-8 pt-6 border-t border-slate-800">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Or explore popular open-source repositories:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {PRESET_REPOS.map((preset) => (
                <button
                  key={preset.name}
                  type="button"
                  onClick={() => handleSelectPreset(preset.url)}
                  className={`text-left p-3 rounded-xl border transition-all ${
                    url === preset.url
                      ? 'bg-indigo-950/40 border-indigo-500/60 ring-1 ring-indigo-500/40'
                      : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
                  }`}
                >
                  <p className="text-xs font-mono font-medium text-indigo-300">{preset.name}</p>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{preset.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Features Highlights */}
          <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 border-t border-slate-800 text-xs text-slate-400">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
              <span>Evidence-backed decisions with source links</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
              <span>Question-First instant answering</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
              <span>PR conflict & architectural drift detection</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
