import React, { useRef, useEffect } from 'react';
import { Paperclip, ArrowUp, Loader2 } from 'lucide-react';

export default function InputBar({
  input,
  setInput,
  onSubmit,
  disabled,
  isStreaming,
  hasDocument,
  onAttachFile,
  isUploading
}) {
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [input]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !disabled && !isStreaming) {
        onSubmit(e);
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onAttachFile(e.target.files[0]);
    }
  };

  const canSubmit = input.trim().length > 0 && !disabled && !isStreaming && hasDocument;

  return (
    <div className="sticky bottom-0 z-20 w-full bg-gradient-to-t from-white via-white/95 to-transparent pb-4 pt-2">
      <div className="max-w-3xl mx-auto px-4 sm:px-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (canSubmit) onSubmit(e);
          }}
          className="relative bg-white border border-gray-200/90 rounded-2xl shadow-lg shadow-gray-200/40 focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all duration-200 flex items-end p-2 gap-2"
        >
          {/* Hidden file input for attachment icon */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={handleFileChange}
            className="hidden"
            disabled={isUploading}
          />

          {/* Attachment Paperclip Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-colors flex-shrink-0 disabled:opacity-50"
            title={hasDocument ? "Change uploaded document" : "Upload document (PDF or DOCX)"}
          >
            {isUploading ? (
              <Loader2 className="w-5 h-5 text-emerald-600 animate-spin" />
            ) : (
              <Paperclip className="w-5 h-5" />
            )}
          </button>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              !hasDocument
                ? "Upload a document first to start chatting..."
                : "Ask anything about your file..."
            }
            disabled={disabled || !hasDocument}
            className="w-full resize-none max-h-40 py-2.5 px-1 bg-transparent border-0 focus:ring-0 text-sm sm:text-base text-gray-900 placeholder:text-gray-400 focus:outline-none disabled:opacity-50"
          />

          {/* Send Button */}
          <button
            type="submit"
            disabled={!canSubmit}
            className={`p-2 rounded-xl flex-shrink-0 transition-all duration-200 ${
              canSubmit
                ? 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm shadow-emerald-300'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
            title="Send question"
          >
            {isStreaming ? (
              <div className="w-5 h-5 flex items-center justify-center">
                <span className="w-2.5 h-2.5 bg-gray-500 rounded-sm animate-pulse" />
              </div>
            ) : (
              <ArrowUp className="w-5 h-5" />
            )}
          </button>
        </form>

        {/* Small sub-text */}
        <p className="text-center text-[11px] text-gray-400 mt-2">
          DocQuery AI uses RAG to answer only from your uploaded file. Page citations are verified.
        </p>
      </div>
    </div>
  );
}
