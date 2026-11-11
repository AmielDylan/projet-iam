-- Ordonnance V4, ticket 20: access log.
-- Who read or changed which ordonnance or patient, and when. Identifiers only, never medical data.
-- Append-only: triggers refuse any update or delete from the application.
-- Applied automatically at startup by SchemaMigrator; idempotent if run by hand.

CREATE TABLE IF NOT EXISTS `access_log` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `object_type` VARCHAR(20) NOT NULL,
    `object_id` BIGINT NULL,
    `action` VARCHAR(20) NOT NULL,
    `ip` VARCHAR(45) NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_access_log_object` (`object_type`, `object_id`, `created_at`),
    KEY `idx_access_log_user` (`user_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TRIGGER IF EXISTS `access_log_no_update`;
DELIMITER ;;
CREATE TRIGGER `access_log_no_update` BEFORE UPDATE ON `access_log`
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'access_log is append-only';
END;;
DELIMITER ;

DROP TRIGGER IF EXISTS `access_log_no_delete`;
DELIMITER ;;
CREATE TRIGGER `access_log_no_delete` BEFORE DELETE ON `access_log`
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'access_log is append-only';
END;;
DELIMITER ;
