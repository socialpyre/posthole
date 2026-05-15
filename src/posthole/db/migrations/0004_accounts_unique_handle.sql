-- Enforce one handle per platform. Pre-dedupe so the index lands cleanly
-- on an upgrade from a build that didn't enforce it.
DELETE FROM accounts
 WHERE rowid NOT IN (
   SELECT MIN(rowid) FROM accounts GROUP BY platform, username
 );
CREATE UNIQUE INDEX idx_accounts_platform_username ON accounts (platform, username);
