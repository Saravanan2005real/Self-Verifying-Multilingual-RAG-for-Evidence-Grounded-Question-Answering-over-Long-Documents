import React from 'react';
import { FileText, Sparkles, Key, RefreshCw, Layers, CheckCircle2, AlertCircle } from 'lucide-react';

export default function Navbar({
  documentInfo,
  onResetChat,
  onOpenSettings,
  systemStatus
}) {
  return (
    <header className="sticky top-0 z-30 w-full bg-white/90 backdrop-blur-md border-b border-gray-200/80 transition-all">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-sm shadow-emerald-200">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900 text-base tracking-tight">DocQuery AI</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60 uppercase tracking-wider">
                RAG
              </span>
            </div>
          </div>
        </div>

        {/* Center: Uploaded Document Pill (if uploaded) */}
        {documentInfo && (
          <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-gray-50 border border-gray-200 rounded-full text-xs text-gray-700 shadow-xs max-w-xs truncate">
            <FileText className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
            <span className="font-medium truncate" title={documentInfo.fileName}>
              {documentInfo.fileName}
            </span>
            <span className="text-gray-400">•</span>
            <span className="text-gray-500 flex-shrink-0">
              {documentInfo.pageCount} {documentInfo.pageCount === 1 ? 'page' : 'pages'}
            </span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* New Chat Button */}
          {documentInfo && (
            <button
              type="button"
              onClick={onResetChat}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
              title="Clear chat messages"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">New Chat</span>
            </button>
          )}

          {/* Local / Offline Status Pill */}
          <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-emerald-700 bg-emerald-50 rounded-full border border-emerald-200/60">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>Local Engine Active</span>
          </div>
        </div>
      </div>
    </header>
  );
}
