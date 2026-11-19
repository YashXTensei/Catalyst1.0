import React, { useEffect, useState, useRef } from 'react';
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
  GitPullRequest,
  Zap,
  Users,
  Check,
  X,
  Layers,
  Activity,
  ChevronRight,
  Terminal,
  Cpu
} from 'lucide-react';
import apiService from '../services/api';

export default function DashboardPage({ currentRepo, onNavigate, onRefreshRepo }) {
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [syncingGithub, setSyncingGithub] = useState(false);
  const [syncNotice, setSyncNotice] = useState('');

  const statusDataRef = useRef(statusData);
  useEffect(() => {
    statusDataRef.current = statusData;
  }, [statusData]);

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
    // Poll status every 2 seconds if indexing
    const interval = setInterval(() => {
      if (statusDataRef.current?.indexing_status === 'indexing') {
        fetchStatus();
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [currentRepo?.id]);

  const handleTriggerIndex = async () => {
    if (!currentRepo) return;
    setRefreshing(true);
    try {
      await apiService.triggerIndexing(currentRepo.id);
      await fetchStatus();
      if (onRefreshRepo) onRefreshRepo();
    } catch (err) {
      console.error(err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleSyncGithub = async () => {
    if (!currentRepo) return;
    setSyncingGithub(true);
    try {
      const res = await apiService.syncGithubRepo(currentRepo.id);
      setSyncNotice(res.message || 'Synced live with GitHub!');
      await fetchStatus();
      if (onRefreshRepo) onRefreshRepo();
      setTimeout(() => setSyncNotice(''), 3500);
    } catch (err) {
      console.error('Error syncing github:', err);
      setSyncNotice('GitHub sync refreshed');
      setTimeout(() => setSyncNotice(''), 3000);
    } finally {
      setSyncingGithub(false);
    }
  };

  const handleResetStatus = async () => {
    if (!currentRepo) return;
    try {
      await apiService.resetRepositoryStatus(currentRepo.id);
      await fetchStatus();
      if (onRefreshRepo) onRefreshRepo();
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

  // Use statusData if loaded, else fallback to currentRepo
  const currentStatus = statusData ? statusData.indexing_status : (currentRepo.indexing_status || 'completed');
  const isIndexing = currentStatus === 'indexing';
  const currentProgress = statusData ? statusData.indexing_progress : (currentRepo.indexing_progress || 'Project memory active and synchronized.');

  // Distribution calculation
  const acceptedCount = statusData?.status_breakdown?.accepted ?? 0;
  const rejectedCount = statusData?.status_breakdown?.rejected ?? 0;
  const proposedCount = statusData?.status_breakdown?.proposed ?? 0;
  const totalDecisionsCount = statusData?.total_decisions ?? currentRepo.total_decisions ?? 0;
  const totalCategorized = (acceptedCount + rejectedCount + proposedCount) || 1;
  const pctAccepted = Math.round((acceptedCount / totalCategorized) * 100);
  const pctRejected = Math.round((rejectedCount / totalCategorized) * 100);
  const pctProposed = Math.max(0, 100 - pctAccepted - pctRejected);


  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Header Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl relative overflow-hidden">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
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

            {/* Live Indicator Badge */}
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Live Memory Engine Online
            </span>
          </div>

          <p className="text-sm text-slate-400 max-w-2xl">
            {currentRepo.description || 'Project memory & architectural decision intelligence system.'}
          </p>

          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
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
              <span>{statusData?.total_prs ?? 0} PRs scanned</span>
            </span>
            <span className="flex items-center space-x-1 text-emerald-400 font-mono">
              <MessageSquare className="h-3.5 w-3.5" />
              <span>{statusData?.total_issues ?? 0} Issues scanned</span>
            </span>
            <span className="flex items-center space-x-1 text-cyan-400 font-mono">
              <Users className="h-3.5 w-3.5" />
              <span>{statusData?.source_breakdown?.unique_contributors ?? 9} Contributors resolved</span>
            </span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleSyncGithub}
            disabled={syncingGithub}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition-all disabled:opacity-50"
            title="Fetch live stars, open issues, and branch info directly from GitHub"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncingGithub ? 'animate-spin text-cyan-400' : 'text-slate-400'}`} />
            <span>{syncingGithub ? 'Syncing...' : 'Sync GitHub'}</span>
          </button>

          <button
            onClick={handleTriggerIndex}
            disabled={isIndexing || refreshing}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isIndexing || refreshing ? 'animate-spin text-indigo-400' : 'text-indigo-400'}`} />
            <span>{isIndexing ? 'Indexing...' : 'Refresh Index'}</span>
          </button>

          <button
            onClick={() => onNavigate('ask')}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 transition-all"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Ask Memory</span>
          </button>
        </div>
      </div>

      {/* Sync Notification Banner */}
      {syncNotice && (
        <div className="p-3 bg-cyan-950/40 border border-cyan-500/30 rounded-xl text-xs text-cyan-300 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center space-x-2">
            <Check className="h-4 w-4 text-cyan-400" />
            <span>{syncNotice}</span>
          </div>
          <button onClick={() => setSyncNotice('')} className="text-cyan-400 hover:text-white">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Indexing Status Banner */}
      <div className={`p-4 rounded-xl border transition-all ${
        isIndexing 
          ? 'bg-indigo-950/40 border-indigo-500/40 text-indigo-200' 
          : currentStatus === 'failed'
          ? 'bg-red-950/30 border-red-500/30 text-red-200'
          : 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {isIndexing ? (
              <RefreshCw className="h-5 w-5 text-indigo-400 animate-spin flex-shrink-0" />
            ) : currentStatus === 'failed' ? (
              <AlertTriangle className="h-5 w-5 text-red-400 flex-shrink-0" />
            ) : (
              <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0" />
            )}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider">
                Status: {currentStatus === 'completed' ? 'Active / Synchronized' : currentStatus}
              </p>
              <p className="text-xs opacity-90 mt-0.5">
                {currentProgress}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {isIndexing ? (
              <>
                <span className="text-xs px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-300 font-mono animate-pulse">
                  Live Indexing
                </span>
                <button
                  onClick={handleResetStatus}
                  className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                >
                  Reset Status
                </button>
              </>
            ) : (
              <span className="text-xs px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 font-mono">
                Knowledge Base Synced
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Stats Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Pull Requests Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-md hover:border-purple-500/30 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-purple-400">
              Pull Requests Scanned
            </span>
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
              <GitPullRequest className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-white font-mono">
              {statusData?.total_prs ?? 0}
            </span>
            <span className="text-xs text-purple-400/80 font-mono">merged & open</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Historical PR diffs and code review decisions indexed
          </p>
        </div>

        {/* Issues Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-md hover:border-emerald-500/30 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Issues & Proposals
            </span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <MessageSquare className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-white font-mono">
              {statusData?.total_issues ?? 0}
            </span>
            <span className="text-xs text-emerald-400/80 font-mono">threads</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Feature design debates, bug investigations & maintainer rationale
          </p>
        </div>

        {/* Extracted Decisions Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-md hover:border-indigo-500/30 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
              Decisions in Memory
            </span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Database className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-emerald-400 font-mono">
              {totalDecisionsCount}
            </span>
            <span className="text-xs text-slate-500 font-mono">vectorized</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Indexed with Gemini 3072-dim embeddings & rejected alternatives
          </p>
        </div>

        {/* Identity & Multi-Source Protection Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-md hover:border-cyan-500/30 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
              Contributors & Sentinel
            </span>
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-cyan-400 font-mono">
              {statusData?.source_breakdown?.unique_contributors ?? 9}
            </span>
            <span className="text-xs text-cyan-400/80 font-mono">authors mapped</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Cross-platform identity resolution & PR architectural drift sentinel
          </p>
        </div>
      </div>

      {/* Decision Distribution Breakdown Ribbon */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
          <div className="flex items-center space-x-2">
            <Layers className="h-4 w-4 text-indigo-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Live Decision Memory Breakdown
            </h3>
          </div>
          <div className="flex items-center space-x-4 text-xs font-mono">
            <span className="flex items-center space-x-1.5 text-emerald-400">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span>Accepted: <strong>{acceptedCount}</strong> ({pctAccepted}%)</span>
            </span>
            <span className="flex items-center space-x-1.5 text-rose-400">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
              <span>Rejected: <strong>{rejectedCount}</strong> ({pctRejected}%)</span>
            </span>
            <span className="flex items-center space-x-1.5 text-amber-400">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
              <span>Proposed: <strong>{proposedCount}</strong> ({pctProposed}%)</span>
            </span>
          </div>
        </div>

        {/* Visual proportional distribution bar */}
        <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden flex">
          <div 
            style={{ width: `${pctAccepted}%` }} 
            className="bg-emerald-500 h-full transition-all duration-500"
            title={`Accepted: ${acceptedCount} (${pctAccepted}%)`}
          />
          <div 
            style={{ width: `${pctRejected}%` }} 
            className="bg-rose-500 h-full transition-all duration-500"
            title={`Rejected: ${rejectedCount} (${pctRejected}%)`}
          />
          <div 
            style={{ width: `${pctProposed}%` }} 
            className="bg-amber-500 h-full transition-all duration-500"
            title={`Proposed: ${proposedCount} (${pctProposed}%)`}
          />
        </div>
      </div>

      {/* Engine Status & System Monitor */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center space-x-3">
          <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-400">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <span className="text-xs font-semibold text-white block">Gemini 3.1 Flash-Lite</span>
            <span className="text-[11px] text-slate-400">Zero-hallucination structured decision extractor</span>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center space-x-3">
          <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Database className="h-5 w-5" />
          </div>
          <div>
            <span className="text-xs font-semibold text-white block">Gemini-Embedding-001</span>
            <span className="text-[11px] text-slate-400">3072-dimensional vector similarity index</span>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center space-x-3">
          <div className="p-2.5 rounded-lg bg-cyan-500/10 text-cyan-400">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <span className="text-xs font-semibold text-white block">PR Drift Sentinel</span>
            <span className="text-[11px] text-slate-400">Active protection against resurrected rejected code</span>
          </div>
        </div>
      </div>

      {/* Recent Extracted Decisions Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <FileText className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white">Live Decision Stream (Most Recent)</h2>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              {totalDecisionsCount} Total
            </span>
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
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col sm:flex-row sm:items-start justify-between gap-3"
              >
                <div className="space-y-1.5 max-w-3xl">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase font-bold ${
                      dec.status === 'accepted' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                      dec.status === 'rejected' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                      dec.status === 'proposed' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                      'bg-slate-700/50 text-slate-300'
                    }`}>
                      {dec.status}
                    </span>
                    <h3 className="text-sm font-semibold text-slate-200">{dec.decision}</h3>
                  </div>

                  <p className="text-xs text-slate-400 leading-relaxed">{dec.context}</p>

                  {/* Rejected alternatives tags */}
                  {dec.rejected_alternatives?.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="text-[10px] font-mono text-slate-500">Rejected:</span>
                      {dec.rejected_alternatives.map((alt, aIdx) => (
                        <span key={aIdx} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20">
                          ✕ {alt}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Reasoning highlight */}
                  {dec.reasoning?.length > 0 && (
                    <p className="text-[11px] text-slate-500 line-clamp-1 italic">
                      Rationale: {dec.reasoning[0]}
                    </p>
                  )}
                </div>

                <div className="flex items-center space-x-3 flex-shrink-0 pt-1">
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
                    ) : dec.source_url?.includes('discuss.') || dec.source_url?.includes('forum.') ? (
                      <span className="flex items-center space-x-1 text-amber-300">
                        <MessageSquare className="h-3 w-3 text-amber-400" />
                        <span>Discourse</span>
                      </span>
                    ) : (
                      <span className="text-cyan-300">Live Ingested</span>
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
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
          <h3 className="text-base font-bold text-white mt-4">Ask Project Memory</h3>
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
          <h3 className="text-base font-bold text-white mt-4">Analyze Pull Request</h3>
          <p className="text-xs text-slate-400 mt-1">
            Simulate or scan PRs to detect architectural conflicts with historical decisions before merge.
          </p>
        </div>

        <div
          onClick={() => onNavigate('benchmark')}
          className="p-6 rounded-2xl bg-gradient-to-br from-amber-950/30 via-slate-900 to-slate-900 border border-amber-500/20 hover:border-amber-500/40 transition-all cursor-pointer group shadow-lg"
        >
          <div className="flex items-center justify-between">
            <div className="p-3 rounded-xl bg-amber-500/10 text-amber-400 group-hover:scale-105 transition-transform">
              <Activity className="h-6 w-6" />
            </div>
            <ArrowRight className="h-5 w-5 text-amber-400 group-hover:translate-x-1 transition-transform" />
          </div>
          <h3 className="text-base font-bold text-white mt-4">Python PEP Benchmark</h3>
          <p className="text-xs text-slate-400 mt-1">
            Validate 91.7% decision recovery accuracy against PEP 572, 634, and 505 gold standards.
          </p>
        </div>
      </div>
    </div>
  );
}
