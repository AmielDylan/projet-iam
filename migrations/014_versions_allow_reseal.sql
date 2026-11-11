-- Ordonnance V4, ticket 21: key rotation.
-- ordonnance_versions stays append-only for the application. The only update allowed is a
-- reseal during a key rotation (scripts/rotate_data_keys.py): the session sets
-- @digiremed_key_rotation = 1, and only `content` may change, never the version or its draft.
-- Applied automatically at startup by SchemaMigrator; idempotent if run by hand.

DROP TRIGGER IF EXISTS `ordonnance_versions_no_update`;
DELIMITER ;;
CREATE TRIGGER `ordonnance_versions_no_update` BEFORE UPDATE ON `ordonnance_versions`
FOR EACH ROW
BEGIN
    IF COALESCE(@digiremed_key_rotation, 0) <> 1
       OR NEW.ordonnance_id <> OLD.ordonnance_id
       OR NEW.version <> OLD.version
       OR NEW.created_at <> OLD.created_at THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ordonnance_versions is append-only';
    END IF;
END;;
DELIMITER ;
