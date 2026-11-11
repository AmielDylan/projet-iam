-- V3.2 prescriber-only account requests, temporary identity documents,
-- temporary passwords, and prescriber establishments.
-- Idempotent: each column is added only when missing, so the file can be replayed.

DROP PROCEDURE IF EXISTS `iam_add_column_if_missing`;

DELIMITER ;;
CREATE PROCEDURE `iam_add_column_if_missing`(
    IN p_table VARCHAR(64),
    IN p_column VARCHAR(64),
    IN p_definition VARCHAR(255)
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_table
          AND COLUMN_NAME = p_column
    ) THEN
        SET @iam_ddl = CONCAT('ALTER TABLE `', p_table, '` ADD COLUMN `', p_column, '` ', p_definition);
        PREPARE iam_stmt FROM @iam_ddl;
        EXECUTE iam_stmt;
        DEALLOCATE PREPARE iam_stmt;
    END IF;
END;;
DELIMITER ;

CALL `iam_add_column_if_missing`('iam_users', 'birthdate', 'DATE NULL AFTER `last_name`');
CALL `iam_add_column_if_missing`('iam_users', 'profession', 'VARCHAR(120) NULL AFTER `birthdate`');
CALL `iam_add_column_if_missing`('iam_users', 'order_number', 'VARCHAR(160) NULL AFTER `profession`');
CALL `iam_add_column_if_missing`('iam_users', 'phone', 'VARCHAR(80) NULL AFTER `order_number`');
CALL `iam_add_column_if_missing`('iam_users', 'temporary_password_expires_at', 'DATETIME NULL AFTER `review_note`');
CALL `iam_add_column_if_missing`('iam_users', 'must_change_password', 'TINYINT NOT NULL DEFAULT 0 AFTER `temporary_password_expires_at`');

DROP PROCEDURE IF EXISTS `iam_add_column_if_missing`;

CREATE TABLE IF NOT EXISTS `identity_documents` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `filename` VARCHAR(255) NOT NULL,
    `mime_type` VARCHAR(120) NOT NULL,
    `size_bytes` INT NOT NULL,
    `content` LONGBLOB NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_identity_documents_user` (`user_id`),
    KEY `idx_identity_documents_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `prescriber_establishments` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `name` VARCHAR(180) NOT NULL,
    `type` VARCHAR(120) NULL,
    `address` TEXT NULL,
    `phone` VARCHAR(80) NULL,
    `email` VARCHAR(255) NULL,
    `identifier_label` VARCHAR(120) NULL,
    `identifier_value` VARCHAR(160) NULL,
    `secondary_identifier_label` VARCHAR(120) NULL,
    `secondary_identifier_value` VARCHAR(160) NULL,
    `free_text` TEXT NULL,
    `logo_filename` VARCHAR(255) NULL,
    `logo_mime_type` VARCHAR(120) NULL,
    `logo_size_bytes` INT NULL,
    `logo_content` LONGBLOB NULL,
    `is_active` TINYINT NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY `idx_prescriber_establishments_user` (`user_id`, `is_active`),
    KEY `idx_prescriber_establishments_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
