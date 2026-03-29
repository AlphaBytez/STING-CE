import React, { useState } from 'react';
import { Database, X, Loader2 } from 'lucide-react';
import { externalAiApi } from '../../services/externalAiApi';

/**
 * Modal for promoting a session jar to a permanent honey jar.
 * Shows when user clicks "Promote" on the session jar indicator.
 */
const SessionJarPromoteModal = ({ conversationId, sessionJar, onClose, onPromoted }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [generateSummary, setGenerateSummary] = useState(true);
  const [isPromoting, setIsPromoting] = useState(false);
  const [error, setError] = useState(null);

  const handlePromote = async () => {
    setIsPromoting(true);
    setError(null);
    try {
      const result = await externalAiApi.sessionJar.promote(conversationId, {
        name: name || undefined,
        description: description || undefined,
        generate_summary: generateSummary
      });
      if (onPromoted) onPromoted(result);
      onClose();
    } catch (err) {
      setError(err.response?.data?.error || 'Promotion failed');
    } finally {
      setIsPromoting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 border border-gray-600 rounded-xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-2 text-yellow-400">
            <Database className="w-5 h-5" />
            <h3 className="text-lg font-semibold">Promote to Honey Jar</h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <p className="text-sm text-gray-300">
            This will convert {sessionJar?.file_count || 0} uploaded file(s) into a permanent
            Honey Jar knowledge base you can use across conversations and reports.
          </p>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="My Research Files"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-yellow-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Description (optional)</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Files from my chat session about..."
              rows={2}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-yellow-500 resize-none"
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={generateSummary}
              onChange={e => setGenerateSummary(e.target.checked)}
              className="rounded border-gray-600 text-yellow-500 focus:ring-yellow-500"
            />
            Generate AI conversation summary document
          </label>

          {error && (
            <div className="p-2 bg-red-900/50 border border-red-700 rounded text-sm text-red-300">
              {error}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 p-4 border-t border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white rounded-lg"
            disabled={isPromoting}
          >
            Cancel
          </button>
          <button
            onClick={handlePromote}
            disabled={isPromoting}
            className="px-4 py-2 text-sm bg-yellow-500 hover:bg-yellow-400 text-black font-medium rounded-lg flex items-center gap-2 disabled:opacity-50"
          >
            {isPromoting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Promoting...
              </>
            ) : (
              <>
                <Database className="w-4 h-4" />
                Promote
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SessionJarPromoteModal;
