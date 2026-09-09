import React, { useState } from 'react';
import { X, Key, Check, AlertCircle, Database, Cpu, ExternalLink } from 'lucide-react';

export default function ApiKeyModal({ isOpen, onClose, systemStatus, onSaveKey }) {
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);
  const [saveError, setSaveError] = useState(null);

  if (!isOpen) return null;

  const handleSave = async (e) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) return;

    setIsSaving(true);
    setSaveMessage(null);
    setSaveError(null);

    try {
      const res = await fetch('/api/config/key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ apiKey: apiKeyInput.trim() }),
      });

      const data = await res.json();
      if (res.ok) {
        setSaveMessage('API Key updated successfully!');
        setApiKeyInput('');
        if (onSaveKey) onSaveKey();
        setTimeout(() => {
          onClose();
        }, 1200);
      } else {
        setSaveError(data.error || 'Failed to update API key.');
      }
    } catch (err) {
      setSaveError(err.message || 'Network error connecting to backend.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-xs animate-fade-in">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-100 relative">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
            <Key className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">System Configuration</h3>
            <p className="text-xs text-gray-500">Google Gemini & Vector DB status</p>
          </div>
        </div>

        {/* Backend & Vector DB Status */}
        <div className="mb-5 p-3.5 bg-gray-50 rounded-xl space-y-2.5 text-xs border border-gray-200/60">
          <div className="flex items-center justify-between">
            <span className="text-gray-600 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-gray-500" />
              Gemini API Key:
            </span>
            <span className={`font-semibold ${systemStatus?.hasApiKey ? 'text-emerald-600' : 'text-amber-600'}`}>
              {systemStatus?.hasApiKey ? 'Configured & Active' : 'Not Configured'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-600 flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-gray-500" />
              Vector Engine:
            </span>
            <span className="font-semibold text-gray-800 text-[11px] truncate max-w-[200px]" title={systemStatus?.vectorStoreType}>
              {systemStatus?.vectorStoreType || 'Initializing...'}
            </span>
          </div>
        </div>

        {/* Enter API Key Form */}
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Enter Google Gemini API Key
            </label>
            <input
              type="password"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder="AIzaSy..."
              className="w-full px-3.5 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all font-mono"
            />
            <p className="mt-1.5 text-[11px] text-gray-500 flex items-center gap-1">
              <span>You can get a free API key from</span>
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-emerald-600 hover:underline font-medium inline-flex items-center gap-0.5"
              >
                Google AI Studio <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </p>
          </div>

          {saveMessage && (
            <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-700 flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-600" />
              <span>{saveMessage}</span>
            </div>
          )}

          {saveError && (
            <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600" />
              <span>{saveError}</span>
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving || !apiKeyInput.trim()}
              className="flex-1 px-4 py-2 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl transition-colors disabled:opacity-50 shadow-sm"
            >
              {isSaving ? 'Saving...' : 'Save API Key'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
