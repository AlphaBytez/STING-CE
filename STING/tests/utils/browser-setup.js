/**
 * Browser Setup Utilities for STING Testing
 * Standardized browser configuration and helpers
 */

const { chromium, firefox } = require('playwright');

/**
 * Standard browser launch configuration for STING
 */
const BROWSER_CONFIG = {
  headless: false,
  ignoreHTTPSErrors: true,
  args: [
    '--ignore-ssl-errors=yes',
    '--ignore-certificate-errors',
    '--ignore-certificate-errors-spki-list',
    '--allow-running-insecure-content',
    '--disable-web-security',
    '--allow-insecure-localhost',
    '--disable-features=VizDisplayCompositor'
  ]
};

const CONTEXT_CONFIG = {
  ignoreHTTPSErrors: true,
  acceptDownloads: true,
  bypassCSP: true
};

/**
 * Launch browser with STING-optimized settings
 */
async function launchBrowser(browserType = 'chromium', options = {}) {
  const config = { ...BROWSER_CONFIG, ...options };
  
  let browser;
  switch (browserType) {
    case 'firefox':
      browser = await firefox.launch(config);
      break;
    case 'chromium':
    default:
      browser = await chromium.launch(config);
      break;
  }
  
  return browser;
}

/**
 * Create browser context with STING settings
 */
async function createContext(browser, options = {}) {
  const config = { ...CONTEXT_CONFIG, ...options };
  return await browser.newContext(config);
}

/**
 * Setup page with STING-specific monitoring
 */
function setupPageMonitoring(page, options = {}) {
  const { logNetwork = false, logConsole = false, logErrors = true } = options;
  
  // Log errors by default
  if (logErrors) {
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('🔴 Browser Error:', msg.text());
      }
    });
  }
  
  // Log console messages if requested
  if (logConsole) {
    page.on('console', msg => {
      if (msg.text().includes('🔄') || msg.text().includes('🚨') || msg.text().includes('✅') || msg.text().includes('🗑️')) {
        console.log('📱 STING Debug:', msg.text());
      }
    });
  }
  
  // Log network activity if requested
  if (logNetwork) {
    page.on('response', response => {
      if (response.status() >= 400) {
        console.log(`🌐 HTTP ${response.status()}: ${response.url()}`);
      }
    });
  }
  
  return page;
}

/**
 * Clear browser storage for clean test
 */
async function clearBrowserState(page) {
  await page.evaluate(() => {
    sessionStorage.clear();
    localStorage.clear();
    localStorage.setItem('aal_debug', 'true');
    console.log('🗑️ Cleared browser storage for clean test');
  });
}

/**
 * Navigate with SSL fallback
 */
async function navigateWithFallback(page, httpsUrl) {
  try {
    await page.goto(httpsUrl, { waitUntil: 'domcontentloaded', timeout: 10000 });
    console.log('✅ Connected via HTTPS');
    return httpsUrl;
  } catch (error) {
    console.log('⚠️  HTTPS failed, trying HTTP...');
    const httpUrl = httpsUrl.replace('https://', 'http://');
    await page.goto(httpUrl, { waitUntil: 'domcontentloaded', timeout: 10000 });
    console.log('✅ Connected via HTTP');
    return httpUrl;
  }
}

module.exports = {
  BROWSER_CONFIG,
  CONTEXT_CONFIG,
  launchBrowser,
  createContext,
  setupPageMonitoring,
  clearBrowserState,
  navigateWithFallback
};