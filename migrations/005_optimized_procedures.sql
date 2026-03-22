-- Migration 005: Optimized procedures for better performance
-- These procedures reduce the number of database round-trips

-- Drop existing procedures if they exist
DROP PROCEDURE IF EXISTS `get_full_interactions`;
DROP PROCEDURE IF EXISTS `validate_medication`;
DROP PROCEDURE IF EXISTS `get_medication_type`;
DROP PROCEDURE IF EXISTS `get_classes_for_medication`;

-- Combined validation procedure: checks all types in one call
DELIMITER ;;
CREATE PROCEDURE `validate_medication`(IN med_name TEXT)
BEGIN
    SELECT
        (SELECT COUNT(*) > 0 FROM projet_ipa.classes WHERE denomination = med_name) AS is_classe,
        (SELECT COUNT(*) > 0 FROM projet_ipa.substances WHERE substances = med_name) AS is_substance,
        (SELECT COUNT(*) > 0 FROM projet_ipa.specialites WHERE specialites = med_name) AS is_specialite;
END;;
DELIMITER ;

-- Get medication type as a single string
DELIMITER ;;
CREATE PROCEDURE `get_medication_type`(IN med_name TEXT)
BEGIN
    DECLARE is_cls TINYINT(1) DEFAULT 0;
    DECLARE is_sub TINYINT(1) DEFAULT 0;
    DECLARE is_spe TINYINT(1) DEFAULT 0;

    SELECT COUNT(*) > 0 INTO is_cls FROM projet_ipa.classes WHERE denomination = med_name;
    SELECT COUNT(*) > 0 INTO is_sub FROM projet_ipa.substances WHERE substances = med_name;
    SELECT COUNT(*) > 0 INTO is_spe FROM projet_ipa.specialites WHERE specialites = med_name;

    SELECT
        CASE
            WHEN is_cls = 1 THEN 'classe'
            WHEN is_sub = 1 THEN 'substance'
            WHEN is_spe = 1 THEN 'specialite'
            ELSE 'unknown'
        END AS medication_type,
        is_cls AS is_classe,
        is_sub AS is_substance,
        is_spe AS is_specialite;
END;;
DELIMITER ;

-- Get all classes for a medication (regardless of type)
DELIMITER ;;
CREATE PROCEDURE `get_classes_for_medication`(IN med_name TEXT)
BEGIN
    DECLARE is_cls TINYINT(1) DEFAULT 0;
    DECLARE is_sub TINYINT(1) DEFAULT 0;
    DECLARE is_spe TINYINT(1) DEFAULT 0;

    SELECT COUNT(*) > 0 INTO is_cls FROM projet_ipa.classes WHERE denomination = med_name;
    SELECT COUNT(*) > 0 INTO is_sub FROM projet_ipa.substances WHERE substances = med_name;
    SELECT COUNT(*) > 0 INTO is_spe FROM projet_ipa.specialites WHERE specialites = med_name;

    IF is_cls = 1 THEN
        -- If it's a class, return it directly
        SELECT id, denomination AS class_name
        FROM projet_ipa.classes
        WHERE denomination = med_name;
    ELSEIF is_sub = 1 THEN
        -- If it's a substance, get its associated classes
        SELECT c.id, c.denomination AS class_name
        FROM projet_ipa.classes c
        INNER JOIN projet_ipa.liaisons_cs lcs ON c.id = lcs.id_classes
        INNER JOIN projet_ipa.substances s ON lcs.id_substance = s.id
        WHERE s.substances = med_name;
    ELSEIF is_spe = 1 THEN
        -- If it's a specialite, get classes via substance chain
        SELECT DISTINCT c.id, c.denomination AS class_name
        FROM projet_ipa.classes c
        INNER JOIN projet_ipa.liaisons_cs lcs ON c.id = lcs.id_classes
        INNER JOIN projet_ipa.liaisons_ss lss ON lcs.id_substance = lss.id_substance
        INNER JOIN projet_ipa.specialites sp ON lss.id_specialites = sp.id
        WHERE sp.specialites = med_name;
    END IF;
END;;
DELIMITER ;

