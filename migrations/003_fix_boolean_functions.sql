-- Migration 003: Fix boolean functions to return TINYINT(1) instead of VARCHAR "True"/"False"
-- This eliminates the need for eval() in Python code

-- Drop existing functions
DROP FUNCTION IF EXISTS `isClasse`;
DROP FUNCTION IF EXISTS `isSubstance`;
DROP FUNCTION IF EXISTS `isSpecialite`;

-- Recreate isClasse with proper boolean return
DELIMITER ;;
CREATE FUNCTION `isClasse`(med TEXT) RETURNS TINYINT(1)
    DETERMINISTIC
    READS SQL DATA
BEGIN
    DECLARE result TINYINT(1) DEFAULT 0;
    IF (SELECT COUNT(*) FROM projet_ipa.classes WHERE denomination = med) > 0 THEN
        SET result = 1;
    END IF;
    RETURN result;
END;;
DELIMITER ;

-- Recreate isSubstance with proper boolean return
DELIMITER ;;
CREATE FUNCTION `isSubstance`(sub TEXT) RETURNS TINYINT(1)
    DETERMINISTIC
    READS SQL DATA
BEGIN
    DECLARE result TINYINT(1) DEFAULT 0;
    IF (SELECT COUNT(*) FROM projet_ipa.substances WHERE substances = sub) > 0 THEN
        SET result = 1;
    END IF;
    RETURN result;
END;;
DELIMITER ;

-- Recreate isSpecialite with proper boolean return
DELIMITER ;;
CREATE FUNCTION `isSpecialite`(med TEXT) RETURNS TINYINT(1)
    DETERMINISTIC
    READS SQL DATA
BEGIN
    DECLARE result TINYINT(1) DEFAULT 0;
    IF (SELECT COUNT(*) FROM projet_ipa.specialites WHERE specialites = med) > 0 THEN
        SET result = 1;
    END IF;
    RETURN result;
END;;
DELIMITER ;
