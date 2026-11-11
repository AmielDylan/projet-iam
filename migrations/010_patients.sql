-- Ordonnance V4, ticket 03: patients with a stable identity.
-- The record (identity and clinical data) is sealed by the application (app/services/vault.py):
-- the database never holds a patient's name, birthdate or clinical data in clear.
-- Search goes through HMAC tokens of name prefixes and of the birthdate.
-- patient_history is kept read-only during the transition; its rows are copied at startup
-- by PatientService.migrate_legacy_history(), once each (legacy_history_id).
-- Applied automatically at startup by SchemaMigrator; idempotent if run by hand.

CREATE TABLE IF NOT EXISTS `patients` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `owner_id` BIGINT NOT NULL,
    `record` LONGTEXT NOT NULL,
    `birthdate_token` CHAR(64) NULL,
    `legacy_history_id` BIGINT NULL,
    `last_seen_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_patients_legacy_history` (`legacy_history_id`),
    KEY `idx_patients_owner_seen` (`owner_id`, `last_seen_at`),
    KEY `idx_patients_owner_birthdate` (`owner_id`, `birthdate_token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `patient_search_tokens` (
    `patient_id` BIGINT NOT NULL,
    `owner_id` BIGINT NOT NULL,
    `token` CHAR(64) NOT NULL,
    PRIMARY KEY (`patient_id`, `token`),
    KEY `idx_patient_tokens_owner_token` (`owner_id`, `token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
