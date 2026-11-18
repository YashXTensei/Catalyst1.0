import React, { useEffect, useState } from 'react';
import { 
  Database, 
  Search, 
  Filter, 
  ExternalLink, 
  Code2, 
  XCircle, 
  CheckCircle2, 
  AlertCircle, 
  HelpCircle,
  ChevronDown,
  ChevronUp,
  FileCode,
  Tag,
  Layers,
  GitPullRequest,
  MessageSquare
} from 'lucide-react';
import apiService from '../services/api';

export default function DecisionExplorerPage({ currentRepo }) {
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [counts, setCounts] = useState({ total: 0, prs: 0, issues: 0 });
  const [expandedId, setExpandedId] = useState(null);

  const fetchDecisions = async () => {
    if (!currentRepo) return;
    setLoading(true);
    try {
      const params = {};
      if (searchTerm.trim()) params.search = searchTerm.trim();
      if (statusFilter) params.status = statusFilter;
      if (sourceFilter) params.source_type = sourceFilter;
      const data = await apiService.getDecisions(currentRepo.id, params);
      setDecisions(data.decisions || []);
      setCounts({
        total: data.total ?? (data.decisions ? data.decisions.length : 0),
        prs: data.total_pr_decisions ?? 0,
        issues: data.total_issue_decisions ?? 0,
      });
    } catch (err) {
      console.error('Failed to load decisions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisions();
  }, [currentRepo?.id, statusFilter, sourceFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchDecisions();
  };

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'accepted':
        return (
          <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" />
            <span>accepted</span>
          </span>
        );
      case 'rejected':
        return (
          <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="h-3 w-3" />
            <span>rejected</span>
          </span>
        );
      case 'proposed':
        return (
          <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertCircle className="h-3 w-3" />
            <span>proposed</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-slate-700/40 text-slate-300 border border-slate-700">
            <HelpCircle className="h-3 w-3" />
            <span>{status || 'uncertain'}</span>
          </span>
        );
    }
  };

  if (!currentRepo) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center text-slate-400">
        Please select a repository to view decision trail.
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">Decision Explorer</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              {counts.total || decisions.length} recorded
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center space-x-1">
              <GitPullRequest className="h-3 w-3" />
              <span>{counts.prs} PRs</span>
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center space-x-1">
              <MessageSquare className="h-3 w-3" />
              <span>{counts.issues} Issues</span>
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Browse structured decisions with rejected alternatives, reasoning, and linked source discussions.
          </p>
        </div>

        {/* Search & Status Filter */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-64">
            <Search className="h-4 w-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search decisions..."
              className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </form>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full sm:w-auto px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
          >
            <option value="">All Statuses</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
            <option value="proposed">Proposed</option>
            <option value="deprecated">Deprecated</option>
            <option value="uncertain">Uncertain</option>
          </select>
        </div>
      </div>

      {/* Source Type Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setSourceFilter('')}
          className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
            sourceFilter === ''
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
              : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700'
          }`}
        >
          All Decisions ({counts.total || decisions.length})
        </button>
        <button
          type="button"
          onClick={() => setSourceFilter('pr')}
          className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
            sourceFilter === 'pr'
              ? 'bg-purple-600 text-white shadow-md shadow-purple-600/30'
              : 'bg-slate-900 text-purple-300 hover:text-white border border-purple-500/20 hover:border-purple-500/40'
          }`}
        >
          <GitPullRequest className="h-3.5 w-3.5" />
          <span>Pull Requests ({counts.prs})</span>
        </button>
        <button
          type="button"
          onClick={() => setSourceFilter('issue')}
          className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
            sourceFilter === 'issue'
              ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
              : 'bg-slate-900 text-emerald-300 hover:text-white border border-emerald-500/20 hover:border-emerald-500/40'
          }`}
        >
          <MessageSquare className="h-3.5 w-3.5" />
          <span>Issues ({counts.issues})</span>
        </button>
      </div>

      {/* Decisions List */}
      {loading ? (
        <div className="text-center py-16 text-slate-400 text-sm">
          Loading extracted decisions...
        </div>
      ) : decisions.length === 0 ? (
        <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <Database className="h-10 w-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-slate-300">No decisions match your filters</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try adjusting search terms or verify that background indexing has processed issues for this repository.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {decisions.map((dec) => {
            const isExpanded = expandedId === dec.id;
            return (
              <div
                key={dec.id}
                className="bg-slate-900 border border-slate-800/90 rounded-2xl p-5 sm:p-6 shadow-lg transition-all hover:border-slate-700"
              >
                {/* Header line */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {getStatusBadge(dec.status)}
                      <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                        {dec.decision}
                      </h2>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {dec.context}
                    </p>
                  </div>

                  {/* Actions & Source Link */}
                  <div className="flex items-center space-x-3 flex-shrink-0">
                    <a
                      href={dec.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 border border-slate-700 text-xs font-mono transition-colors"
                      title="Open source in GitHub"
                    >
                      {dec.source_url?.includes('/pull/') ? (
                        <span className="flex items-center space-x-1 text-purple-300 font-semibold">
                          <GitPullRequest className="h-3.5 w-3.5 text-purple-400" />
                          <span>PR #{dec.source_url.split('/pull/')[1]?.split(/[#/?]/)[0]}</span>
                        </span>
                      ) : dec.source_url?.includes('/issues/') ? (
                        <span className="flex items-center space-x-1 text-emerald-300 font-semibold">
                          <MessageSquare className="h-3.5 w-3.5 text-emerald-400" />
                          <span>Issue #{dec.source_url.split('/issues/')[1]?.split(/[#/?]/)[0]}</span>
                        </span>
                      ) : (
                        <span className="text-slate-300">Discussion</span>
                      )}
                      <ExternalLink className="h-3 w-3 text-slate-400 ml-0.5" />
                    </a>

                    <button
                      onClick={() => toggleExpand(dec.id)}
                      className="p-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-700 text-slate-300 transition-colors"
                      title={isExpanded ? 'Collapse' : 'Expand details'}
                    >
                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                {/* Key metadata chips */}
                <div className="mt-4 pt-3 border-t border-slate-800/60 flex flex-wrap items-center gap-4 text-xs">
                  {/* Rejected Alternatives */}
                  {dec.rejected_alternatives && dec.rejected_alternatives.length > 0 && (
                    <div className="flex items-center space-x-1.5">
                      <span className="text-slate-400 text-[11px] font-semibold uppercase">Rejected:</span>
                      <div className="flex flex-wrap gap-1">
                        {dec.rejected_alternatives.map((alt, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 rounded bg-rose-950/40 border border-rose-500/30 text-rose-300 font-mono text-[11px]"
                          >
                            {alt}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Code references */}
                  {dec.code_references && dec.code_references.length > 0 && (
                    <div className="flex items-center space-x-1.5">
                      <span className="text-slate-400 text-[11px] font-semibold uppercase">Code:</span>
                      <div className="flex flex-wrap gap-1">
                        {dec.code_references.map((cr, i) => (
                          <span
                            key={i}
                            className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-indigo-300 font-mono text-[11px]"
                          >
                            <FileCode className="h-3 w-3" />
                            <span>{cr}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Components */}
                  {dec.affected_components && dec.affected_components.length > 0 && (
                    <div className="flex items-center space-x-1.5">
                      <span className="text-slate-400 text-[11px] font-semibold uppercase">Module:</span>
                      <span className="text-slate-300 font-mono">{dec.affected_components.join(', ')}</span>
                    </div>
                  )}
                </div>

                {/* Expanded Details Drawer */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-slate-800 space-y-4 text-xs animate-in fade-in duration-200">
                    {/* Reasoning */}
                    {dec.reasoning && dec.reasoning.length > 0 && (
                      <div>
                        <p className="font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                          Reasoning & Trade-offs:
                        </p>
                        <ul className="list-disc list-inside space-y-1 text-slate-300">
                          {dec.reasoning.map((r, rIdx) => (
                            <li key={rIdx}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Evidence quote */}
                    {dec.evidence && dec.evidence.length > 0 && (
                      <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                        <p className="font-semibold text-slate-400 uppercase tracking-wider mb-1">
                          Direct Evidence Excerpt:
                        </p>
                        {dec.evidence.map((ev, evIdx) => (
                          <p key={evIdx} className="text-slate-300 italic">
                            "{ev}"
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
