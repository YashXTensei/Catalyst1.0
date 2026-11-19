import React, { useState, useEffect } from 'react';
import { 
  Award, 
  Play, 
  RefreshCw, 
  ExternalLink, 
  CheckCircle2, 
  AlertCircle, 
  HelpCircle, 
  Loader2, 
  ChevronDown, 
  ChevronUp, 
  Check, 
  Quote, 
  Scale, 
  FileText, 
  MessageSquare,
  Sparkles
} from 'lucide-react';
import apiService from '../services/api';

export default function PEPBenchmarkPage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [activePEP, setActivePEP] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(695);
  const [expandedPEPs, setExpandedPEPs] = useState({});

  const fetchBenchmark = async () => {
    setLoading(true);
    try {
      const data = await apiService.getBenchmarkSummary();
      setSummary(data);
      // Auto expand first PEP
      if (data?.dataset?.length > 0) {
        setExpandedPEPs({ [data.dataset[0].pep_number]: true });
      }
    } catch (err) {
      console.error('Failed to fetch benchmark summary:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCandidates = async () => {
    try {
      const data = await apiService.getBenchmarkCandidates();
      if (data?.candidate_peps) {
        setCandidates(data.candidate_peps);
        if (data.candidate_peps.length > 0) {
          setSelectedCandidate(data.candidate_peps[0]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch candidates:', err);
    }
  };

  useEffect(() => {
    fetchBenchmark();
    fetchCandidates();
  }, []);

  const handleRunFullBenchmark = async () => {
    setRunning(true);
    try {
      const updated = await apiService.runBenchmark({ force_refresh: true });
      setSummary(updated);
    } catch (err) {
      console.error('Benchmark execution error:', err);
    } finally {
      setRunning(false);
    }
  };

  const handleRunSingle = async (pepNum) => {
    setRunning(true);
    setActivePEP(pepNum);
    try {
      await apiService.runSinglePEPBenchmark(pepNum, true);
      await fetchBenchmark();
      setExpandedPEPs(prev => ({ ...prev, [pepNum]: true }));
    } catch (err) {
      console.error(`Error running PEP ${pepNum}:`, err);
    } finally {
      setRunning(false);
      setActivePEP(null);
    }
  };

  const toggleExpand = (pepNum) => {
    setExpandedPEPs(prev => ({
      ...prev,
      [pepNum]: !prev[pepNum]
    }));
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'matched':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1"><Check className="h-3 w-3" /> MATCHED</span>;
      case 'partial':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center gap-1"><AlertCircle className="h-3 w-3" /> PARTIAL</span>;
      case 'missed':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center gap-1"><AlertCircle className="h-3 w-3" /> MISSED</span>;
      case 'unmatched_recovery':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/30 flex items-center gap-1"><Sparkles className="h-3 w-3" /> UNMATCHED RECOVERY</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-700 text-slate-300">{status}</span>;
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Award className="h-6 w-6" />
            </span>
            <h1 className="text-2xl font-bold text-white tracking-tight">Python PEP Blind Decision Recovery Benchmark</h1>
          </div>
          <p className="text-xs text-slate-400 mt-2 max-w-3xl leading-relaxed">
            Evaluates whether DecisionTrail's extraction agent can blindly recover rejected architectural alternatives and reasoning directly from raw community discussions (e.g. <span className="text-indigo-400 font-mono">discuss.python.org</span>) without seeing the official PEP document. Reference answers are parsed from the official <span className="text-slate-300 font-mono">python/peps</span> repository.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          <button
            onClick={fetchBenchmark}
            disabled={loading || running}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            title="Refresh Benchmark Results"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleRunFullBenchmark}
            disabled={running}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-medium text-xs shadow-lg shadow-indigo-500/20 transition disabled:opacity-50"
          >
            {running && !activePEP ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Evaluating Benchmark...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-white" />
                <span>Run Full Benchmark</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 flex flex-col justify-between">
            <span className="text-xs text-slate-400 font-medium">Precision (Accuracy)</span>
            <div className="mt-2 flex items-baseline space-x-2">
              <span className="text-3xl font-bold text-emerald-400 font-mono">
                {summary.average_precision}%
              </span>
              <span className="text-xs text-slate-500">TP / (TP + FP)</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Grounding accuracy of recovered ideas</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 flex flex-col justify-between">
            <span className="text-xs text-slate-400 font-medium">Recall (Coverage)</span>
            <div className="mt-2 flex items-baseline space-x-2">
              <span className="text-3xl font-bold text-indigo-400 font-mono">
                {summary.average_recall}%
              </span>
              <span className="text-xs text-slate-500">TP / (TP + FN)</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Share of PEP rejected ideas recovered</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 flex flex-col justify-between">
            <span className="text-xs text-slate-400 font-medium">F1 Score</span>
            <div className="mt-2 flex items-baseline space-x-2">
              <span className="text-3xl font-bold text-cyan-400 font-mono">
                {summary.average_f1_score}%
              </span>
              <span className="text-xs text-slate-500">Harmonic mean</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Balanced precision & coverage metric</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 flex flex-col justify-between">
            <span className="text-xs text-slate-400 font-medium">Dataset Coverage</span>
            <div className="mt-2 flex items-baseline space-x-2">
              <span className="text-3xl font-bold text-white font-mono">
                {summary.completed_evaluations} <span className="text-lg text-slate-500">/ {summary.total_peps_evaluated}</span>
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">{summary.total_ground_truth_ideas} ground-truth items compared</p>
          </div>
        </div>
      )}

      {/* Candidate Runner Bar */}
      <div className="p-4 rounded-xl bg-slate-800/30 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-2">
          <Scale className="h-4 w-4 text-indigo-400" />
          <span className="text-slate-300 font-medium">Targeted Single PEP Evaluation:</span>
          <select
            value={selectedCandidate}
            onChange={(e) => setSelectedCandidate(parseInt(e.target.value, 10))}
            className="px-3 py-1 bg-slate-900 border border-slate-700 rounded-md text-slate-200 font-mono focus:outline-none focus:border-indigo-500 cursor-pointer"
          >
            {candidates.map((num) => (
              <option key={num} value={num}>PEP {num}</option>
            ))}
          </select>
        </div>

        <button
          onClick={() => handleRunSingle(selectedCandidate)}
          disabled={running}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-500/30 font-medium transition disabled:opacity-50 w-fit"
        >
          {running && activePEP === selectedCandidate ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>Evaluating PEP {selectedCandidate}...</span>
            </>
          ) : (
            <>
              <Play className="h-3.5 w-3.5 fill-indigo-300" />
              <span>Evaluate PEP {selectedCandidate}</span>
            </>
          )}
        </button>
      </div>

      {/* Dataset Results Table / Cards */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-white tracking-tight">Evaluated PEP Documents & Discussions</h2>

        {loading ? (
          <div className="py-16 text-center text-slate-500 flex flex-col items-center space-y-2">
            <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
            <span>Loading benchmark dataset...</span>
          </div>
        ) : summary?.dataset?.length === 0 ? (
          <div className="p-8 rounded-xl bg-slate-800/20 border border-slate-800 text-center text-slate-400 space-y-3">
            <p>No benchmark records found. Click <strong>"Run Full Benchmark"</strong> to evaluate against live Python PEP discussions.</p>
          </div>
        ) : (
          summary?.dataset?.map((pep) => {
            const isExpanded = expandedPEPs[pep.pep_number];
            return (
              <div 
                key={pep.pep_number}
                className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-lg transition"
              >
                {/* Header row */}
                <div 
                  className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-slate-800/30 transition"
                  onClick={() => toggleExpand(pep.pep_number)}
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-3">
                      <span className="px-2 py-0.5 rounded font-mono text-xs font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        PEP {pep.pep_number}
                      </span>
                      <h3 className="text-base font-semibold text-white">{pep.title}</h3>
                      {pep.status === 'completed' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          Evaluated
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          {pep.status}
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 pt-1">
                      <a 
                        href={pep.official_url} 
                        target="_blank" 
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center space-x-1 text-indigo-400 hover:underline"
                      >
                        <FileText className="h-3 w-3" />
                        <span>Official PEP</span>
                        <ExternalLink className="h-2.5 w-2.5" />
                      </a>

                      {pep.discussion_url && (
                        <a 
                          href={pep.discussion_url} 
                          target="_blank" 
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="flex items-center space-x-1 text-cyan-400 hover:underline"
                        >
                          <MessageSquare className="h-3 w-3" />
                          <span>Discourse Thread</span>
                          <ExternalLink className="h-2.5 w-2.5" />
                        </a>
                      )}

                      <span>Ground Truth Ideas: <strong className="text-white font-mono">{pep.total_ground_truth}</strong></span>
                      <span>Recovered: <strong className="text-white font-mono">{pep.total_recovered}</strong></span>
                    </div>
                  </div>

                  {/* Metrics Badges */}
                  <div className="flex items-center space-x-4 self-end md:self-auto">
                    <div className="text-right">
                      <span className="text-[11px] text-slate-400 block">Precision</span>
                      <span className="text-sm font-bold font-mono text-emerald-400">{Math.round(pep.precision * 100)}%</span>
                    </div>
                    <div className="text-right">
                      <span className="text-[11px] text-slate-400 block">Recall</span>
                      <span className="text-sm font-bold font-mono text-indigo-400">{Math.round(pep.recall * 100)}%</span>
                    </div>
                    <div className="text-right">
                      <span className="text-[11px] text-slate-400 block">F1 Score</span>
                      <span className="text-sm font-bold font-mono text-cyan-400">{Math.round(pep.f1_score * 100)}%</span>
                    </div>

                    <button className="p-1 rounded text-slate-400 hover:text-white">
                      {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                    </button>
                  </div>
                </div>

                {/* Expanded Comparison Breakdown */}
                {isExpanded && (
                  <div className="border-t border-slate-800 bg-slate-950/60 p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                        Ground-Truth vs. Blind Recovered Ideas ({pep.comparisons?.length || 0})
                      </h4>
                      <button
                        onClick={() => handleRunSingle(pep.pep_number)}
                        disabled={running}
                        className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center space-x-1"
                      >
                        <RefreshCw className={`h-3 w-3 ${running && activePEP === pep.pep_number ? 'animate-spin' : ''}`} />
                        <span>Re-evaluate this PEP</span>
                      </button>
                    </div>

                    {pep.comparisons?.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">No comparison items recorded.</p>
                    ) : (
                      <div className="space-y-3">
                        {pep.comparisons.map((c, idx) => (
                          <div 
                            key={idx}
                            className={`p-4 rounded-lg border text-xs space-y-2 ${
                              c.status === 'matched' 
                                ? 'bg-emerald-950/10 border-emerald-500/20' 
                                : c.status === 'partial'
                                ? 'bg-amber-950/10 border-amber-500/20'
                                : c.status === 'missed'
                                ? 'bg-rose-950/10 border-rose-500/20'
                                : 'bg-purple-950/10 border-purple-500/20'
                            }`}
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                              <div className="flex items-center space-x-2">
                                {getStatusBadge(c.status)}
                                <span className="text-slate-400 text-[11px]">{c.explanation}</span>
                              </div>
                              {c.confidence > 0 && (
                                <span className="text-[11px] font-mono text-slate-400">
                                  Match Confidence: <strong className="text-slate-200">{(c.confidence * 100).toFixed(0)}%</strong>
                                </span>
                              )}
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-800/60">
                              {/* Left: Ground Truth from PEP */}
                              <div className="space-y-1">
                                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                                  Reference Answer (Official PEP):
                                </span>
                                {c.ground_truth_idea ? (
                                  <>
                                    <p className="font-semibold text-slate-200">{c.ground_truth_idea}</p>
                                    <p className="text-slate-400 leading-relaxed text-[11px]">{c.ground_truth_reason}</p>
                                  </>
                                ) : (
                                  <p className="text-slate-500 italic text-[11px]">Not formally listed in final PEP document.</p>
                                )}
                              </div>

                              {/* Right: Blind Recovered Idea */}
                              <div className="space-y-1">
                                <span className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider block">
                                  Blind Recovered (From Raw Discussion):
                                </span>
                                {c.recovered_idea ? (
                                  <>
                                    <p className="font-semibold text-indigo-200">{c.recovered_idea}</p>
                                    <p className="text-slate-400 leading-relaxed text-[11px]">{c.recovered_reason}</p>
                                  </>
                                ) : (
                                  <p className="text-rose-400/80 italic text-[11px]">Idea was not recovered from the discussion thread.</p>
                                )}
                              </div>
                            </div>

                            {/* Evidence Quote */}
                            {c.evidence_quote && (
                              <div className="mt-2 pt-2 border-t border-slate-800/40 flex items-start space-x-2 text-[11px] text-slate-300 bg-slate-900/50 p-2.5 rounded">
                                <Quote className="h-3.5 w-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                                <div className="space-y-0.5">
                                  <span className="text-indigo-400 font-semibold block text-[10px] uppercase">Grounded Evidence:</span>
                                  <p className="italic text-slate-300">"{c.evidence_quote}"</p>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
