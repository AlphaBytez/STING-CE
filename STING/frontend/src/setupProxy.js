const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Simple, clean proxy configuration for Kratos
  const kratosProxy = createProxyMiddleware({
    target: 'https://kratos:4433',
    changeOrigin: true,
    secure: false,
    logLevel: 'debug',
    onProxyReq: (proxyReq, req, res) => {
      console.log(`Proxying ${req.method} ${req.url} to Kratos`);
    },
    onProxyRes: (proxyRes, req, res) => {
      console.log(`Kratos responded with ${proxyRes.statusCode} for ${req.url}`);
      
      // Handle redirect responses from Kratos
      if (proxyRes.statusCode === 303 || proxyRes.statusCode === 302) {
        const location = proxyRes.headers.location;
        if (location && location.includes('flow=')) {
          // Extract just the flow parameter and construct a relative URL
          const url = new URL(location);
          const flowId = url.searchParams.get('flow');
          const pathname = url.pathname;
          
          // Rewrite the location header to be relative
          proxyRes.headers.location = `${pathname}?flow=${flowId}`;
          console.log(`Rewrote redirect from ${location} to ${proxyRes.headers.location}`);
        }
      }
    },
    onError: (err, req, res) => {
      console.error(`Proxy error for ${req.url}:`, err.message);
      res.status(502).json({
        error: 'Failed to connect to authentication service'
      });
    }
  });

  // IMPORTANT: Apply Kratos proxy FIRST, before any other middleware
  // This ensures .ory paths are intercepted before falling through to React app
  app.use([
    '/self-service',
    '/sessions',
    '/identities',
    '/schemas', 
    '/health',
    '/.ory'
  ], kratosProxy);

  // Detect if we're running in Docker by checking for Docker-specific file
  const fs = require('fs');
  const isDocker = fs.existsSync('/.dockerenv') || fs.existsSync('/proc/1/cgroup');
  
  // Use container name when running in Docker, localhost otherwise
  const beeTarget = isDocker
    ? 'http://sting-ce-chatbot:8888' 
    : 'http://localhost:8888';
    
  console.log('[Proxy] Running in Docker:', isDocker);
  console.log('[Proxy] Bee target:', beeTarget);

  // Proxy for chat/bee endpoints - MUST BE BEFORE general /api proxy
  app.use('/api/chat', createProxyMiddleware({
    target: beeTarget,
    changeOrigin: true,
    secure: false,
    pathRewrite: { '^/api/chat': '/chat' }
  }));
    
  app.use('/api/bee', createProxyMiddleware({
    target: beeTarget,
    changeOrigin: true,
    secure: false,
    pathRewrite: { '^/api/bee': '' }
  }));

  // Proxy for messaging service
  app.use('/api/messaging', createProxyMiddleware({
    target: isDocker ? 'http://sting-ce-messaging:8889' : 'http://localhost:8889',
    changeOrigin: true,
    secure: false,
    pathRewrite: { '^/api/messaging': '' },
    onProxyReq: (proxyReq, req, res) => {
      console.log(`[Proxy] Messaging request: ${req.method} ${req.url}`);
      // Forward cookies to messaging service
      const cookies = req.headers.cookie;
      if (cookies) {
        console.log(`[Proxy] Forwarding cookies to messaging service: ${cookies}`);
        proxyReq.setHeader('Cookie', cookies);
      }
    }
  }));

  // Proxy for external AI service
  app.use('/api/external-ai', createProxyMiddleware({
    target: isDocker ? 'http://sting-ce-external-ai:8091' : 'http://localhost:8091',
    changeOrigin: true,
    secure: false,
    pathRewrite: { '^/api/external-ai': '' },
    onProxyReq: (proxyReq, req, res) => {
      console.log(`[Proxy] External AI request: ${req.method} ${req.url}`);
      // Forward cookies to external AI service
      const cookies = req.headers.cookie;
      if (cookies) {
        console.log(`[Proxy] Forwarding cookies to external AI service: ${cookies}`);
        proxyReq.setHeader('Cookie', cookies);
      }
    }
  }));

  // Proxy for knowledge service (honey jars)
  app.use('/api/knowledge', createProxyMiddleware({
    target: isDocker ? 'http://sting-ce-knowledge:8090' : 'http://localhost:8090',
    changeOrigin: true,
    secure: false,
    pathRewrite: { '^/api/knowledge': '' },
    onProxyReq: (proxyReq, req, res) => {
      console.log(`[Proxy] Knowledge service request: ${req.method} ${req.url}`);
      // Forward cookies to knowledge service
      const cookies = req.headers.cookie;
      if (cookies) {
        console.log(`[Proxy] Forwarding cookies to knowledge service: ${cookies}`);
        proxyReq.setHeader('Cookie', cookies);
      }
    }
  }));

  // Proxy for STING API
  app.use('/api', createProxyMiddleware({
    target: 'https://sting-ce-app:5050',
    changeOrigin: true,
    secure: false,
    cookieDomainRewrite: {
      "*": ""  // Remove domain from cookies to ensure they work locally
    },
    onProxyReq: (proxyReq, req, res) => {
      console.log(`Proxying API request: ${req.method} ${req.url}`);
      // Log cookies being forwarded
      const cookies = req.headers.cookie;
      if (cookies) {
        console.log(`Forwarding cookies to API: ${cookies}`);
        // Ensure cookies are forwarded
        proxyReq.setHeader('Cookie', cookies);
      }
      // Forward the origin header for CORS
      if (req.headers.origin) {
        proxyReq.setHeader('Origin', req.headers.origin);
      }
    },
    onProxyRes: (proxyRes, req, res) => {
      console.log(`API responded with ${proxyRes.statusCode} for ${req.url}`);
      // Log any set-cookie headers from the response
      const setCookies = proxyRes.headers['set-cookie'];
      if (setCookies) {
        console.log(`API set cookies:`, setCookies);
      }
    }
  }));

  // Debug logging
  app.use((req, res, next) => {
    console.log(`[Debug] Incoming request: ${req.method} ${req.url}`);
    next();
  });
};