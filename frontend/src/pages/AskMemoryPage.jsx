import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Send, 
  Loader2, 
  ExternalLink, 
  Quote, 
  BookOpen, 
  CheckCircle, 
  AlertCircle,
  Copy,
  Check,
  Search,
  KeyRound,
  HelpCircle
} from 'lucide-react';
import apiService from '../services/api';
import MarkdownRenderer from '../components/MarkdownRenderer';

const DEFAULT_QUESTIONS = [
  "What were the key architectural decisions made recently?",
  "What alternatives were rejected and why?",
  "What were the main trade-offs discussed?",
  "What UI or dependency choices were standardized?",
];

export default function AskMemoryPage({ currentRepo }) {
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState(DEFAULT_QUESTIONS);
  const [healthInfo, setHealthInfo] = useState(null);

  // Fetch repository decisions to generate tailored suggested questions
  useEffect(() => {
    if (!currentRepo) return;
    
    // Check system health
    apiService.getHealth().then(setHealthInfo).catch(console.error);

    // Fetch decisions for this repo
    apiService.getDecisions(currentRepo.id, { limit: 5 })
      .then((res) => {
        if (res.decisions && res.decisions.length > 0) {
          const dynamicQs = res.decisions.slice(0, 4).map((d) => {
            const title = d.decision;
            if (title.toLowerCase().startsWith('use')) {
              return `Why was it decided to ${title.toLowerCase()}?`;
            } else if (title.toLowerCase().startsWith('bump') || title.toLowerCase().includes('next')) {
              return `What was the reason for ${title}?`;
            } else {
              return `What was decided regarding: "${title}"?`;
            }
          });
          setSuggestedQuestions(dynamicQs);
        } else {
          setSuggestedQuestions(DEFAULT_QUESTIONS);
        }
      })
      .catch((err) => {
        console.error(err);
        setSuggestedQuestions(DEFAULT_QUESTIONS);
      });
  }, [currentRepo?.id]);

  const handleAsk = async (queryText) => {
    const q = (queryText || question).trim();
    if (!q || !currentRepo) return;

    setLoading(true);
    const userMessage = { role: 'user', content: q };
    setHistory((prev) => [...prev, userMessage]);
    setQuestion('');

    try {
      const response = await apiService.askQuestion(currentRepo.id, q);
      setHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          citations: response.citations || [],
          decisions: response.decisions_used || [],
          evidenceFound: response.evidence_found,
          strategy: response.search_strategy,
          confidence: response.confidence,
        },
      ]);
    } catch (err) {
      console.error(err);
      setHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'An error occurred while querying project memory. Please check your network or try again.',
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  if (!currentRepo) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center text-slate-400">
        Please connect or select a repository to ask project memory.
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Ask Project Memory</h1>
            <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">
              {currentRepo.full_name}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Semantic search & AI grounded strictly on real historical discussions, PRs, and decisions.
          </p>
        </div>

        <div className="flex items-center space-x-3 text-xs text-slate-400">
          <span className="flex items-center space-x-1.5">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Question-First Live Retrieval</span>
          </span>
        </div>
      </div>

      {/* API Key Status Notice */}
      {healthInfo && !healthInfo.services?.gemini_configured && (
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <KeyRound className="h-4 w-4 text-amber-400 flex-shrink-0" />
            <span>
              <strong>Tip:</strong> Running in rule-based heuristic mode. To unlock Gemini 2.5 flash reasoning, set <code>GEMINI_API_KEY</code> in <code>backend/.env</code>.
            </span>
          </div>
        </div>
      )}

      {/* Suggested Questions based on actual repo content */}
      {history.length === 0 && (
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
            <Sparkles className="h-4 w-4 text-indigo-400" />
            <span>Relevant Questions for {currentRepo.name}</span>
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {suggestedQuestions.map((sq, i) => (
              <button
                key={i}
                onClick={() => handleAsk(sq)}
                className="text-left p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-800/40 text-xs text-slate-300 transition-all flex items-center justify-between group"
              >
                <span className="line-clamp-2">"{sq}"</span>
                <Send className="h-3 w-3 text-slate-500 group-hover:text-indigo-400 transition-colors ml-2 flex-shrink-0" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Conversation Thread */}
      <div className="space-y-6">
        {history.map((msg, idx) => (
          <div
            key={idx}
            className={`flex flex-col ${
              msg.role === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            {msg.role === 'user' ? (
              <div className="max-w-2xl px-5 py-3.5 rounded-2xl bg-indigo-600 text-white text-sm font-medium shadow-md">
                {msg.content}
              </div>
            ) : (
              <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                  <div className="flex items-center space-x-2">
                    <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                      <Sparkles className="h-4 w-4" />
                    </div>
                    <span className="text-xs font-bold text-slate-200">DecisionTrail Intelligence</span>
                    {msg.strategy && (
                      <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                        msg.strategy === 'ai_general_knowledge'
                          ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                          : 'bg-slate-800 text-slate-400'
                      }`}>
                        {msg.strategy === 'ai_general_knowledge' ? 'Architectural Insight' : msg.strategy}
                      </span>
                    )}
                    {msg.strategy === 'ai_general_knowledge' && (
                      <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        No Direct Repo ADR
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => copyToClipboard(msg.content, idx)}
                    className="text-slate-400 hover:text-slate-200 p-1 rounded transition-colors"
                    title="Copy Answer"
                  >
                    {copiedIndex === idx ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                  </button>
                </div>

                {/* Answer body with Markdown formatting */}
                <div className="max-w-none text-sm text-slate-200">
                  <MarkdownRenderer content={msg.content} />
                </div>

                {/* Citations and Evidence */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-800 space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                      <BookOpen className="h-3.5 w-3.5 text-indigo-400" />
                      <span>Historical Citations & Evidence</span>
                    </p>
                    <div className="grid grid-cols-1 gap-2.5">
                      {msg.citations.map((c, cIdx) => (
                        <div
                          key={cIdx}
                          className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col sm:flex-row sm:items-start justify-between gap-3 text-xs"
                        >
                          <div className="space-y-1">
                            <span className="font-semibold text-indigo-300">
                              {c.decision_title}
                            </span>
                            {c.evidence_snippet && (
                              <p className="text-slate-400 italic line-clamp-2">
                                "{c.evidence_snippet}"
                              </p>
                            )}
                          </div>
                          <a
                            href={c.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center space-x-1 text-slate-400 hover:text-white font-mono flex-shrink-0 self-start"
                          >
                            <span>View Source</span>
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex items-center space-x-3 text-slate-400 text-sm">
            <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
            <span>Consulting project memory, vector index, and discussions...</span>
          </div>
        )}
      </div>

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleAsk();
        }}
        className="sticky bottom-6 pt-2"
      >
        <div className="relative flex items-center shadow-2xl">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={`Ask about decisions in ${currentRepo.name}...`}
            disabled={loading}
            className="w-full pl-5 pr-28 py-4 bg-slate-900/95 backdrop-blur-md border border-slate-700/80 rounded-2xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-sans"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="absolute right-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold rounded-xl transition-all shadow-md flex items-center space-x-1.5"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            <span>Ask</span>
          </button>
        </div>
      </form>
    </div>
  );
}
