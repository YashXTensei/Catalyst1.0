import React from 'react';
import ReactMarkdown from 'react-markdown';

export default function MarkdownRenderer({ content }) {
  if (!content) return null;

  return (
    <div className="markdown-content text-sm text-slate-200 leading-relaxed space-y-2">
      <ReactMarkdown
        components={{
          h1: ({ node, ...props }) => <h1 className="text-lg font-bold text-white mt-4 mb-2 tracking-tight" {...props} />,
          h2: ({ node, ...props }) => <h2 className="text-base font-bold text-white mt-3.5 mb-1.5 tracking-tight border-b border-slate-800 pb-1" {...props} />,
          h3: ({ node, ...props }) => <h3 className="text-sm font-bold text-indigo-300 mt-3 mb-1" {...props} />,
          p: ({ node, ...props }) => <p className="mb-2 leading-relaxed text-slate-200" {...props} />,
          strong: ({ node, ...props }) => <strong className="font-bold text-white" {...props} />,
          em: ({ node, ...props }) => <em className="italic text-slate-300" {...props} />,
          ul: ({ node, ...props }) => <ul className="list-disc pl-5 space-y-1 my-2 text-slate-300" {...props} />,
          ol: ({ node, ...props }) => <ol className="list-decimal pl-5 space-y-1 my-2 text-slate-300" {...props} />,
          li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
          blockquote: ({ node, ...props }) => (
            <blockquote className="border-l-2 border-indigo-500/70 pl-3 py-1 my-2 italic text-slate-400 bg-slate-950/40 rounded-r" {...props} />
          ),
          code: ({ node, inline, className, children, ...props }) => (
            <code
              className="px-1.5 py-0.5 rounded bg-slate-800/90 text-indigo-300 font-mono text-xs border border-slate-700/60"
              {...props}
            >
              {children}
            </code>
          ),
          a: ({ node, href, children, ...props }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-indigo-400 hover:text-indigo-300 underline font-mono text-xs transition-colors"
              {...props}
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
