import React, { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp, ExternalLink, Sparkles } from 'lucide-react';

export default function SourceCitations({ citations }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  if (!citations || citations.length === 0) {
    return null;
  }

  const toggleExpand = (idx) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  return (
    <div className="mt-4 pt-3 border-t border-gray-100">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2.5">
        <BookOpen className="w-3.5 h-3.5 text-emerald-600" />
        <span>Source Citations ({citations.length})</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {citations.map((citation, idx) => {
          const isExpanded = expandedIndex === idx;
          const scorePercent = Math.round((citation.relevanceScore || 0) * 100);

          return (
            <div
              key={idx}
              className={`rounded-lg border transition-all duration-200 text-left overflow-hidden ${
                isExpanded
                  ? 'border-emerald-300 bg-emerald-50/40 shadow-sm'
                  : 'border-gray-200/80 bg-gray-50/50 hover:bg-gray-50 hover:border-gray-300'
              }`}
            >
              <button
                type="button"
                onClick={() => toggleExpand(idx)}
                className="w-full px-3 py-2 text-left flex items-center justify-between gap-2"
                aria-expanded={isExpanded}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800">
                    {citation.pageDisplay || `Page ${citation.startPage}`}
                  </span>
                  {citation.relevanceScore > 0 && (
                    <span className="text-[11px] text-gray-500 truncate">
                      {scorePercent}% match
                    </span>
                  )}
                </div>
                <div className="text-gray-400 hover:text-gray-600 flex-shrink-0">
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </div>
              </button>

              {isExpanded && (
                <div className="px-3 pb-2.5 pt-0.5 text-xs text-gray-700 font-normal leading-relaxed border-t border-emerald-100/70 bg-white/70">
                  <div className="text-[11px] text-gray-400 font-medium mb-1 flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-emerald-600" />
                    Chunk #{citation.chunkIndex} context:
                  </div>
                  <blockquote className="italic border-l-2 border-emerald-500 pl-2 text-gray-600">
                    "{citation.snippet}"
                  </blockquote>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
