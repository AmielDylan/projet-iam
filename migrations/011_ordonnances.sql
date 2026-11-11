-- Ordonnance V4, ticket 02: ordonnances and their saved versions.
-- `content` (patient, establishment, lines, notes, derogations) and `snapshot` are sealed by
-- the application (app/services/vault.py). Lines live inside the sealed content rather than
-- in a clear table, so that a copy of the database reveals no prescription.
-- Versions are append-only: triggers refuse any update or delete.
-- Applied automatically at startup by SchemaMigrator; idempotent if run by hand.

CREATE TABLE IF NOT EXISTS `ordonnances` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `owner_id` BIGINT NOT NULL,
    `status` VARCHAR(16) NOT NULL DEFAULT 'draft',
    `version` INT NOT NULL DEFAULT 1,
    `patient_id` BIGINT NULL,
    `establishment_id` BIGINT NULL,
    `origin_id` BIGINT NULL,
    `content` LONGTEXT NOT NULL,
    `number` VARCHAR(32) NULL,
    `snapshot` LONGTEXT NULL,
    `issued_at` DATETIME NULL,
    `cancelled_at` DATETIME NULL,
    `cancel_reason` TEXT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_ordonnances_number` (`number`),
    KEY `idx_ordonnances_owner_status` (`owner_id`, `status`, `updated_at`),
    KEY `idx_ordonnances_owner_patient` (`owner_id`, `patient_id`, `updated_at`),
    KEY `idx_ordonnances_origin` (`origin_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ordonnance_versions` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `ordonnance_id` BIGINT NOT NULL,
    `version` INT NOT NULL,
    `content` LONGTEXT NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_ordonnance_versions` (`ordonnance_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TRIGGER IF EXISTS `ordonnance_versions_no_update`;
DELIMITER ;;
CREATE TRIGGER `ordonnance_versions_no_update` BEFORE UPDATE ON `ordonnance_versions`
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ordonnance_versions is append-only';
END;;
DELIMITER ;

DROP TRIGGER IF EXISTS `ordonnance_versions_no_delete`;
DELIMITER ;;
CREATE TRIGGER `ordonnance_versions_no_delete` BEFORE DELETE ON `ordonnance_versions`
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ordonnance_versions is append-only';
END;;
DELIMITER ;
