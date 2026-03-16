-- This table is used by scripts to exclude specific addresses from being sync'd to postconfirm
-- https://github.com/ietf-tools/mail-support-scripts/blob/main/scripts/global-allowlist-sync
CREATE TABLE never_allow (
  email VARCHAR(255) NOT NULL,
  reason VARCHAR(255),
  PRIMARY KEY (email),
  created TIMESTAMP WITH TIME ZONE DEFAULT now()
);

UPDATE config SET value = '2' WHERE name = 'schema';
