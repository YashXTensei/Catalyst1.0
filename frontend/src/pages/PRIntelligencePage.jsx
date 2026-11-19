import React, { useState } from 'react';
import { 
  GitPullRequest, 
  Search, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldAlert, 
  FileCode, 
  ExternalLink, 
  Loader2, 
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Info,
  Terminal,
  Play
} from 'lucide-react';
import apiService from '../services/api';
import MarkdownRenderer from '../components/MarkdownRenderer';

export default function PRIntelligencePage({ currentRepo }) {
  const [mode, setMode] = useState('simulate'); // 'simulate' or 'github'
  const [prNumber, setPrNumber] = useState('');
  
  // Simulator state
  const [simTitle, setSimTitle] = useState('Introduce Redis-based distributed session storage');
  const [simFiles, setSimFiles] = useState('backend/database.py, app/services/session.py');
  const [simDescription, setSimDescription] = useState('Replaces local storage with Redis cluster to support multi-node session caching.');
  const [simDiff, setSimDiff] = useState('+ import redis\n+ redis_client = redis.Redis(host="localhost", port=6379)\n+ def save_session(session_id, data): redis_client.set(session_id, data)');
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyzeGitHub = async (e) => {
    e?.preventDefault();
    if (!prNumber || !currentRepo) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await apiService.analyzePR(currentRepo.id, prNumber);
      setResult(data);
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail || err.message || 'Failed to analyze pull request.';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeSimulated = async (e) => {
    e?.preventDefault();
    if (!simTitle || !currentRepo) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const changedFilesList = simFiles.split(',').map(f => f.trim()).filter(Boolean);
      const data = await apiService.simulatePR(currentRepo.id, {
        title: simTitle,
        description: simDescription,
        changed_files: changedFilesList,
        diff: simDiff
      });
      setResult(data);
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail || err.message || 'Failed to analyze simulated pull request.';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadPreset = (presetType) => {
    if (presetType === 'redis') {
      setSimTitle('Introduce Redis for session management and distributed cache');
      setSimFiles('backend/database.py, app/services/session_store.py');
      setSimDescription('Adding Redis client for session storage to scale beyond local database.');
      setSimDiff('+ import redis\n+ pool = redis.ConnectionPool(host="redis-cluster")\n+ def get_session(token): return pool.get(token)');
    } else if (presetType === 'walrus') {
      setSimTitle('Re-evaluate using "as" keyword for inline assignment expressions');
      setSimFiles('Python/compile.c, Parser/python.gram');
      setSimDescription('Proposal to allow (expr as target) syntax instead of := operator.');
      setSimDiff('+ // Grammar: expr AS NAME\n+ STMT: expr "as" NAME');
    }
    setError(null);
    setResult(null);
  };

  const getRiskBadge = (risk) => {
    switch (risk?.toLowerCase()) {
      case 'high':
        return (
          <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
            <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
            <span>HIGH CONFLICT RISK</span>
          </span>
        );
      case 'medium':
        return (
          <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            <span>MEDIUM RISK</span>
          </span>
        );
      case 'low':
        return (
          <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
            <Info className="h-3.5 w-3.5 text-blue-400" />
            <span>LOW TOUCHPOINT</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span>ALIGNED / NO CONFLICTS</span>
          </span>
        );
    }
  };

  if (!currentRepo) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center text-slate-400">
        Please select a repository to analyze pull requests.
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <GitPullRequest className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">PR Intelligence & Architectural Drift Bot</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Automatically checks proposed code changes against historical engineering decisions to prevent regressions.
            </p>
          </div>
        </div>
      </div>

      {/* Mode Switcher */}
      <div className="flex items-center space-x-3">
        <button
          onClick={() => { setMode('simulate'); setResult(null); }}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            mode === 'simulate'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          <Play className="h-3.5 w-3.5" />
          <span>Interactive PR Simulator (Live Demo)</span>
        </button>

        <button
          onClick={() => { setMode('github'); setResult(null); }}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            mode === 'github'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          <GitPullRequest className="h-3.5 w-3.5" />
          <span>Live GitHub PR (# Number)</span>
        </button>
      </div>

      {/* Input Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        {mode === 'simulate' ? (
          <form onSubmit={handleAnalyzeSimulated} className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Simulate Proposed Pull Request on <span className="font-mono text-indigo-400">{currentRepo.full_name}</span>
              </span>
              <div className="flex items-center space-x-2 text-xs">
                <span className="text-slate-400">Quick presets:</span>
                <button
                  type="button"
                  onClick={() => handleLoadPreset('redis')}
                  className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700 font-mono text-[11px]"
                >
                  Redis Session Storage
                </button>
                <button
                  type="button"
                  onClick={() => handleLoadPreset('walrus')}
                  className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 font-mono text-[11px]"
                >
                  Walrus 'as' Syntax
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">PR Title</label>
              <input
                type="text"
                value={simTitle}
                onChange={(e) => setSimTitle(e.target.value)}
                placeholder="e.g. Introduce Redis for session cache"
                className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-700 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-medium"
                disabled={loading}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Changed Files (comma-separated)</label>
                <input
                  type="text"
                  value={simFiles}
                  onChange={(e) => setSimFiles(e.target.value)}
                  placeholder="e.g. backend/database.py, app/session.py"
                  className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-100 font-mono placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">PR Description / Context</label>
                <input
                  type="text"
                  value={simDescription}
                  onChange={(e) => setSimDescription(e.target.value)}
                  placeholder="e.g. Adds distributed redis cache"
                  className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  disabled={loading}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Code Diff Snippet (Optional)</label>
              <textarea
                value={simDiff}
                onChange={(e) => setSimDiff(e.target.value)}
                rows={3}
                placeholder="+ import redis..."
                className="w-full px-4 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading || !simTitle.trim()}
              className="flex items-center justify-center space-x-2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-600 hover:to-indigo-700 text-white rounded-xl text-sm font-semibold transition-all disabled:opacity-50 shadow-lg shadow-cyan-500/20"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Checking Code-to-Decision Mappings & Conflicts...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Analyze Simulated PR for Conflicts</span>
                </>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleAnalyzeGitHub} className="space-y-4">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Target Pull Request Number in <span className="font-mono text-indigo-400">{currentRepo.full_name}</span>
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <span className="absolute left-4 top-3 text-slate-500 font-mono text-sm">#</span>
                <input
                  type="number"
                  min="1"
                  value={prNumber}
                  onChange={(e) => setPrNumber(e.target.value)}
                  placeholder="e.g. 1024"
                  className="w-full pl-8 pr-4 py-3 bg-slate-950/80 border border-slate-700 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
                  disabled={loading}
                />
              </div>
              <button
                type="submit"
                disabled={loading || !prNumber}
                className="flex items-center justify-center space-x-2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-600 hover:to-indigo-700 text-white rounded-xl text-sm font-semibold transition-all disabled:opacity-50 shadow-lg shadow-cyan-500/20"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Analyzing Architectural Drift...</span>
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    <span>Scan PR Conflicts</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}

        {error && (
          <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Analysis Results */}
      {result && (
        <div className="space-y-6 animate-fade-in">
          {/* PR Overview Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-6 shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
              <div>
                <div className="flex items-center space-x-3 mb-1">
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {result.pr_number > 0 ? `PR #${result.pr_number}` : 'SIMULATED PR'}
                  </span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 uppercase">
                    {result.state}
                  </span>
                  {result.author && (
                    <span className="text-xs text-slate-400">
                      by <span className="text-slate-200 font-mono">@{result.author}</span>
                    </span>
                  )}
                </div>
                <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">{result.pr_title}</h2>
              </div>
              <div className="flex items-center space-x-3">
                {getRiskBadge(result.overall_risk)}
                {result.pr_url && (
                  <a
                    href={result.pr_url}
                    target="_blank"
                    rel="noreferrer"
                    className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition-colors"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
              </div>
            </div>

            {/* AI Summary */}
            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Architectural Footprint Summary</span>
              <p className="text-sm text-slate-300 leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
                {result.summary}
              </p>
            </div>

            {/* Changed files */}
            {result.changed_files?.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Touched Components / Files ({result.changed_files.length})
                </span>
                <div className="flex flex-wrap gap-2">
                  {result.changed_files.map((file, idx) => (
                    <span
                      key={idx}
                      className="flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-slate-800/70 border border-slate-700/50 text-slate-300"
                    >
                      <FileCode className="h-3 w-3 text-cyan-400" />
                      <span>{file}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Potential Conflicts / Drift Warnings */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-white tracking-tight flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-amber-400" />
              <span>Historical Decision Conflicts & Regressions</span>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 ml-2">
                {result.potential_conflicts?.length || 0}
              </span>
            </h3>

            {result.potential_conflicts?.length > 0 ? (
              <div className="space-y-4">
                {result.potential_conflicts.map((conflict, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-900 border border-rose-500/30 rounded-2xl p-6 space-y-4 shadow-xl relative overflow-hidden"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold uppercase">
                          {conflict.conflict_risk} Conflict
                        </span>
                        <h4 className="text-base font-bold text-white">
                          Violates Past Decision: &ldquo;{conflict.decision_title}&rdquo;
                        </h4>
                      </div>
                      {conflict.source_url && (
                        <a
                          href={conflict.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center space-x-1 text-xs text-indigo-400 hover:underline font-mono"
                        >
                          <span>Original Discussion</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>

                    <p className="text-sm text-slate-300 leading-relaxed font-medium">
                      {conflict.explanation}
                    </p>

                    {conflict.evidence_snippet && (
                      <div className="bg-slate-950/80 border-l-2 border-indigo-500 p-3 rounded-r-xl text-xs text-slate-400 font-mono space-y-1">
                        <span className="text-[10px] text-indigo-400 uppercase font-bold tracking-wider">Historical Evidence Excerpt:</span>
                        <p className="italic text-slate-300">&ldquo;{conflict.evidence_snippet}&rdquo;</p>
                      </div>
                    )}

                    <div className="flex items-start space-x-2 text-xs text-amber-300 bg-amber-950/30 p-3 rounded-xl border border-amber-500/30">
                      <Sparkles className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold uppercase tracking-wider text-[10px] block text-amber-400">
                          Maintainer Recommendation:
                        </span>
                        <span>{conflict.recommendation}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-slate-900 border border-emerald-500/30 rounded-2xl p-6 text-center text-slate-300 space-y-2">
                <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto" />
                <p className="text-sm font-semibold text-white">No Historical Conflicts Detected</p>
                <p className="text-xs text-slate-400 max-w-lg mx-auto">
                  The proposed code changes do not contradict any previously evaluated or rejected architectural decisions.
                </p>
              </div>
            )}
          </div>

          {/* Actionable Review Recommendations */}
          {result.recommendations?.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Actionable Next Steps for PR Author & Reviewer
              </span>
              <ul className="space-y-2 text-sm text-slate-300">
                {result.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <ArrowRight className="h-4 w-4 text-cyan-400 flex-shrink-0 mt-0.5" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