-- Main optimized procedure: get full interactions in one call
DELIMITER ;;
CREATE PROCEDURE `get_full_interactions`(IN med1_name TEXT, IN med2_name TEXT)
BEGIN
    -- Create temporary tables to store class IDs
    DROP TEMPORARY TABLE IF EXISTS tmp_classes_1;
    DROP TEMPORARY TABLE IF EXISTS tmp_classes_2;

    CREATE TEMPORARY TABLE tmp_classes_1 (
        class_id INT,
        class_name VARCHAR(255)
    );

    CREATE TEMPORARY TABLE tmp_classes_2 (
        class_id INT,
        class_name VARCHAR(255)
    );

    -- Get classes for medication 1
    -- Check if it's a class
    INSERT INTO tmp_classes_1 (class_id, class_name)
    SELECT id, denomination FROM projet_ipa.classes WHERE denomination = med1_name;

    -- Check if it's a substance
    INSERT INTO tmp_classes_1 (class_id, class_name)
    SELECT c.id, c.denomination
    FROM projet_ipa.classes c
    INNER JOIN projet_ipa.liaisons_cs lcs ON c.id = lcs.id_classes
    INNER JOIN projet_ipa.substances s ON lcs.id_substance = s.id
    WHERE s.substances = med1_name
    AND c.id NOT IN (SELECT class_id FROM tmp_classes_1);

    -- Check if it's a specialite
    INSERT INTO tmp_classes_1 (class_id, class_name)
    SELECT DISTINCT c.id, c.denomination
    FROM projet_ipa.classes c
    INNER JOIN projet_ipa.liaisons_cs lcs ON c.id = lcs.id_classes
    INNER JOIN projet_ipa.liaisons_ss lss ON lcs.id_substance = lss.id_substance
    INNER JOIN projet_ipa.specialites sp ON lss.id_specialites = sp.id
    WHERE sp.specialites = med1_name
    AND c.id NOT IN (SELECT class_id FROM tmp_classes_1);

    -- Get classes for medication 2
    INSERT INTO tmp_classes_2 (class_id, class_name)
    SELECT id, denomination FROM projet_ipa.classes WHERE denomination = med2_name;

    INSERT INTO tmp_classes_2 (class_id, class_name)
    SELECT c.id, c.denomination
    FROM projet_ipa.classes c
    INNER JOIN projet_ipa.liaisons_cs lcs ON c.id = lcs.id_classes
    INNER JOIN projet_ipa.substances s ON lcs.id_substance = s.id
    WHERE s.substances = med2_name
    AND c.id NOT IN (SELECT class_id FROM tmp_classes_2);

    INSERT INTO tmp_classes_2 (class_id, class_name)
    SELECT DISTINCT c.id, c.denomination
    FROM projet_ipa.classes c
    INNER JOIN projet_ipa.liaisons_cs lcs ON c.id = lcs.id_classes
    INNER JOIN projet_ipa.liaisons_ss lss ON lcs.id_substance = lss.id_substance
    INNER JOIN projet_ipa.specialites sp ON lss.id_specialites = sp.id
    WHERE sp.specialites = med2_name
    AND c.id NOT IN (SELECT class_id FROM tmp_classes_2);

    -- Get all interactions between the two sets of classes (bidirectional)
    SELECT DISTINCT
        t1.class_name AS class_1,
        t2.class_name AS class_2,
        ic.id AS interaction_id,
        ic.details,
        ic.risques,
        n.niveaux AS niveau,
        ic.niveau AS niveau_id,
        ic.actions
    FROM tmp_classes_1 t1
    CROSS JOIN tmp_classes_2 t2
    INNER JOIN projet_ipa.interactions_classes ic ON
        (ic.med_1 = t1.class_id AND ic.med_2 = t2.class_id)
        OR (ic.med_1 = t2.class_id AND ic.med_2 = t1.class_id)
    LEFT JOIN projet_ipa.niveaux n ON ic.niveau = n.id
    ORDER BY ic.niveau DESC;

    -- Cleanup
    DROP TEMPORARY TABLE IF EXISTS tmp_classes_1;
    DROP TEMPORARY TABLE IF EXISTS tmp_classes_2;
END;;
DELIMITER ;
