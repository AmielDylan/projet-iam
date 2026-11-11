-- Ordonnance V4, ticket 15: catalog gaps seen in use.
-- Free-text medication names counted at issuance, without any link to a patient,
-- a prescriber or an ordonnance. Resolved once an admin creates the catalog entry.
-- Applied automatically at startup by SchemaMigrator; idempotent if run by hand.

CREATE TABLE IF NOT EXISTS `medication_free_entries` (
    `name_key` VARCHAR(190) PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL,
    `occurrences` INT NOT NULL DEFAULT 0,
    `resolved_catalog_id` BIGINT NULL,
    `last_seen_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_free_entries_open` (`resolved_catalog_id`, `occurrences`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
