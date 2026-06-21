-- V3.1 auth and prescription ownership.
-- Non-destructive migration: existing IAM/catalog tables are not dropped or rewritten.

CREATE TABLE IF NOT EXISTS `iam_users` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `email` VARCHAR(255) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` VARCHAR(32) NOT NULL DEFAULT 'prescriber',
    `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
    `first_name` VARCHAR(120) NULL,
    `last_name` VARCHAR(120) NULL,
    `requested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `reviewed_at` TIMESTAMP NULL,
    `reviewed_by` BIGINT NULL,
    `review_note` TEXT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_iam_users_email` (`email`),
    KEY `idx_iam_users_role_status` (`role`, `status`),
    KEY `idx_iam_users_reviewed_by` (`reviewed_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `prescriber_profiles` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `title` VARCHAR(32) NULL,
    `first_name` VARCHAR(120) NULL,
    `last_name` VARCHAR(120) NULL,
    `profession` VARCHAR(160) NULL,
    `organization` VARCHAR(180) NULL,
    `address` TEXT NULL,
    `phone` VARCHAR(80) NULL,
    `email` VARCHAR(255) NULL,
    `country` VARCHAR(120) NULL,
    `identifier_label` VARCHAR(120) NULL,
    `identifier_value` VARCHAR(160) NULL,
    `secondary_identifier_label` VARCHAR(120) NULL,
    `secondary_identifier_value` VARCHAR(160) NULL,
    `extra_details` TEXT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_prescriber_profiles_user` (`user_id`),
    KEY `idx_prescriber_profiles_name` (`last_name`, `first_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `patient_history` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `patient_key` CHAR(64) NOT NULL,
    `patient_title` VARCHAR(32) NULL,
    `patient_first_name` VARCHAR(120) NULL,
    `patient_last_name` VARCHAR(120) NULL,
    `patient_birthdate` DATE NULL,
    `patient_weight` DECIMAL(6,2) NULL,
    `patient_address` TEXT NULL,
    `clinical_notes` TEXT NULL,
    `last_seen_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_patient_history_user_key` (`user_id`, `patient_key`),
    KEY `idx_patient_history_search` (`user_id`, `patient_last_name`, `patient_first_name`),
    KEY `idx_patient_history_last_seen` (`user_id`, `last_seen_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
