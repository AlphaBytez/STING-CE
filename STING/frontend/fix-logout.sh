#!/bin/bash
# Script to fix logout functionality by updating the LogoutPage component

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default container name
CONTAINER_NAME="sting-frontend-1"

# Check if frontend container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
  echo -e "${RED}Error: Frontend container '$CONTAINER_NAME' not found or not running!${NC}"
  echo -e "${YELLOW}Available containers:${NC}"
  docker ps --format "{{.Names}}" | grep frontend
  
  # Ask user to specify container name if needed
  read -p "Enter frontend container name (or press Enter to exit): " custom_container
  
  if [ -z "$custom_container" ]; then
    echo "Exiting..."
    exit 1
  fi
  
  CONTAINER_NAME=$custom_container
  
  # Verify the specified container exists
  if ! docker ps | grep -q $CONTAINER_NAME; then
    echo -e "${RED}Error: Container '$CONTAINER_NAME' not found or not running!${NC}"
    exit 1
  fi
fi

echo -e "${BLUE}=== Fixing logout functionality in container '$CONTAINER_NAME' ===${NC}"

# Create a temporary LogoutPage.jsx with the fixed implementation
LOGOUT_COMPONENT=$(cat << 'EOF'
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

/**
 * LogoutPage - Handles proper Kratos logout flow
 * This component processes the logout flow and redirects users
 */
const LogoutPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState('Logging you out...');
  
  // Get Kratos URL from environment or use default
  const kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
  
  useEffect(() => {
    // Process the logout
    const processLogout = async () => {
      try {
        console.log("Starting logout process");
        
        // Check if we have a logout token in the URL
        const url = new URL(window.location.href);
        const logoutToken = url.searchParams.get('token');
        
        if (logoutToken) {
          console.log("Token found in URL, executing logout with token:", logoutToken);
          
          // We have a token, execute the logout
          await axios.post(`${kratosUrl}/self-service/logout`, { 
            logout_token: logoutToken 
          }, {
            withCredentials: true
          });
          
          setMessage('You have been successfully logged out!');
          console.log("Logout with token successful");
          
          // Clear local storage
          localStorage.removeItem('user');
        } else {
          console.log("No token in URL, initiating logout flow");
          
          // No token, initialize logout flow
          const response = await axios.get(`${kratosUrl}/self-service/logout/browser`, {
            withCredentials: true
          });
          
          console.log("Logout flow response:", response.data);
          
          // Check if we got a valid flow
          if (response.data && response.data.logout_url) {
            // For HTTP redirect we could use window.location, but for better UX
            // we can also extract the token and call the API directly
            const logoutUrl = new URL(response.data.logout_url);
            const token = logoutUrl.searchParams.get('token');
            
            if (token) {
              console.log("Extracted token from logout URL:", token);
              
              await axios.post(`${kratosUrl}/self-service/logout`, { 
                logout_token: token 
              }, {
                withCredentials: true
              });
              
              setMessage('You have been successfully logged out!');
              console.log("Logout with extracted token successful");
              
              // Clear local storage
              localStorage.removeItem('user');
            } else {
              console.log("No token found in logout URL, redirecting to full URL");
              
              // Fallback to full redirect
              window.location.href = response.data.logout_url;
              return;
            }
          } else {
            console.log("Invalid logout flow response:", response.data);
            throw new Error('Invalid logout flow response');
          }
        }
      } catch (err) {
        console.error('Logout error:', err);
        setError('An error occurred during logout. Please try again.');
      } finally {
        setLoading(false);
        
        // After a short delay, redirect to login
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      }
    };
    
    processLogout();
  }, [kratosUrl, navigate]);
  
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-gray-800 p-8 rounded-lg shadow-lg max-w-md w-full text-white text-center">
        <div className="mb-6">
          {loading ? (
            <div className="w-12 h-12 border-t-2 border-b-2 border-yellow-400 rounded-full animate-spin mx-auto"></div>
          ) : error ? (
            <svg className="w-12 h-12 text-red-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          ) : (
            <svg className="w-12 h-12 text-green-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
            </svg>
          )}
        </div>
        
        <h1 className="text-2xl font-bold mb-2">
          {error ? 'Logout Failed' : 'Logging Out'}
        </h1>
        
        <p className="text-gray-300 mb-6">
          {error || message}
        </p>
        
        <div className="flex flex-col space-y-4">
          {error && (
            <button 
              onClick={() => window.location.reload()}
              className="w-full py-2 bg-yellow-600 hover:bg-yellow-700 rounded"
            >
              Try Again
            </button>
          )}
          
          <button 
            onClick={() => navigate('/login')}
            className={`w-full py-2 ${
              error 
                ? 'bg-gray-700 hover:bg-gray-600' 
                : 'bg-blue-600 hover:bg-blue-700'
            } rounded`}
          >
            Return to Login
          </button>
        </div>
      </div>
    </div>
  );
};

