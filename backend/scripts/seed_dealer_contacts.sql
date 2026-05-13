-- 2026-05-13: Seed dealer_contacts with the top stale-target sellers enriched
-- via public-web research. Run after 2026-05-13_create_dealer_contacts.sql.
--
-- Top 6 Kijiji dealers (cover 211 of 219 Kijiji-with-seller listings, ~96%) +
-- ANCO (already unmasked from May 8 supply-targets work).
--
-- Idempotent: ON CONFLICT updates contact fields if changed, refreshes updated_at.

INSERT INTO dealer_contacts (seller_name, source, contact_name, contact_email, contact_phone, website, address, notes, enrichment_source, enriched_by) VALUES
    ('Global Power Systems', 'kijiji',
     'Sales',
     NULL,
     '780-450-6363',
     'https://www.globalpower.ca/',
     'Nisku, Alberta',
     'Multiquip / Allmand / Generac dealer. Generators + industrial engines + oilfield equipment.',
     'web-research',
     'curtis@arcanosai.com'),

    ('Hammerstrap Industries', 'kijiji',
     'Adrian',
     NULL,
     '780-288-4199',
     'https://www.hammerstrap.com/',
     'Waskatenau, Alberta',
     'Premium pre-owned equipment. Adrian primary, Paul secondary at 780-656-5808. Ag/construction/oilfield/trucks.',
     'web-research',
     'curtis@arcanosai.com'),

    ('Edmonton Equipment Rentals and Sales 2025 Ltd.', 'kijiji',
     'Sales',
     NULL,
     '780-571-0023',
     'https://edmontonequipmentrentalsandsales.com/',
     '473 South Avenue, Spruce Grove, AB T7X-2E9',
     'Trucks, trailers, heavy equipment rentals + sales. 30+ years.',
     'web-research',
     'curtis@arcanosai.com'),

    ('Capital Automotive Equipment Ltd. - Calgary Terminal', 'kijiji',
     'Sales',
     'sales@capitalautoequipment.com',
     '365-317-7933',
     'https://capitalautoequipment.com/',
     'HQ Stoney Creek ON; Calgary pickup available',
     'Auto/truck repair equipment. Calgary terminal is a pickup point, not a staffed branch.',
     'web-research',
     'curtis@arcanosai.com'),

    ('PD Equipment', 'kijiji',
     'Sales',
     'pdequipment@gmail.com',
     '780-913-5954',
     'https://www.pdequip.com/',
     '20804 - 100 Avenue, Edmonton, AB',
     'Used heavy equipment sales + rental. Will source equipment in North America if not in stock.',
     'web-research',
     'curtis@arcanosai.com'),

    ('Driven Equipment Ltd', 'kijiji',
     'Nick',
     'nick@drivenequipmentltd.com',
     NULL,
     'https://drivenequipmentltd.com/',
     '7515 84th Street SE, Calgary, AB T2C 4Y1',
     'Founded 2019 Calgary. Heavy equipment sales/service/rental. Trucking arm: mac@drivenequipmentltd.com.',
     'web-research',
     'curtis@arcanosai.com'),

    ('Seller 23609 - ANCO', 'allsurplus',
     NULL,
     NULL,
     NULL,
     'https://www.andersoncolumbia.com/',
     'Lake City, FL (HQ) + plants in Old Town/Quincy/Marianna FL, TX yards Robstown/Weslaco/Corpus Christi/New Braunfels, GA aggregate ops',
     'Anderson Columbia Co. (ACCI). Heavy-civil road construction contractor. Confirmed via per-lot location triangulation 2026-05-08. Recurring fleet rotation, not bankruptcy. Named contact still TBD via Shreya.',
     'web-research',
     'curtis@arcanosai.com')

ON CONFLICT (seller_name, source) DO UPDATE SET
    contact_name      = COALESCE(EXCLUDED.contact_name, dealer_contacts.contact_name),
    contact_email     = COALESCE(EXCLUDED.contact_email, dealer_contacts.contact_email),
    contact_phone     = COALESCE(EXCLUDED.contact_phone, dealer_contacts.contact_phone),
    website           = COALESCE(EXCLUDED.website, dealer_contacts.website),
    address           = COALESCE(EXCLUDED.address, dealer_contacts.address),
    notes             = COALESCE(EXCLUDED.notes, dealer_contacts.notes),
    enrichment_source = EXCLUDED.enrichment_source,
    enriched_by       = EXCLUDED.enriched_by,
    updated_at        = NOW();
