-- Migration 004: Fix getInteractionsClasses to check both directions
-- Interactions should be found regardless of which medication is entered first

DROP PROCEDURE IF EXISTS `getInteractionsClasses`;

DELIMITER ;;
CREATE PROCEDURE `getInteractionsClasses`(firstMed TEXT, secondMed TEXT)
BEGIN
    DECLARE med1_id INT;
    DECLARE med2_id INT;

    -- Get class IDs
    SELECT id INTO med1_id FROM projet_ipa.classes WHERE denomination = firstMed LIMIT 1;
    SELECT id INTO med2_id FROM projet_ipa.classes WHERE denomination = secondMed LIMIT 1;

    -- Check both directions: (med1, med2) OR (med2, med1)
    SELECT id FROM projet_ipa.interactions_classes
    WHERE (med_1 = med1_id AND med_2 = med2_id)
       OR (med_1 = med2_id AND med_2 = med1_id);
END;;
DELIMITER ;
