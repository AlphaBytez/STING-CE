const fs = require('fs');
const path = require('path');

// Check if certificates exist
function checkCertificatesExist() {
  console.log('Checking certificates...');
  
  const sslKeyFile = process.env.SSL_KEY_FILE;
  const sslCertFile = process.env.SSL_CRT_FILE;
  
  console.log(`SSL_KEY_FILE: ${sslKeyFile}`);
  console.log(`SSL_CRT_FILE: ${sslCertFile}`);
  
  if (!sslKeyFile || !sslCertFile) {
    console.error('SSL certificate files not specified in environment variables');
    return false;
  }
  
  try {
    if (fs.existsSync(sslKeyFile)) {
      console.log(`✅ Key file exists: ${sslKeyFile}`);
    } else {
      console.error(`❌ Key file does not exist: ${sslKeyFile}`);
      return false;
    }
    
    if (fs.existsSync(sslCertFile)) {
      console.log(`✅ Certificate file exists: ${sslCertFile}`);
    } else {
      console.error(`❌ Certificate file does not exist: ${sslCertFile}`);
      return false;
    }
    
    return true;
  } catch (err) {
    console.error(`Error checking certificate files: ${err.message}`);
    return false;
  }
}

const certsExist = checkCertificatesExist();
console.log(`Certificates exist: ${certsExist}`);

if (!certsExist) {
  console.log('HTTPS will be disabled due to missing certificates');
  process.env.HTTPS = 'false';
} else {
  console.log('HTTPS is enabled with provided certificates');
}