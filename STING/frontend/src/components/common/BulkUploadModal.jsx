import React, { useState, useEffect } from 'react';
import { 
  Upload, 
  Folder, 
  X, 
  Settings, 
  FileText, 
  CheckCircle, 
  AlertCircle,
  Clock,
  Zap
} from 'lucide-react';
import { honeyJarApi } from '../../services/knowledgeApi';

const BulkUploadModal = ({ isOpen, onClose, honeyJarId, honeyJarName }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadId, setUploadId] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [progress, setProgress] = useState({ processed: 0, total_files: 0, percentage: 0 });
  const [error, setError] = useState(null);
  const [showOptions, setShowOptions] = useState(false);
  const [options, setOptions] = useState({
    include_patterns: ['*.md', '*.txt', '*.pdf', '*.doc', '*.docx', '*.json', '*.html'],
    exclude_patterns: ['.git', 'node_modules', '*.tmp', '.DS_Store', '*.log'],
    retention_policy: 'permanent',
    metadata: {
      source: 'Bulk Upload',
      category: 'documents'
    }
  });
  const [polling, setPolling] = useState(false);

  // File input handler
  const handleFileSelect = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      // Check if it's an archive file
      const allowedTypes = [
        'application/zip',
        'application/x-zip-compressed',
        'application/gzip',
        'application/x-tar',
        'application/x-compressed-tar'
      ];
      const allowedExtensions = ['.zip', '.tar', '.tar.gz', '.tgz'];
      
      const isValidType = allowedTypes.includes(file.type) || 
                         allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
      
      if (!isValidType) {
        setError('Please select a valid archive file (.zip, .tar, .tar.gz, .tgz)');
        return;
      }
      
      setSelectedFile(file);
      setError(null);
    }
  };

  // Start upload
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setError(null);
    setUploadStatus('uploading');
    
    try {
      const response = await honeyJarApi.uploadDirectory(honeyJarId, selectedFile, options);
      setUploadId(response.upload_id);
      setUploadStatus('processing');
      setPolling(true);
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.response?.data?.detail || 'Failed to start bulk upload');
      setUploadStatus(null);
    }
  };

  // Poll for upload status
  useEffect(() => {
    let interval = null;
    
    if (polling && uploadId) {
      interval = setInterval(async () => {
        try {
          const status = await honeyJarApi.getBulkUploadStatus(uploadId);
          
          setProgress({
            processed: status.progress?.processed || 0,
            total_files: status.progress?.total_files || 0,
            successful: status.progress?.successful || 0,
            failed: status.progress?.failed || 0,
            percentage: status.progress?.percentage || 0
          });

          if (status.status === 'completed') {
            setUploadStatus('completed');
            setPolling(false);
          } else if (status.status === 'failed') {
            setUploadStatus('failed');
            setError(status.error || 'Upload failed');
            setPolling(false);
          }
        } catch (err) {
          console.error('Status polling error:', err);
          setError('Failed to get upload status');
          setPolling(false);
        }
      }, 2000); // Poll every 2 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [polling, uploadId]);

  // Close modal
  const handleClose = () => {
    if (uploadStatus === 'uploading' || uploadStatus === 'processing') {
      if (!window.confirm('Upload is in progress. Are you sure you want to close?')) {
        return;
      }
    }
    
    setPolling(false);
    setSelectedFile(null);
    setUploadId(null);
    setUploadStatus(null);
    setProgress({ processed: 0, total_files: 0, percentage: 0 });
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-500/20 rounded-lg">
              <Folder className="w-6 h-6 text-yellow-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Bulk Directory Upload</h2>
              <p className="text-sm text-gray-400">Upload to: {honeyJarName}</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            disabled={uploadStatus === 'uploading' || uploadStatus === 'processing'}
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* File Selection */}
          {!uploadStatus && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                Select Archive File
              </label>
              
              <div className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center hover:border-slate-500 transition-colors">
                <input
                  type="file"
                  accept=".zip,.tar,.tar.gz,.tgz"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="bulk-upload-file"
                />
                <label htmlFor="bulk-upload-file" className="cursor-pointer">
                  <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-white font-medium mb-2">
                    {selectedFile ? selectedFile.name : 'Choose archive file'}
                  </p>
                  <p className="text-sm text-gray-400">
                    Supports .zip, .tar, .tar.gz, .tgz files
                  </p>
                  {selectedFile && (
                    <p className="text-xs text-green-400 mt-2">
                      Size: {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  )}
                </label>
              </div>
            </div>
          )}

          {/* Upload Options */}
          {!uploadStatus && (
            <div>
              <button
                onClick={() => setShowOptions(!showOptions)}
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                <Settings className="w-4 h-4" />
                Upload Options
              </button>
              
              {showOptions && (
                <div className="mt-4 space-y-4 sting-glass-medium rounded-lg p-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-2">Include Patterns</label>
                    <input
                      type="text"
                      value={options.include_patterns.join(', ')}
                      onChange={(e) => setOptions(prev => ({
                        ...prev,
                        include_patterns: e.target.value.split(',').map(s => s.trim())
                      }))}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded text-white text-sm"
                      placeholder="*.md, *.txt, *.pdf"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-xs text-gray-400 mb-2">Exclude Patterns</label>
                    <input
                      type="text"
                      value={options.exclude_patterns.join(', ')}
                      onChange={(e) => setOptions(prev => ({
                        ...prev,
                        exclude_patterns: e.target.value.split(',').map(s => s.trim())
                      }))}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded text-white text-sm"
                      placeholder=".git, node_modules, *.tmp"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-gray-400 mb-2">Source Label</label>
                    <input
                      type="text"
                      value={options.metadata.source}
                      onChange={(e) => setOptions(prev => ({
                        ...prev,
                        metadata: { ...prev.metadata, source: e.target.value }
                      }))}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded text-white text-sm"
                      placeholder="e.g., Documentation, Code Base"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Upload Progress */}
          {uploadStatus && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                {uploadStatus === 'uploading' && (
                  <>
                    <div className="animate-spin w-5 h-5 border-2 border-yellow-400 border-t-transparent rounded-full"></div>
                    <span className="text-white">Uploading archive...</span>
                  </>
                )}
                {uploadStatus === 'processing' && (
                  <>
                    <Clock className="w-5 h-5 text-blue-400" />
                    <span className="text-white">Processing files...</span>
                  </>
                )}
                {uploadStatus === 'completed' && (
                  <>
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    <span className="text-white">Upload completed!</span>
                  </>
                )}
                {uploadStatus === 'failed' && (
                  <>
                    <AlertCircle className="w-5 h-5 text-red-400" />
                    <span className="text-white">Upload failed</span>
                  </>
                )}
              </div>

              {uploadStatus === 'processing' && (
                <div>
                  <div className="flex items-center justify-between text-sm text-gray-400 mb-2">
                    <span>Progress</span>
                    <span>{progress.processed}/{progress.total_files} files ({progress.percentage}%)</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div 
                      className="bg-yellow-400 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${progress.percentage}%` }}
                    ></div>
                  </div>
                  {progress.successful > 0 && (
                    <div className="mt-2 text-xs text-green-400">
                      ✓ {progress.successful} successful
                      {progress.failed > 0 && <span className="text-red-400 ml-2">✗ {progress.failed} failed</span>}
                    </div>
                  )}
                </div>
              )}

              {uploadStatus === 'completed' && (
                <div className="bg-green-900/20 border border-green-800/50 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-green-300 mb-2">
                    <Zap className="w-4 h-4" />
                    <span className="font-medium">Upload Summary</span>
                  </div>
                  <div className="text-sm space-y-1">
                    <div>✓ {progress.successful} files processed successfully</div>
                    {progress.failed > 0 && <div>✗ {progress.failed} files failed</div>}
                    <div className="text-green-400/80">Documents are now available in the honey jar</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-red-300">
                <AlertCircle className="w-4 h-4" />
                <span className="font-medium">Error</span>
              </div>
              <p className="text-sm text-red-400 mt-2">{error}</p>
            </div>
          )}

          {/* Instructions */}
          {!uploadStatus && (
            <div className="bg-blue-900/20 border border-blue-800/50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-blue-300 mb-2">
                <FileText className="w-4 h-4" />
                <span className="font-medium">How to prepare your archive:</span>
              </div>
              <ul className="text-sm text-blue-200 space-y-1 ml-6 list-disc">
                <li>Create a .zip, .tar, or .tar.gz file of your directory</li>
                <li>Include files you want to upload (documents, markdown, etc.)</li>
                <li>The archive will be extracted and files processed automatically</li>
                <li>Files matching exclude patterns will be skipped</li>
              </ul>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-slate-700">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
            disabled={uploadStatus === 'uploading' || uploadStatus === 'processing'}
          >
            {uploadStatus === 'completed' ? 'Close' : 'Cancel'}
          </button>
          {!uploadStatus && (
            <button
              onClick={handleUpload}
              disabled={!selectedFile}
              className="px-6 py-2 bg-yellow-500 text-black rounded-lg hover:bg-yellow-400 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Start Upload
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default BulkUploadModal;