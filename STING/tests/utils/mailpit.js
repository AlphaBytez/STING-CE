/**
 * Mailpit Integration Utilities
 * Helper functions for extracting email codes during testing
 */

async function getLatestEmailCode() {
  try {
    // Get latest email from Mailpit API
    const response = await fetch('http://localhost:8025/api/v1/messages?limit=1');
    const data = await response.json();
    
    if (!data.messages || data.messages.length === 0) {
      console.log('📧 No emails found in Mailpit');
      return null;
    }
    
    const latestMessage = data.messages[0];
    console.log(`📧 Latest email: ${latestMessage.Subject} to ${latestMessage.To[0].Address}`);
    
    // Get email content
    const contentResponse = await fetch(`http://localhost:8025/api/v1/message/${latestMessage.ID}`);
    const emailData = await contentResponse.json();
    
    // Extract 6-digit code from email content
    const emailBody = emailData.Text || emailData.HTML || '';
    const codeMatch = emailBody.match(/\b(\d{6})\b/);
    
    if (codeMatch) {
      const code = codeMatch[1];
      console.log(`📧 Extracted code: ${code}`);
      return code;
    } else {
      console.log('📧 No 6-digit code found in email');
      return null;
    }
    
  } catch (error) {
    console.error('📧 Error fetching email code:', error.message);
    return null;
  }
}

async function waitForNewEmail(timeoutMs = 10000) {
  const startTime = Date.now();
  let lastCount = 0;
  
  try {
    // Get initial email count
    const initialResponse = await fetch('http://localhost:8025/api/v1/messages?limit=1');
    const initialData = await initialResponse.json();
    lastCount = initialData.total || 0;
    
    while (Date.now() - startTime < timeoutMs) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const response = await fetch('http://localhost:8025/api/v1/messages?limit=1');
      const data = await response.json();
      const currentCount = data.total || 0;
      
      if (currentCount > lastCount) {
        console.log('📧 New email detected!');
        return await getLatestEmailCode();
      }
    }
    
    console.log('📧 Timeout waiting for new email');
    return null;
    
  } catch (error) {
    console.error('📧 Error waiting for email:', error.message);
    return null;
  }
}

module.exports = {
  getLatestEmailCode,
  waitForNewEmail
};