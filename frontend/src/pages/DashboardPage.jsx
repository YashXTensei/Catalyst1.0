import React, { useEffect, useState } from 'react';
import { 
  GitBranch, 
  Database, 
  MessageSquare, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  RefreshCw, 
  ExternalLink, 
  Sparkles, 
  FileText, 
  ArrowRight,
  ShieldCheck,
  Star,
  GitPullRequest
} from 'lucide-react';
import apiService from '../services/api';

export default function DashboardPage({ currentRepo, onNavigate, onRefreshRepo }) {
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStatus = async () => {
    if (!currentRepo) return;
    try {
      const data = await apiService.getRepositoryStatus(currentRepo.id);
      setStatusData(data);
      if (onRefreshRepo && (data.total_decisions !== currentRepo.total_decisions || data.indexing_status !== currentRepo.indexing_status)) {
        onRefreshRepo();
      }
    } catch (err) {
      console.error('Error fetching repo status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll status every 4 seconds if indexing
    const interval = setInterval(() => {
      if (statusData?.indexing_status === 'indexing') {
        fetchStatus();
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [currentRepo?.id, statusData?.indexing_status]);

  const handleTriggerIndex = async () => {
    if (!currentRepo) return;
    setRefreshing(true);
    try {
      await apiService.triggerIndexing(currentRepo.id);
      await fetchStatus();
    } catch (err) {
      console.error(err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleResetStatus = async () => {
    if (!currentRepo) return;
    try {
      await apiService.resetRepositoryStatus(currentRepo.id);
      await fetchStatus();
    } catch (err) {
      console.error('Error resetting status:', err);
    }
  };

  if (!currentRepo) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <Database className="h-12 w-12 text-slate-600 mx-auto mb-4" />
        <h3 className="text-xl font-bold text-white">No Repository Selected</h3>
        <p className="text-slate-400 text-sm mt-1">Connect or select a GitHub repository to get started.</p>
      </div>
    );
  }

  const isIndexing = statusData?.indexing_status === 'indexing';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Header Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl relative overflow-hidden">
        <div className="space-y-2">
          <div className="flex items-center space-x-3">
            <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              {currentRepo.owner}
            </span>
            <span className="text-slate-500">/</span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {currentRepo.name}
            </h1>
            <a
              href={currentRepo.url}
              target="_blank"
              rel="noreferrer"
              className="text-slate-400 hover:text-white transition-colors"
              title="Open repository in GitHub"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
          <p className="text-sm text-slate-400 max-w-2xl">
            {currentRepo.description || 'No description provided by repository.'}
          </p>
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 pt-1">
            <span className="flex items-center space-x-1">
              <Star className="h-3.5 w-3.5 text-amber-400 fill-amber-400/20" />
              <span>{currentRepo.stars?.toLocaleString() || 0} stars</span>
            </span>
            <span className="flex items-center space-x-1">
              <GitBranch className="h-3.5 w-3.5 text-slate-400" />
              <span>branch: {currentRepo.default_branch || 'main'}</span>
            </span>
            <span className="flex items-center space-x-1 text-purple-400 font-mono">
              <GitPullRequest className="h-3.5 w-3.5" />
              <span>{statusData?.total_prs ?? 0} PRs</span>
            </span>
            <span className="flex items-center space-x-1 text-emerald-400 font-mono">
              <MessageSquare className="h-3.5 w-3.5" />
              <span>{statusData?.total_issues ?? 0} Issues</span>
            </span>
          </div>
        </div>

        {/* Indexing trigger and action buttons */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleTriggerIndex}
            disabled={isIndexing || refreshing}
            className="flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isIndexing || refreshing ? 'animate-spin text-indigo-400' : ''}`} />
            <span>{isIndexing ? 'Indexing in progress...' : 'Refresh Index'}</span>
          </button>

          <button
            onClick={() => onNavigate('ask')}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 transition-all"
          >
            <Sparkles className="h-4 w-4" />
            <span>Ask Memory</span>
          </button>
        </div>
      </div>

      {/* Indexing Status Banner */}
      <div className={`p-4 rounded-xl border transition-all ${
        isIndexing 
          ? 'bg-indigo-950/40 border-indigo-500/40 text-indigo-200' 
          : statusData?.indexing_status === 'failed'
          ? 'bg-red-950/30 border-red-500/30 text-red-200'
          : 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {isIndexing ? (
              <RefreshCw className="h-5 w-5 text-indigo-400 animate-spin flex-shrink-0" />
            ) : statusData?.indexing_status === 'failed' ? (
              <AlertTriangle className="h-5 w-5 text-red-400 flex-shrink-0" />
            ) : (
              <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0" />
            )}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider">
                Status: {statusData?.indexing_status || currentRepo.indexing_status}
              </p>
              <p className="text-xs opacity-90 mt-0.5">
                {statusData?.indexing_progress || currentRepo.indexing_progress}
              </p>
            </div>
          </div>
          {isIndexing && (
            <div className="flex items-center space-x-2">
              <span className="text-xs px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-300 font-mono animate-pulse">
                Live Indexing
              </span>
              <button
                onClick={handleResetStatus}
                className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                title="Click if indexing is taking too long or got stuck"
              >
                Reset Status
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Stats Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Pull Requests Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-md hover:border-purple-500/30 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-purple-400">
              Pull Requests
            </span>
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
              <GitPullRequest className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-white font-mono">
              {statusData?.total_prs ?? 0}
            </span>
            <span className="text-xs text-purple-400/80 font-mono">scanned</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Merged & open PRs analyzed for code changes and discussions
          </p>
        </div>

        {/* Issues Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-md hover:border-emerald-500/30 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              GitHub Issues
            </span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <MessageSquare className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-white font-mono">
              {statusData?.total_issues ?? 0}
            </span>
            <span className="text-xs text-emerald-400/80 font-mono">scanned</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Bug reports, proposals & feature design discussions analyzed
          </p>
        </div>

        {/* Extracted Decisions Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-md hover:border-indigo-500/30 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
              Decisions Extracted
            </span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Database className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-emerald-400 font-mono">
              {statusData?.total_decisions ?? currentRepo.total_decisions}
            </span>
            <span className="text-xs text-slate-500">memories</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Vectorized with alternatives, reasoning, and evidence citations
          </p>
        </div>

        {/* Architecture Protection Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-md hover:border-cyan-500/30 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
              Drift & Protection
            </span>
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-cyan-400 font-mono">
              Active
            </span>
            <span className="text-xs text-cyan-400/80 font-mono">ready</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Automated conflict & drift intelligence on incoming PR diffs
          </p>
        </div>
      </div>

      {/* Recent Decisions Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <FileText className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white">Recent Extracted Decisions</h2>
          </div>
          <button
            onClick={() => onNavigate('decisions')}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center space-x-1"
          >
            <span>View All in Explorer</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        {statusData?.recent_decisions?.length > 0 ? (
          <div className="space-y-3">
            {statusData.recent_decisions.map((dec) => (
              <div
                key={dec.id}
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase font-bold ${
                      dec.status === 'accepted' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                      dec.status === 'rejected' ? 'bg-red-500/20 text-red-300 border border-red-500/30' :
                      dec.status === 'proposed' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                      'bg-slate-700/50 text-slate-300'
                    }`}>
                      {dec.status}
                    </span>
                    <h3 className="text-sm font-semibold text-slate-200">{dec.decision}</h3>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-1">{dec.context}</p>
                </div>

                <div className="flex items-center space-x-3 flex-shrink-0">
                  <a
                    href={dec.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-xs text-slate-300 hover:text-white font-mono transition-colors"
                  >
                    {dec.source_url?.includes('/pull/') ? (
                      <span className="flex items-center space-x-1 text-purple-300">
                        <GitPullRequest className="h-3 w-3 text-purple-400" />
                        <span>PR #{dec.source_url.split('/pull/')[1]?.split(/[#/?]/)[0]}</span>
                      </span>
                    ) : dec.source_url?.includes('/issues/') ? (
                      <span className="flex items-center space-x-1 text-emerald-300">
                        <MessageSquare className="h-3 w-3 text-emerald-400" />
                        <span>Issue #{dec.source_url.split('/issues/')[1]?.split(/[#/?]/)[0]}</span>
                      </span>
                    ) : (
                      <span>Source</span>
                    )}
                    <ExternalLink className="h-3 w-3 ml-1" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-10 bg-slate-950/30 rounded-xl border border-dashed border-slate-800">
            <p className="text-slate-400 text-sm">
              {isIndexing ? 'Indexing in progress... decisions will appear here shortly.' : 'No decisions extracted yet. Try refreshing the index.'}
            </p>
          </div>
        )}
      </div>

      {/* Quick Action Navigation Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          onClick={() => onNavigate('ask')}
          className="p-6 rounded-2xl bg-gradient-to-br from-indigo-950/40 via-slate-900 to-slate-900 border border-indigo-500/20 hover:border-indigo-500/40 transition-all cursor-pointer group shadow-lg"
        >
          <div className="flex items-center justify-between">
            <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400 group-hover:scale-105 transition-transform">
              <Sparkles className="h-6 w-6" />
            </div>
            <ArrowRight className="h-5 w-5 text-indigo-400 group-hover:translate-x-1 transition-transform" />
          </div>
          <h3 className="text-lg font-bold text-white mt-4">Ask Project Memory</h3>
          <p className="text-xs text-slate-400 mt-1">
            "Why was library X chosen?", "What alternatives were evaluated?", or "What trade-offs were made?"
          </p>
        </div>

        <div
          onClick={() => onNavigate('pr')}
          className="p-6 rounded-2xl bg-gradient-to-br from-cyan-950/40 via-slate-900 to-slate-900 border border-cyan-500/20 hover:border-cyan-500/40 transition-all cursor-pointer group shadow-lg"
        >
          <div className="flex items-center justify-between">
            <div className="p-3 rounded-xl bg-cyan-500/10 text-cyan-400 group-hover:scale-105 transition-transform">
              <GitBranch className="h-6 w-6" />
            </div>
            <ArrowRight className="h-5 w-5 text-cyan-400 group-hover:translate-x-1 transition-transform" />
          </div>
          <h3 className="text-lg font-bold text-white mt-4">Analyze Pull Request</h3>
          <p className="text-xs text-slate-400 mt-1">
            Detect if a new PR conflicts with historical decisions or introduces previously rejected libraries.
          </p>
        </div>
      </div>
    </div>
  );
}
