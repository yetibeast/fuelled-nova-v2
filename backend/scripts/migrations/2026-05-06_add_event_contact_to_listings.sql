-- 2026-05-06: Capture AllSurplus event contact details (Liquidity Services
-- account managers per consignment event). Each /asset/{seller_id}/{asset_id}
-- references an event_id; that event page has a public "Contact Details" block
-- with a real human's name, email, and phone.
--
-- Phase 2 of Mark's supply-targeting ask — gives us actionable outbound contacts.
-- All columns nullable; safe to apply on a live table.

ALTER TABLE listings ADD COLUMN IF NOT EXISTS event_id              TEXT;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS event_title           TEXT;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS event_contact_name    TEXT;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS event_contact_email   TEXT;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS event_contact_phone   TEXT;

CREATE INDEX IF NOT EXISTS idx_listings_event ON listings (source, event_id) WHERE event_id IS NOT NULL;
