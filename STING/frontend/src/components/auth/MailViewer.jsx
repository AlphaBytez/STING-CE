import React, { useState, useEffect } from 'react';
import axios from 'axios';

/**
 * MailViewer - A component for viewing verification emails sent by Kratos
 * Connects to Mailpit API to fetch and display emails
 */
const MailViewer = () => {
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [verificationLinks, setVerificationLinks] = useState([]);
  
  // Mailpit API URL - Use environment variable if available
  const mailpitUrl = window.env?.REACT_APP_MAILPIT_URL || 'http://localhost:8026';
  
  // Fetch emails from Mailpit
  const fetchEmails = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await axios.get(`${mailpitUrl}/api/v1/messages`, {
        headers: {
          'Accept': 'application/json',
        }
      });
      
      setEmails(response.data.messages || []);
    } catch (err) {
      console.error('Error fetching emails:', err);
      setError(`Failed to fetch emails: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Fetch email details
  const fetchEmailDetails = async (id) => {
    try {
      const response = await axios.get(`${mailpitUrl}/api/v1/message/${id}`, {
        headers: {
          'Accept': 'application/json',
        }
      });
      
      setSelectedEmail(response.data);
      
      // Extract verification links from HTML body
      if (response.data.HTML) {
        extractVerificationLinks(response.data.HTML);
      }
    } catch (err) {
      console.error('Error fetching email details:', err);
      setError(`Failed to fetch email details: ${err.message}`);
    }
  };
  
  // Extract verification links from HTML content
  const extractVerificationLinks = (html) => {
    const links = [];
    const regex = /<a\s+(?:[^>]*?\s+)?href=(["'])(https?:\/\/[^"']+verification[^"']*)\1/gi;
    let match;
    
    while ((match = regex.exec(html)) !== null) {
      links.push(match[2]);
    }
    
    setVerificationLinks(links);
  };
  
  // Open verification link in new tab
  const openVerificationLink = (link) => {
    window.open(link, '_blank');
  };
  
  // Refresh emails periodically
  useEffect(() => {
    fetchEmails();
    
    // Set up polling for new emails every 5 seconds
    const interval = setInterval(() => {
      fetchEmails();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="bg-gray-800 text-white p-6 rounded-lg shadow-lg">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Verification Emails</h2>
        <button 
          onClick={fetchEmails}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
        >
          Refresh
        </button>
      </div>
      
      {error && (
        <div className="bg-red-900 bg-opacity-30 border border-red-800 p-3 rounded mb-4">
          <p className="text-red-400">{error}</p>
          <p className="text-sm mt-2">
            Make sure Mailpit is running and accessible at {mailpitUrl}
          </p>
        </div>
      )}
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Email List */}
        <div className="md:col-span-1 bg-gray-700 p-4 rounded h-96 overflow-y-auto">
          <h3 className="font-medium mb-3 text-yellow-400">Recent Emails</h3>
          
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400"></div>
            </div>
          ) : emails.length === 0 ? (
            <p className="text-gray-400">No emails found</p>
          ) : (
            <ul className="space-y-2">
              {emails.map(email => (
                <li 
                  key={email.ID}
                  onClick={() => fetchEmailDetails(email.ID)}
                  className={`p-2 rounded cursor-pointer border transition-colors ${
                    selectedEmail?.ID === email.ID ? 
                    'bg-blue-800 border-blue-600' : 
                    'hover:bg-gray-600 border-transparent'
                  }`}
                >
                  <div className="text-sm font-medium truncate">{email.Subject || '(No Subject)'}</div>
                  <div className="text-xs text-gray-400 mt-1">
                    <span>From: {email.From?.Address || 'Unknown'}</span>
                    <span className="block">To: {email.To?.map(t => t.Address).join(', ') || 'Unknown'}</span>
                    <span className="block text-right text-gray-500">
                      {new Date(email.Created).toLocaleString()}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        
        {/* Email Content */}
        <div className="md:col-span-2 bg-gray-700 p-4 rounded h-96 overflow-y-auto">
          <h3 className="font-medium mb-3 text-yellow-400">Email Content</h3>
          
          {!selectedEmail ? (
            <p className="text-gray-400">Select an email to view its content</p>
          ) : (
            <div>
              <div className="mb-3">
                <h4 className="font-medium">{selectedEmail.Subject || '(No Subject)'}</h4>
                <div className="text-sm text-gray-400">
                  <div>From: {selectedEmail.From?.Address || 'Unknown'}</div>
                  <div>To: {selectedEmail.To?.map(t => t.Address).join(', ') || 'Unknown'}</div>
                  <div>Date: {new Date(selectedEmail.Created).toLocaleString()}</div>
                </div>
              </div>
              
              <hr className="border-gray-600 my-3" />
              
              {/* Verification Links */}
              {verificationLinks.length > 0 && (
                <div className="mb-4 bg-green-900 bg-opacity-30 p-3 rounded border border-green-700">
                  <h5 className="font-medium text-green-400 mb-2">Verification Links</h5>
                  <ul className="space-y-2">
                    {verificationLinks.map((link, index) => (
                      <li key={index}>
                        <button
                          onClick={() => openVerificationLink(link)}
                          className="text-blue-400 hover:text-blue-300 underline text-sm"
                        >
                          {link.length > 60 ? `${link.substring(0, 60)}...` : link}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Email Body */}
              <div className="bg-gray-800 p-3 rounded">
                {selectedEmail.HTML ? (
                  <div 
                    className="prose prose-sm max-w-none prose-invert"
                    dangerouslySetInnerHTML={{ __html: selectedEmail.HTML }}
                  />
                ) : selectedEmail.Text ? (
                  <pre className="whitespace-pre-wrap text-sm">{selectedEmail.Text}</pre>
                ) : (
                  <p className="text-gray-400">No content</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      
      <div className="mt-4 text-sm text-gray-400">
        <p>
          Note: You can also access the Mailpit UI directly at{' '}
          <a 
            href={mailpitUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:underline"
          >
            {mailpitUrl}
          </a>
        </p>
      </div>
    </div>
  );
};

export default MailViewer;