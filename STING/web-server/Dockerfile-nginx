# Use the official Nginx image as the base image
FROM nginx:1.27-alpine

# Copy the Nginx configuration file to the Nginx configuration directory
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]