export default LogoutPage;
EOF
)

# Create fixed KratosProvider.jsx with updated logout method
KRATOS_PROVIDER_UPDATE=$(cat << 'EOF'
  // Handle logout - Use our dedicated component page for better UX
  const logout = () => {
    // Clear any local storage before redirecting
    localStorage.removeItem('user');
    sessionStorage.clear();
    
    // Redirect to logout page which will handle the API calls
    window.location.href = `${window.location.origin}/logout`;
  };
EOF
)

# Update LogoutPage in the frontend container
echo -e "${YELLOW}Updating LogoutPage component...${NC}"
echo "$LOGOUT_COMPONENT" > LogoutPage.jsx.temp
docker cp LogoutPage.jsx.temp "${CONTAINER_NAME}:/app/src/components/auth/LogoutPage.jsx"
rm LogoutPage.jsx.temp

if [ $? -eq 0 ]; then
  echo -e "${GREEN}Successfully updated LogoutPage component${NC}"
else
  echo -e "${RED}Failed to update LogoutPage component${NC}"
  exit 1
fi

# Make sure the logout route is set up correctly in AppRoutes.js
echo -e "${YELLOW}Checking if AppRoutes.js has the logout route...${NC}"
docker exec $CONTAINER_NAME grep -q "/logout" /app/src/AppRoutes.js
if [ $? -eq 0 ]; then
  echo -e "${GREEN}Logout route found in AppRoutes.js${NC}"
else
  echo -e "${RED}Logout route not found in AppRoutes.js, please add it manually${NC}"
  echo -e "${BLUE}Add this line to the routes in AppRoutes.js:${NC}"
  echo -e "${BLUE}<Route path=\"/logout\" element={<LogoutPage />} />${NC}"
fi

# Update KratosProvider.jsx
echo -e "${YELLOW}Updating KratosProvider...${NC}"
docker exec $CONTAINER_NAME cat /app/src/auth/KratosProvider.jsx > KratosProvider.jsx.temp
UPDATED_CONTENT=$(sed -n '/\/\/ Handle logout/,/};/!p' KratosProvider.jsx.temp)
UPDATED_CONTENT+=$'\n'"$KRATOS_PROVIDER_UPDATE"$'\n'
UPDATED_CONTENT+=$(sed -n '/};/,$p' KratosProvider.jsx.temp | tail -n +2)
echo "$UPDATED_CONTENT" > KratosProvider.jsx.updated
docker cp KratosProvider.jsx.updated "${CONTAINER_NAME}:/app/src/auth/KratosProvider.jsx"
rm KratosProvider.jsx.temp KratosProvider.jsx.updated

if [ $? -eq 0 ]; then
  echo -e "${GREEN}Successfully updated KratosProvider${NC}"
else
  echo -e "${RED}Failed to update KratosProvider${NC}"
fi

echo -e "${GREEN}=== Logout functionality fix completed! ===${NC}"
echo -e "${YELLOW}Note: You may need to refresh your browser to see the changes.${NC}"
echo -e "${BLUE}Try logging out now - you should see a proper logout page${NC}"