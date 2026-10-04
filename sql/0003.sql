-- sql/0003.sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS senders_patterns
    ON senders (sender) WHERE type = 'P';
CREATE INDEX CONCURRENTLY IF NOT EXISTS senders_static_patterns
    ON senders_static (sender) WHERE type = 'P';

UPDATE config SET value = '3' WHERE name = 'schema';
