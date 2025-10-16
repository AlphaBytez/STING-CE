-- Create database if it doesn't exist
SELECT 'CREATE DATABASE sting_app'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sting_app');