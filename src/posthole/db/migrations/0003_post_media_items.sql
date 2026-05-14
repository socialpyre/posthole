-- Carousel support: posts can carry an ordered list of media items. The
-- legacy single media_url / media_type columns stay (most posts are
-- single-media; cheap to keep, no app-level branching at insert). When
-- media_items is non-null it's authoritative; when null the loader
-- synthesizes a 1-item list from media_url + media_type.

ALTER TABLE posts ADD COLUMN media_items TEXT;

-- Demo carousel so /posts shows the new shape without manual SQL. References
-- the seeded IG account from 0001_instagram.sql. Pre-published so the
-- caption + media render directly without running the seed_flow.
INSERT INTO posts (
  id, platform, account_id, caption, status, created_at, published_at,
  external_ref, media_url, media_type, platform_post_id, media_items
) VALUES (
  'demo-carousel-0001',
  'instagram',
  '178414000000001',
  'demo carousel — three frames from the rooftop',
  'published',
  '2026-04-01T12:00:00+00:00',
  '2026-04-01T12:00:00+00:00',
  'demo-container-carousel-0001',
  'https://picsum.photos/seed/posthole-c1/1080/1080',
  'IMAGE',
  'demo-platform-post-carousel-0001',
  '[{"ordinal":0,"kind":"IMAGE","url":"https://picsum.photos/seed/posthole-c1/1080/1080"},{"ordinal":1,"kind":"IMAGE","url":"https://picsum.photos/seed/posthole-c2/1080/1080"},{"ordinal":2,"kind":"IMAGE","url":"https://picsum.photos/seed/posthole-c3/1080/1080"}]'
);
