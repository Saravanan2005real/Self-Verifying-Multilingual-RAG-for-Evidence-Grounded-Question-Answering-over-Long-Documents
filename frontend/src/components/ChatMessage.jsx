import React, { useState } from 'react';
import { User, Bot, Copy, Check, Sparkles } from 'lucide-react';
import SourceCitations from './SourceCitations';

// Simple lightweight markdown parser for paragraphs, bold, lists, and inline code
function SimpleMarkdown({ text }) {
  if (!text) return null;

  const lines = text.split('\n');
  const elements = [];
  let inList = false;
  let listItems = [];

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="my-2 ml-4 list-disc space-y-1 text-gray-800">
          {listItems.map((item, idx) => (
            <li key={idx}>{parseInline(item)}</li>
          ))}
        </ul>
      );
      listItems = [];
      inList = false;
    }
  };

  const parseInline = (str) => {
    // Replace citations like [Page 1] or [Page 2] with highlighted badges
    const parts = str.split(/(\[Page\s*\d+(?:-\d+)?\]|\*\*.*?\*\*|`.*?`)/g);

    return parts.map((part, index) => {
      if (/^\[Page\s*\d+(?:-\d+)?\]$/.test(part)) {
        return (
          <span
            key={index}
            className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800 mx-1 align-baseline border border-emerald-200"
          >
            {part}
          </span>
        );
      }
      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        return <strong key={index} className="font-semibold text-gray-900">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        return (
          <code key={index} className="px-1.5 py-0.5 bg-gray-100 text-gray-800 text-xs rounded font-mono">
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  lines.forEach((line, i) => {
    const trimmed = line.trim();

    if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      inList = true;
      listItems.push(trimmed.substring(2));
    } else if (/^\d+\.\s/.test(trimmed)) {
      inList = true;
      listItems.push(trimmed.replace(/^\d+\.\s/, ''));
    } else {
      flushList();
      if (trimmed.length > 0) {
        elements.push(
          <p key={i} className="mb-2.5 last:mb-0 leading-relaxed text-gray-800">
            {parseInline(line)}
          </p>
        );
      }
    }
  });

  flushList();

  return <div className="space-y-1">{elements}</div>;
}

export default function ChatMessage({ message, isStreaming }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = () => {
    if (message.content) {
      navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      className={`py-5 px-4 sm:px-6 w-full flex justify-center transition-colors ${
        isUser ? 'bg-transparent' : 'bg-gray-50/70 border-y border-gray-100'
      }`}
    >
      <div className="w-full max-w-3xl flex gap-4 items-start">
        {/* Avatar */}
        <div className="flex-shrink-0 pt-0.5">
          {isUser ? (
            <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center font-medium shadow-sm">
              <User className="w-4 h-4" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center shadow-sm shadow-emerald-200">
              <Bot className="w-4 h-4" />
            </div>
          )}
        </div>

        {/* Message Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className="text-xs font-semibold text-gray-900 tracking-tight">
              {isUser ? 'You' : 'DocQuery AI'}
            </span>

            {!isUser && message.content && (
              <button
                type="button"
                onClick={handleCopy}
                className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors"
                title="Copy response"
              >
                {copied ? (
                  <span className="flex items-center gap-1 text-[11px] text-emerald-600">
                    <Check className="w-3.5 h-3.5" /> Copied
                  </span>
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
            )}
          </div>

          {/* Body */}
          <div className="text-[15px] leading-relaxed break-words text-gray-800">
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <div>
                <SimpleMarkdown text={message.content} />
                {isStreaming && <span className="cursor-blink" />}
              </div>
            )}
          </div>

          {/* Citations section if present */}
          {!isUser && message.citations && message.citations.length > 0 && (
            <SourceCitations citations={message.citations} />
          )}
        </div>
      </div>
    </div>
  );
}
