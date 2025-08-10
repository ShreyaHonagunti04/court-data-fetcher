-- Court Data Fetcher Database Schema
-- PostgreSQL Database Initialization Script

-- Create database (run this as postgres superuser)
-- CREATE DATABASE court_data_db;
-- CREATE USER court_user WITH PASSWORD 'secure_password';
-- GRANT ALL PRIVILEGES ON DATABASE court_data_db TO court_user;

-- Connect to the database and run the following:

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Case queries table for logging all search attempts
CREATE TABLE IF NOT EXISTS case_queries (
    id SERIAL PRIMARY KEY,
    case_type VARCHAR(100) NOT NULL,
    case_number VARCHAR(100) NOT NULL,
    filing_year INTEGER NOT NULL,
    query_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    raw_response TEXT,
    parsed_data JSONB,
    ip_address INET,
    user_agent TEXT,
    CONSTRAINT check_filing_year CHECK (filing_year >= 1950 AND filing_year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1)
);

-- Case details table for storing parsed case information
CREATE TABLE IF NOT EXISTS case_details (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(200) UNIQUE NOT NULL,
    case_type VARCHAR(100) NOT NULL,
    case_number VARCHAR(100) NOT NULL,
    filing_year INTEGER NOT NULL,
    petitioner VARCHAR(500),
    respondent VARCHAR(500),
    filing_date DATE,
    next_hearing_date DATE,
    status VARCHAR(200),
    stage VARCHAR(200),
    court_name VARCHAR(200),
    judge_name VARCHAR(200),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_case_id UNIQUE (case_id),
    CONSTRAINT unique_case_info UNIQUE (case_type, case_number, filing_year)
);

-- Orders and judgments table
CREATE TABLE IF NOT EXISTS orders_judgments (
    id SERIAL PRIMARY KEY,
    case_detail_id INTEGER NOT NULL REFERENCES case_details(id) ON DELETE CASCADE,
    order_date DATE,
    order_type VARCHAR(100), -- 'Order', 'Judgment', 'Document'
    description TEXT,
    pdf_url VARCHAR(500),
    file_size VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_case_queries_timestamp ON case_queries(query_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_case_queries_success ON case_queries(success);
CREATE INDEX IF NOT EXISTS idx_case_queries_case_info ON case_queries(case_type, case_number, filing_year);

CREATE INDEX IF NOT EXISTS idx_case_details_case_id ON case_details(case_id);
CREATE INDEX IF NOT EXISTS idx_case_details_case_info ON case_details(case_type, case_number, filing_year);
CREATE INDEX IF NOT EXISTS idx_case_details_dates ON case_details(filing_date, next_hearing_date);

CREATE INDEX IF NOT EXISTS idx_orders_case_detail ON orders_judgments(case_detail_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders_judgments(order_date DESC);

-- Create a function to update last_updated timestamp
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for case_details table
CREATE TRIGGER update_case_details_last_updated 
    BEFORE UPDATE ON case_details 
    FOR EACH ROW 
    EXECUTE FUNCTION update_last_updated_column();

-- Insert some sample data for testing (optional)
-- INSERT INTO case_queries (case_type, case_number, filing_year, success, parsed_data) 
-- VALUES ('W.P.(C)', '1234', 2023, true, '{"test": "data"}');

-- Create a view for query statistics
CREATE OR REPLACE VIEW query_statistics AS
SELECT 
    COUNT(*) as total_queries,
    COUNT(*) FILTER (WHERE success = true) as successful_queries,
    COUNT(*) FILTER (WHERE success = false) as failed_queries,
    COUNT(DISTINCT CONCAT(case_type, '/', case_number, '/', filing_year)) as unique_case_searches,
    DATE_TRUNC('day', query_timestamp) as query_date
FROM case_queries
GROUP BY DATE_TRUNC('day', query_timestamp)
ORDER BY query_date DESC;

-- Grant permissions to the application user
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO court_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO court_user;