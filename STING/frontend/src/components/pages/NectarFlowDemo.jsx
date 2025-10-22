import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import NectarFlow from '../pollen/NectarFlow';
import './NectarFlowDemo.css';

const NectarFlowDemo = () => {
  const navigate = useNavigate();

  return (
    <div className="nectar-flow-demo-page">
      {/* Header */}
      <div className="demo-header">
        <button
          onClick={() => navigate('/dashboard')}
          className="back-button"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Dashboard
        </button>
        <div className="demo-title">
          <h1>Nectar Flow Dashboard Demo</h1>
          <p>Real-time monitoring of knowledge processing pipeline</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="demo-content">
        <div className="demo-container">
          <NectarFlow />
        </div>

        {/* Info Panel */}
        <div className="info-panel">
          <h3>About Nectar Flow</h3>
          <p>
            The Nectar Flow dashboard provides real-time visibility into STING's knowledge 
            processing pipeline. Monitor document ingestion, text extraction, chunking, 
            and embedding generation as they happen.
          </p>
          
          <div className="feature-list">
            <h4>Key Features:</h4>
            <ul>
              <li>Live processing status for active documents</li>
              <li>Queue management and prioritization</li>
              <li>Performance metrics and processing rates</li>
              <li>Error tracking and retry mechanisms</li>
              <li>Multi-format document support (PDF, DOCX, MD, TXT, HTML)</li>
            </ul>
          </div>

          <div className="tech-stack">
            <h4>Technology Stack:</h4>
            <ul>
              <li>FastAPI backend for async processing</li>
              <li>Chroma DB for vector storage</li>
              <li>Sentence transformers for embeddings</li>
              <li>Redis queue for job management</li>
              <li>WebSocket updates for real-time status</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NectarFlowDemo;