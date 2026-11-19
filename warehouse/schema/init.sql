-- ============================================
-- SupplyChainIQ — PostgreSQL Init Script
-- Creates the warehouse schema for star-schema tables
-- ============================================
CREATE SCHEMA IF NOT EXISTS warehouse;

-- Grant usage to the app user
GRANT ALL ON SCHEMA warehouse TO sciq_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA warehouse GRANT ALL ON TABLES TO sciq_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA warehouse GRANT ALL ON SEQUENCES TO sciq_user;
