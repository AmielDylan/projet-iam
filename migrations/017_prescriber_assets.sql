-- Prescriber signature and stamp, as transparent PNG images.
-- Sealed by the application (app/services/vault.py): a signature could be used to forge ordonnances.
-- Applied automatically at startup by SchemaMigrator; idempotent if run by hand.

CREATE TABLE IF NOT EXISTS `prescriber_assets` (
    `user_id` BIGINT NOT NULL,
    `kind` VARCHAR(16) NOT NULL,
    `content` LONGTEXT NOT NULL,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`user_id`, `kind`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
