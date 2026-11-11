-- Ordonnance V4, ticket 22: two-factor authentication.
-- The TOTP secret is sealed by the application (app/services/vault.py); recovery codes are
-- stored as hashes and used once. last_timestep blocks replaying a code.
-- Applied automatically at startup by SchemaMigrator; idempotent if run by hand.

CREATE TABLE IF NOT EXISTS `user_two_factor` (
    `user_id` BIGINT PRIMARY KEY,
    `secret` LONGTEXT NULL,
    `pending_secret` LONGTEXT NULL,
    `enabled_at` DATETIME NULL,
    `last_timestep` BIGINT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user_recovery_codes` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `code_hash` VARCHAR(255) NOT NULL,
    `used_at` DATETIME NULL,
    KEY `idx_recovery_codes_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
