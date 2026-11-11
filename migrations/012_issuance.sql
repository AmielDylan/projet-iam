-- Ordonnance V4, ticket 04: issuing an ordonnance.
-- Prescriber code (4 characters, no ambiguous letters) prefixes every ordonnance number;
-- each prescriber has a yearly sequence. Establishments choose their paper format.
-- Every import of the ANSM thesaurus or of the catalog records a referential version.
-- Applied automatically at startup by SchemaMigrator; "already exists" warnings are tolerated.

ALTER TABLE `iam_users` ADD COLUMN `prescriber_code` CHAR(4) NULL;
ALTER TABLE `iam_users` ADD UNIQUE KEY `uq_iam_users_prescriber_code` (`prescriber_code`);

ALTER TABLE `prescriber_establishments` ADD COLUMN `paper_format` VARCHAR(2) NOT NULL DEFAULT 'A5';

CREATE TABLE IF NOT EXISTS `prescriber_sequences` (
    `owner_id` BIGINT NOT NULL,
    `year` SMALLINT NOT NULL,
    `last_number` INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`owner_id`, `year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `referential_versions` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `kind` VARCHAR(20) NOT NULL,
    `label` VARCHAR(190) NOT NULL,
    `published_on` DATE NULL,
    `imported_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_referential_versions_kind` (`kind`, `imported_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
