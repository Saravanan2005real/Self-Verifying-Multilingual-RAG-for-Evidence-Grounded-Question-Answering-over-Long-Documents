import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import ChatArea from './components/ChatArea';
import InputBar from './components/InputBar';
import ApiKeyModal from './components/ApiKeyModal';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

export default function App() {
  const [documentInfo, setDocumentInfo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  // Upload status
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');

  // Chat generation status
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingAnswer, setStreamingAnswer] = useState('');
  const [streamingCitations, setStreamingCitations] = useState([]);

  // System & API Key
  const [systemStatus, setSystemStatus] = useState(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Notification toast
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Fetch system status on load
  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
      }
    } catch (err) {
      console.warn('Backend not yet reachable:', err);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  // Upload file handler
  const handleUpload = async (file) => {
    setIsUploading(true);
    setUploadProgress(`Uploading ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploadProgress('Extracting text & generating embeddings...');
      const res = await fetch('/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Failed to process document.');
      }

      setDocumentInfo({
        documentId: data.documentId,
        fileName: data.fileName,
        fileSize: data.fileSize,
        pageCount: data.pageCount,
        totalChunks: data.totalChunks,
      });

      setMessages([]);
      showToast(`"${data.fileName}" indexed (${data.pageCount} pages, ${data.totalChunks} chunks)`, 'success');
      fetchStatus();
    } catch (err) {
      showToast(err.message || 'Upload failed. Please try again.', 'error');
    } finally {
      setIsUploading(false);
      setUploadProgress('');
    }
  };

  // Chat query submission (Streaming with SSE fallback to JSON)
  const handleSendMessage = async (queryText) => {
    const question = (queryText || input).trim();
    if (!question || !documentInfo || isGenerating) return;

    setInput('');
    const newMessages = [...messages, { role: 'user', content: question }];
    setMessages(newMessages);

    setIsGenerating(true);
    setStreamingAnswer('');
    setStreamingCitations([]);

    const payload = {
      documentId: documentInfo.documentId,
      question,
      history: messages.slice(-6).map(m => ({ role: m.role, content: m.content })),
      stream: true,
    };

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Server responded with ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let fullText = '';
      let collectedCitations = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = 'message';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.substring(6).trim();
          } else if (trimmed.startsWith('data:')) {
            const dataStr = trimmed.substring(5).trim();
            if (!dataStr) continue;

            if (currentEvent === 'token') {
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.token) {
                  fullText += parsed.token;
                  setStreamingAnswer(fullText);
                }
              } catch (e) {
                fullText += dataStr;
                setStreamingAnswer(fullText);
              }
            } else if (currentEvent === 'citations') {
              try {
                collectedCitations = JSON.parse(dataStr);
                setStreamingCitations(collectedCitations);
              } catch (e) {
                console.error('Error parsing citations:', e);
              }
            } else if (currentEvent === 'error') {
              try {
                const parsed = JSON.parse(dataStr);
                throw new Error(parsed.error || 'Streaming error');
              } catch (e) {
                throw new Error(dataStr);
              }
            }
          }
        }
      }

      // Stream finished successfully
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: fullText || "I couldn't find this information in the uploaded document.",
          citations: collectedCitations,
        }
      ]);
    } catch (streamErr) {
      console.warn('Streaming error, falling back to non-streaming chat:', streamErr);

      // Fallback to standard /chat
      try {
        const fallbackRes = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...payload, stream: false }),
        });

        const fallbackData = await fallbackRes.json();
        if (!fallbackRes.ok) {
          throw new Error(fallbackData.error || 'Chat request failed.');
        }

        setMessages([
          ...newMessages,
          {
            role: 'assistant',
            content: fallbackData.answer,
            citations: fallbackData.citations || [],
          }
        ]);
      } catch (fallbackErr) {
        showToast(fallbackErr.message || 'Error generating answer.', 'error');
        setMessages([
          ...newMessages,
          {
            role: 'assistant',
            content: `Error: ${fallbackErr.message || 'Failed to get answer. Please check if your Gemini API key is valid.'}`,
            citations: [],
          }
        ]);
      }
    } finally {
      setIsGenerating(false);
      setStreamingAnswer('');
      setStreamingCitations([]);
    }
  };

  const handleResetChat = () => {
    setMessages([]);
    showToast('Chat history cleared', 'info');
  };

  return (
    <div className="flex flex-col h-screen bg-white text-gray-900">
      {/* Top Navigation */}
      <Navbar
        documentInfo={documentInfo}
        onResetChat={handleResetChat}
        onOpenSettings={() => setIsSettingsOpen(true)}
        systemStatus={systemStatus}
      />

      {/* Main Chat Stream Area */}
      <ChatArea
        messages={messages}
        documentInfo={documentInfo}
        isGenerating={isGenerating}
        streamingAnswer={streamingAnswer}
        streamingCitations={streamingCitations}
        onUploadSuccess={handleUpload}
        isUploading={isUploading}
        uploadProgress={uploadProgress}
        onSelectPrompt={(prompt) => handleSendMessage(prompt)}
      />

      {/* Fixed Bottom Input Area */}
      <InputBar
        input={input}
        setInput={setInput}
        onSubmit={() => handleSendMessage()}
        disabled={isGenerating}
        isStreaming={isGenerating}
        hasDocument={Boolean(documentInfo)}
        onAttachFile={handleUpload}
        isUploading={isUploading}
      />

      {/* Settings Modal */}
      <ApiKeyModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        systemStatus={systemStatus}
        onSaveKey={fetchStatus}
      />

      {/* Floating Toast Notification */}
      {toast && (
        <div
          className={`fixed bottom-24 right-6 z-50 px-4 py-2.5 rounded-xl shadow-lg border text-xs font-medium flex items-center gap-2 animate-fade-in ${
            toast.type === 'error'
              ? 'bg-red-50 border-red-200 text-red-700'
              : toast.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-gray-900 border-gray-800 text-white'
          }`}
        >
          {toast.type === 'error' ? (
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
          ) : toast.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          ) : null}
          <span>{toast.message}</span>
        </div>
      )}
    </div>
  );
}
