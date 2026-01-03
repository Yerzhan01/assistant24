-- Create dev database if not exists
SELECT 'CREATE DATABASE assistant24_dev'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'assistant24_dev')\gexec

-- Create prod database if not exists
SELECT 'CREATE DATABASE assistant24_prod'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'assistant24_prod')\gexec