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
  Info
} from 'lucide-react';
import apiService from '../services/api';
import MarkdownRenderer from '../components/MarkdownRenderer';

export default function PRIntelligencePage({ currentRepo }) {
  const [prNumber, setPrNumber] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async (e) => {
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
            <h1 className="text-2xl font-bold text-white tracking-tight">PR Intelligence & Conflict Detection</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Automatically checks changed files & PR intent against historical decisions to prevent regressions.
            </p>
          </div>
        </div>
      </div>

      {/* Input Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <form onSubmit={handleAnalyze} className="space-y-4">
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
                className="w-full pl-8 pr-4 py-3 bg-slate-950/80 border border-slate-700 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !prNumber}
              className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-medium text-sm rounded-xl transition-all shadow-lg shadow-cyan-600/20 flex items-center justify-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Analyzing Diff & Decisions...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Analyze PR</span>
                </>
              )}
            </button>
          </div>
        </form>

        {error && (
          <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Analysis Results View */}
      {result && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* PR Header Banner */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center space-x-3">
                  <span className="text-sm font-mono text-slate-400">PR #{result.pr_number}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-mono uppercase font-bold ${
                    result.state === 'open' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-purple-500/20 text-purple-300'
                  }`}>
                    {result.state}
                  </span>
                  <a
                    href={result.pr_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-slate-400 hover:text-white transition-colors"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </div>
                <h2 className="text-xl font-bold text-white tracking-tight">{result.pr_title}</h2>
                {result.author && (
                  <p className="text-xs text-slate-400">Submitted by @{result.author}</p>
                )}
              </div>

              {/* Overall Risk Indicator */}
              <div>{getRiskBadge(result.overall_risk)}</div>
            </div>

            {/* Architectural Summary */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs text-slate-300 leading-relaxed">
              <span className="font-semibold text-white block mb-1">Architectural Footprint:</span>
              <MarkdownRenderer content={result.summary} />
            </div>

            {/* Changed Files */}
            {result.changed_files && result.changed_files.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Touched Files ({result.changed_files.length}):
                </span>
                <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
                  {result.changed_files.map((file, idx) => (
                    <span
                      key={idx}
                      className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700/80 text-slate-300 font-mono text-xs"
                    >
                      <FileCode className="h-3 w-3 text-cyan-400" />
                      <span>{file}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Potential Conflicts Section */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="h-5 w-5 text-rose-400" />
              <h3 className="text-lg font-bold text-white">Potential Decision Conflicts</h3>
            </div>

            {result.potential_conflicts && result.potential_conflicts.length > 0 ? (
              <div className="space-y-4">
                {result.potential_conflicts.map((conf, idx) => (
                  <div
                    key={idx}
                    className="p-5 rounded-xl bg-slate-950/80 border border-rose-500/30 space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold uppercase">
                          {conf.conflict_risk} risk
                        </span>
                        <h4 className="text-sm font-bold text-slate-100">
                          Conflicts with: {conf.decision_title}
                        </h4>
                      </div>
                      <a
                        href={conf.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs font-mono text-slate-400 hover:text-indigo-300 flex items-center space-x-1"
                      >
                        <span>Original Decision Link</span>
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </div>

                    <p className="text-xs text-rose-200/90 leading-relaxed font-medium">
                      {conf.explanation}
                    </p>

                    {conf.evidence_snippet && (
                      <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-400 italic">
                        "{conf.evidence_snippet}"
                      </div>
                    )}

                    <div className="p-3 rounded-lg bg-indigo-950/30 border border-indigo-500/20 text-xs text-indigo-200 flex items-start space-x-2">
                      <Sparkles className="h-4 w-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold block text-indigo-300">Actionable Recommendation:</span>
                        <span>{conf.recommendation}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 rounded-xl bg-slate-950/40 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0" />
                <span>
                  No direct contradictions found with previously accepted historical decisions. The changes align with established patterns.
                </span>
              </div>
            )}
          </div>

          {/* Overall Recommendations */}
          {result.recommendations && result.recommendations.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-3">
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                Recommendations for Reviewers
              </h3>
              <ul className="space-y-2 text-xs text-slate-300">
                {result.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start space-x-2">
                    <span className="text-cyan-400 font-bold">•</span>
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
