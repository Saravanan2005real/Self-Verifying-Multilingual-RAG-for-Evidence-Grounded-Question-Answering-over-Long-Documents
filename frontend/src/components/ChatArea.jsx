import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import UploadDropzone from './UploadDropzone';
import { Sparkles, FileText, Bot, HelpCircle, ArrowRight } from 'lucide-react';

export default function ChatArea({
  messages,
  documentInfo,
  isGenerating,
  streamingAnswer,
  streamingCitations,
  onUploadSuccess,
  isUploading,
  uploadProgress,
  onSelectPrompt
}) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingAnswer, isGenerating]);

  // Suggested starter prompts
  const starterPrompts = [
    "Summarize the entire document in 3 key points.",
    "What are the main rules, obligations, or policies mentioned?",
    "List all dates, deadlines, and key numbers found in the file.",
    "What is the single most important takeaway from this document?"
  ];

  return (
    <div className="flex-1 overflow-y-auto pb-4 pt-2">
      {/* State 1: No document uploaded yet */}
      {!documentInfo && (
        <div className="max-w-2xl mx-auto px-4 py-8 sm:py-12 flex flex-col items-center text-center animate-fade-in">
          <div className="w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-5 shadow-xs border border-emerald-100">
            <Sparkles className="w-7 h-7" />
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 tracking-tight mb-2.5">
            Chat with your PDF or DOCX
          </h1>
          <p className="text-gray-500 text-sm sm:text-base max-w-md mb-8 leading-relaxed">
            Upload your document to ask questions. DocQuery AI uses Retrieval-Augmented Generation (RAG) to provide exact answers with page citations.
          </p>

          <div className="w-full">
            <UploadDropzone
              onUploadSuccess={onUploadSuccess}
              isUploading={isUploading}
              uploadProgress={uploadProgress}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full mt-10 text-left">
            <div className="p-4 rounded-xl bg-gray-50/70 border border-gray-100">
              <div className="text-xs font-semibold text-gray-900 mb-1 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Pure Document RAG
              </div>
              <p className="text-xs text-gray-500 leading-relaxed">
                Answers only from your file. No hallucinations or outside assumptions.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-gray-50/70 border border-gray-100">
              <div className="text-xs font-semibold text-gray-900 mb-1 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Exact Page Citations
              </div>
              <p className="text-xs text-gray-500 leading-relaxed">
                Every factual claim references the specific page and source excerpt.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-gray-50/70 border border-gray-100">
              <div className="text-xs font-semibold text-gray-900 mb-1 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                100% Local & Private
              </div>
              <p className="text-xs text-gray-500 leading-relaxed">
                No external API or credit card required. Works completely on your machine.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* State 2: Document uploaded, but no conversation started */}
      {documentInfo && messages.length === 0 && (
        <div className="max-w-2xl mx-auto px-4 py-8 sm:py-12 animate-fade-in text-center">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200/80 text-emerald-800 text-xs font-medium mb-4">
            <FileText className="w-4 h-4 text-emerald-600" />
            <span className="font-semibold">{documentInfo.fileName}</span>
            <span className="text-emerald-400">|</span>
            <span>{documentInfo.pageCount} {documentInfo.pageCount === 1 ? 'page' : 'pages'}</span>
            <span className="text-emerald-400">|</span>
            <span>{documentInfo.totalChunks} chunks indexed</span>
          </div>

          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight mb-2">
            Ready to explore your document
          </h2>
          <p className="text-gray-500 text-sm max-w-md mx-auto mb-8">
            Type any question below or click a starter suggestion to begin.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left">
            {starterPrompts.map((prompt, i) => (
              <button
                key={i}
                type="button"
                onClick={() => onSelectPrompt(prompt)}
                className="p-3.5 rounded-xl border border-gray-200/80 bg-white hover:border-emerald-400 hover:bg-emerald-50/20 transition-all text-xs font-medium text-gray-700 hover:text-gray-900 flex items-center justify-between group shadow-2xs"
              >
                <span className="line-clamp-2">{prompt}</span>
                <ArrowRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-emerald-600 flex-shrink-0 ml-2 transition-transform group-hover:translate-x-0.5" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* State 3: Active conversation */}
      {documentInfo && messages.length > 0 && (
        <div className="w-full">
          {messages.map((msg, index) => (
            <ChatMessage key={index} message={msg} isStreaming={false} />
          ))}

          {/* Real-time Streaming message */}
          {isGenerating && streamingAnswer && (
            <ChatMessage
              message={{
                role: 'assistant',
                content: streamingAnswer,
                citations: streamingCitations
              }}
              isStreaming={true}
            />
          )}

          {/* Thinking / Loading indicator when awaiting stream start */}
          {isGenerating && !streamingAnswer && (
            <div className="py-5 px-4 sm:px-6 w-full flex justify-center bg-gray-50/70 border-y border-gray-100">
              <div className="w-full max-w-3xl flex gap-4 items-start">
                <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm shadow-emerald-200">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="pt-1.5 flex items-center gap-2">
                  <span className="text-xs font-semibold text-gray-500">Searching document & thinking</span>
                  <div className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  );
}
