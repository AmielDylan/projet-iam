-- V3 ordonnance classique: medication catalog import and enrichment audit.
-- Non-destructive migration: existing IAM tables are not dropped or rewritten.

CREATE TABLE IF NOT EXISTS `medication_catalog_staging` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `import_batch_id` VARCHAR(64) NOT NULL,
    `source_file` VARCHAR(255) NOT NULL,
    `row_number` INT NOT NULL,
    `nom_medicament` VARCHAR(255) NULL,
    `dosage` VARCHAR(120) NULL,
    `concentration` VARCHAR(80) NULL,
    `forme_galenique` VARCHAR(80) NULL,
    `presentation` VARCHAR(80) NULL,
    `volume` VARCHAR(80) NULL,
    `quantite_unites` DECIMAL(10,2) NULL,
    `quantite_boites` DECIMAL(10,2) NULL,
    `substances` TEXT NULL,
    `specialite` TEXT NULL,
    `source_hash` CHAR(64) NOT NULL,
    `normalized_key` CHAR(64) NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_medcat_staging_batch_row` (`import_batch_id`, `row_number`),
    KEY `idx_medcat_staging_hash` (`source_hash`),
    KEY `idx_medcat_staging_key` (`normalized_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `medication_catalog` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `nom_medicament` VARCHAR(255) NOT NULL,
    `dosage` VARCHAR(120) NULL,
    `concentration` VARCHAR(80) NULL,
    `forme_galenique` VARCHAR(80) NULL,
    `presentation` VARCHAR(80) NULL,
    `volume` VARCHAR(80) NULL,
    `quantite_unites` DECIMAL(10,2) NULL,
    `quantite_boites` DECIMAL(10,2) NULL,
    `substances` TEXT NULL,
    `specialite` TEXT NULL,
    `searchable_text` TEXT NULL,
    `source_hash` CHAR(64) NOT NULL,
    `normalized_key` CHAR(64) NOT NULL,
    `iam_specialite_id` INT NULL,
    `match_status` VARCHAR(32) NOT NULL DEFAULT 'unmatched',
    `last_import_batch_id` VARCHAR(64) NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_medcat_source_hash` (`source_hash`),
    KEY `idx_medcat_key` (`normalized_key`),
    KEY `idx_medcat_nom` (`nom_medicament`),
    KEY `idx_medcat_iam_specialite` (`iam_specialite_id`),
    FULLTEXT KEY `ft_medcat_search` (`nom_medicament`, `substances`, `specialite`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `medication_enrichment_audit` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `import_batch_id` VARCHAR(64) NOT NULL,
    `catalog_id` BIGINT NULL,
    `action_type` VARCHAR(64) NOT NULL,
    `target_table` VARCHAR(64) NULL,
    `target_id` BIGINT NULL,
    `status` VARCHAR(32) NOT NULL,
    `reason` TEXT NULL,
    `payload_json` JSON NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_med_audit_batch` (`import_batch_id`),
    KEY `idx_med_audit_catalog` (`catalog_id`),
    KEY `idx_med_audit_action` (`action_type`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `medication_search_miss` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `query` VARCHAR(255) NOT NULL,
    `source` VARCHAR(64) NOT NULL DEFAULT 'ordonnance',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_med_search_miss_query` (`query`),
    KEY `idx_med_search_miss_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
