CREATE TABLE never_allow (
  email VARCHAR(255) NOT NULL,
  reason VARCHAR(255),
  PRIMARY KEY (email),
  created TIMESTAMP WITH TIME ZONE DEFAULT now()
);

UPDATE config SET value = '2' WHERE name = 'schema';
