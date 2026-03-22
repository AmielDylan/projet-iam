-- Migration 001: Fix schema issues and add indexes
-- This migration fixes the id_substance column type and adds performance indexes

-- Step 1: Fix liaisons_cs.id_substance from TEXT to INT
-- First, create a temporary column
ALTER TABLE `liaisons_cs` ADD COLUMN `id_substance_new` INT NULL;

-- Copy data (assuming the TEXT values are numeric)
UPDATE `liaisons_cs` SET `id_substance_new` = CAST(`id_substance` AS UNSIGNED);

-- Drop old column and rename new one
ALTER TABLE `liaisons_cs` DROP COLUMN `id_substance`;
ALTER TABLE `liaisons_cs` CHANGE COLUMN `id_substance_new` `id_substance` INT NOT NULL;

-- Step 2: Add indexes on frequently queried columns

-- Index on classes.denomination for medication lookups
CREATE INDEX `idx_classes_denomination` ON `classes` (`denomination`(100));

-- Index on substances.substances for substance lookups
CREATE INDEX `idx_substances_name` ON `substances` (`substances`(100));

-- Index on specialites.specialites for brand name lookups
CREATE INDEX `idx_specialites_name` ON `specialites` (`specialites`);

-- Indexes on liaisons_cs for class-substance joins
CREATE INDEX `idx_liaisons_cs_id_classes` ON `liaisons_cs` (`id_classes`);
CREATE INDEX `idx_liaisons_cs_id_substance` ON `liaisons_cs` (`id_substance`);

-- Indexes on interactions_classes for interaction lookups
CREATE INDEX `idx_interactions_med1` ON `interactions_classes` (`med_1`);
CREATE INDEX `idx_interactions_med2` ON `interactions_classes` (`med_2`);

-- Composite index for bidirectional interaction queries
CREATE INDEX `idx_interactions_both_meds` ON `interactions_classes` (`med_1`, `med_2`);

-- Index on liaisons_ss for specialite-substance joins
CREATE INDEX `idx_liaisons_ss_substance` ON `liaisons_ss` (`id_substance`);
