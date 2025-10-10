import React, { useState, useEffect } from 'react';
import { X, Download, FileText, Image, File, Loader, AlertCircle, Eye, Copy, CheckCircle } from 'lucide-react';
import { honeyJarApi } from '../../services/knowledgeApi';

const DocumentPreviewModal = ({ isOpen, onClose, document, honeyJarId }) => {
  const [previewContent, setPreviewContent] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copySuccess, setCopySuccess] = useState(false);
  const [viewMode, setViewMode] = useState('preview'); // 'preview' or 'info'

  useEffect(() => {
    if (isOpen && document && viewMode === 'preview') {
      loadPreview();
    }
  }, [isOpen, document, viewMode]);

  const loadPreview = async () => {
    if (!document || !honeyJarId) return;

    setIsLoading(true);
    setError(null);
    setPreviewContent(null);

    try {
      const response = await fetch(
        `/api/knowledge/honey-jars/${honeyJarId}/documents/${document.id}/preview`,
        {
          credentials: 'include',
          headers: {
            'Accept': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to load preview: ${response.status}`);
      }

      const data = await response.json();
      setPreviewContent(data.content || 'No preview available');
    } catch (err) {
      console.error('Error loading document preview:', err);
      setError('Unable to load document preview. The file may be binary or too large.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!document || !honeyJarId) return;

    try {
      const response = await fetch(
        `/api/knowledge/honey-jars/${honeyJarId}/documents/${document.id}/download`,
        {
          credentials: 'include',
        }
      );

      if (!response.ok) {
        throw new Error('Download failed');
      }

      // Get filename from content-disposition header or use document filename
      const contentDisposition = response.headers.get('content-disposition');
      let filename = document.filename;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+?)"?$/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Create blob and trigger download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download error:', err);
      setError('Failed to download document');
    }
  };

  const handleCopyContent = () => {
    if (previewContent) {
      navigator.clipboard.writeText(previewContent);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    return new Date(dateString).toLocaleString();
  };

  const getFileIcon = (filename) => {
    const ext = filename?.split('.').pop()?.toLowerCase();
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'];
    const textExts = ['txt', 'md', 'json', 'xml', 'csv', 'log'];

    if (imageExts.includes(ext)) return <Image className="w-5 h-5" />;
    if (textExts.includes(ext)) return <FileText className="w-5 h-5" />;
    return <File className="w-5 h-5" />;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-800 rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-3">
            {getFileIcon(document?.filename)}
            <div>
              <h2 className="text-lg font-semibold text-white truncate">
                {document?.filename || 'Document Preview'}
              </h2>
              <p className="text-sm text-slate-400">
                {formatBytes(document?.size_bytes)} • {document?.content_type || 'Unknown type'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400 hover:text-white" />
          </button>
        </div>

        {/* View Mode Tabs */}
        <div className="flex gap-2 p-4 border-b border-slate-700">
          <button
            onClick={() => setViewMode('preview')}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
              viewMode === 'preview'
                ? 'bg-yellow-500 text-black'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            <Eye className="w-4 h-4" />
            Preview
          </button>
          <button
            onClick={() => setViewMode('info')}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
              viewMode === 'info'
                ? 'bg-yellow-500 text-black'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            <FileText className="w-4 h-4" />
            Information
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {viewMode === 'preview' ? (
            <div className="h-full flex flex-col">
              {isLoading ? (
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center">
                    <Loader className="w-8 h-8 text-yellow-500 animate-spin mx-auto mb-3" />
                    <p className="text-slate-400">Loading preview...</p>
                  </div>
                </div>
              ) : error ? (
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center max-w-md">
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
                    <p className="text-slate-300 mb-2">Preview Unavailable</p>
                    <p className="text-sm text-slate-400">{error}</p>
                    <button
                      onClick={handleDownload}
                      className="mt-4 px-4 py-2 bg-yellow-500 text-black rounded-lg hover:bg-yellow-600 transition-colors flex items-center gap-2 mx-auto"
                    >
                      <Download className="w-4 h-4" />
                      Download File Instead
                    </button>
                  </div>
                </div>
              ) : previewContent ? (
                <div className="flex-1 flex flex-col">
                  {/* Preview Toolbar */}
                  <div className="flex items-center justify-end gap-2 p-2 bg-slate-900/50">
                    <button
                      onClick={handleCopyContent}
                      className="px-3 py-1 bg-slate-700 text-slate-300 rounded hover:bg-slate-600 transition-colors flex items-center gap-2 text-sm"
                    >
                      {copySuccess ? (
                        <>
                          <CheckCircle className="w-4 h-4 text-green-400" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4" />
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                  {/* Preview Content */}
                  <div className="flex-1 overflow-auto p-4 bg-slate-900">
                    <pre className="text-sm text-slate-300 font-mono whitespace-pre-wrap">
                      {previewContent}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center">
                  <p className="text-slate-400">No preview available</p>
                </div>
              )}
            </div>
          ) : (
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-400 mb-1">Filename</p>
                  <p className="text-white font-medium">{document?.filename}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400 mb-1">File Size</p>
                  <p className="text-white font-medium">{formatBytes(document?.size_bytes)}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400 mb-1">Content Type</p>
                  <p className="text-white font-medium">{document?.content_type || 'Unknown'}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400 mb-1">Upload Date</p>
                  <p className="text-white font-medium">{formatDate(document?.upload_date)}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400 mb-1">Status</p>
                  <p className="text-white font-medium">
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs ${
                      document?.status === 'processed'
                        ? 'bg-green-500/20 text-green-400'
                        : document?.status === 'processing'
                        ? 'bg-yellow-500/20 text-yellow-400'
                        : 'bg-slate-500/20 text-slate-400'
                    }`}>
                      {document?.status || 'Unknown'}
                    </span>
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-400 mb-1">Embeddings</p>
                  <p className="text-white font-medium">{document?.embedding_count || 0}</p>
                </div>
              </div>

              {document?.tags && document.tags.length > 0 && (
                <div>
                  <p className="text-sm text-slate-400 mb-2">Tags</p>
                  <div className="flex flex-wrap gap-2">
                    {document.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-slate-700 text-slate-300 rounded text-sm"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {document?.metadata && Object.keys(document.metadata).length > 0 && (
                <div>
                  <p className="text-sm text-slate-400 mb-2">Metadata</p>
                  <div className="bg-slate-900 rounded p-3">
                    <pre className="text-sm text-slate-300 font-mono">
                      {JSON.stringify(document.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between p-4 border-t border-slate-700">
          <div className="text-sm text-slate-400">
            {viewMode === 'preview' && previewContent && (
              <span>Showing first 10KB of content</span>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleDownload}
              className="px-4 py-2 bg-yellow-500 text-black rounded-lg hover:bg-yellow-600 transition-colors flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentPreviewModal;