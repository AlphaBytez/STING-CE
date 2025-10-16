// This script overrides the MailSlurper service URL logic
// to work correctly with Docker port mappings
(function() {
  // Original getServiceURL function
  const originalGetServiceURL = window.SettingsService.getServiceURL;
  
  // Override with a fixed version
  window.SettingsService.getServiceURL = function(serviceSettings) {
    // Use the original function first
    const originalURL = originalGetServiceURL(serviceSettings);
    
    // Replace the service address with our external hostname
    // and use the mapped port
    const hostname = window.location.hostname;
    const port = "4437"; // Use the exact port we mapped in docker-compose
    
    return window.location.protocol + "//" + hostname + ":" + port;
  };

  console.log("MailSlurper service URL override applied");
})();