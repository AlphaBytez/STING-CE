const path = require('path');

module.exports = {
  babel: {
    presets: [
      '@babel/preset-env',
      ['@babel/preset-react', { runtime: 'automatic' }]
    ]
  },
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    },
    configure: {
      resolve: {
        fallback: {
          "https": require.resolve('https-browserify'),
          "http": require.resolve('stream-http'),
          "stream": require.resolve('stream-browserify')
        }
      }
    }
  },
  devServer: {
    setupMiddlewares: (middlewares, devServer) => {
      // Add any custom middleware here if needed
      return middlewares;
    },
    https: process.env.HTTPS === 'true' 
  }
};
