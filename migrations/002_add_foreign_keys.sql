-- Migration 002: Add foreign key constraints for referential integrity
-- Run this AFTER 001_fix_schema.sql

-- Foreign key: liaisons_cs.id_classes -> classes.id
ALTER TABLE `liaisons_cs`
ADD CONSTRAINT `fk_liaisons_cs_classes`
FOREIGN KEY (`id_classes`) REFERENCES `classes` (`id`)
ON DELETE CASCADE ON UPDATE CASCADE;

-- Foreign key: liaisons_cs.id_substance -> substances.id
ALTER TABLE `liaisons_cs`
ADD CONSTRAINT `fk_liaisons_cs_substances`
FOREIGN KEY (`id_substance`) REFERENCES `substances` (`id`)
ON DELETE CASCADE ON UPDATE CASCADE;

-- Foreign key: liaisons_ss.id_specialites -> specialites.id
ALTER TABLE `liaisons_ss`
ADD CONSTRAINT `fk_liaisons_ss_specialites`
FOREIGN KEY (`id_specialites`) REFERENCES `specialites` (`id`)
ON DELETE CASCADE ON UPDATE CASCADE;

-- Foreign key: liaisons_ss.id_substance -> substances.id
ALTER TABLE `liaisons_ss`
ADD CONSTRAINT `fk_liaisons_ss_substances`
FOREIGN KEY (`id_substance`) REFERENCES `substances` (`id`)
ON DELETE CASCADE ON UPDATE CASCADE;

-- Foreign key: interactions_classes.med_1 -> classes.id
ALTER TABLE `interactions_classes`
ADD CONSTRAINT `fk_interactions_med1`
FOREIGN KEY (`med_1`) REFERENCES `classes` (`id`)
ON DELETE CASCADE ON UPDATE CASCADE;

-- Foreign key: interactions_classes.med_2 -> classes.id
ALTER TABLE `interactions_classes`
ADD CONSTRAINT `fk_interactions_med2`
FOREIGN KEY (`med_2`) REFERENCES `classes` (`id`)
ON DELETE CASCADE ON UPDATE CASCADE;

-- Foreign key: interactions_classes.niveau -> niveaux.id
ALTER TABLE `interactions_classes`
ADD CONSTRAINT `fk_interactions_niveau`
FOREIGN KEY (`niveau`) REFERENCES `niveaux` (`id`)
ON DELETE SET NULL ON UPDATE CASCADE;

-- Foreign key: liaison_ps.id_substance -> substances.id
ALTER TABLE `liaison_ps`
ADD CONSTRAINT `fk_liaison_ps_substances`
FOREIGN KEY (`id_substance`) REFERENCES `substances` (`id`)
ON DELETE CASCADE ON UPDATE CASCADE;

-- Foreign key: liaison_ps.id_plante -> plantes.id
ALTER TABLE `liaison_ps`
ADD CONSTRAINT `fk_liaison_ps_plantes`
FOREIGN KEY (`id_plante`) REFERENCES `plantes` (`id`)
ON DELETE CASCADE ON UPDATE CASCADE;
