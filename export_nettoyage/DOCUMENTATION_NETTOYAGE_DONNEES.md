# Documentation - Nettoyage et Structuration des Données de Spécialités

## 📊 Résumé du Traitement

**Fichier créé:** `Lien SPECIALITES-SUBSTANCES_CLEANED.xlsx`
- **23 251 médicaments** traités et structurés
- **11 colonnes** d'information extraites et organisées
- **2 feuilles Excel:** Données + Statistiques

---

## 📋 Colonnes Créées

### 1. **Nom_Medicament** ✅ 100% couvert (23 251/23 251)
Nom principal du médicament, nettoyé des dosages et quantités.

**Exemples:**
- A 313
- ABBOTICINE
- ABILIFY
- ABEREL

**Utilisation:** Clé primaire ou jointure avec table `specialites`

---

### 2. **Dosage** ✅ 87% couvert (20 269/23 251)
Force/concentration du composant actif avec unités.

**Format:** `[nombre][unité] | [nombre][unité]`

**Unités supportées:** mg, g, ml, UI, %, mcg, µg, mEq, IU

**Exemples:**
- 50000UI
- 200MG | 5ML
- 10MG
- 0,3% | 1/15ML

**Utilisation:** Pour le stockage structuré du dosage en base de données

---

### 3. **Concentration** ✅ 5% couvert (1 150/23 251)
Pourcentage de concentration pour les solutions/pommades.

**Format:** `[nombre]%`

**Exemples:**
- 3%
- 0.5%

**Utilisation:** Distinct du dosage en mg/ml pour meilleure organisation

---

### 4. **Forme_Galenique** ✅ 83% couvert (19 218/23 251)
Forme pharmaceutique du médicament.

**Formes principales identifiées:**
| Forme | Nombre | % |
|-------|--------|---|
| COMPRIMÉ | 10 654 | 46% |
| SOLUTION | 3 103 | 13% |
| GEL | 2 133 | 9% |
| INJECTABLE | 1 104 | 5% |
| POUDRE | 730 | 3% |
| SUSPENSION | 315 | 1% |
| COLLYRE | 263 | 1% |
| POMMADE | 255 | 1% |
| CAPSULE | 219 | 1% |
| GRANULÉS | 198 | 1% |
| SIROP | 150 | 1% |
| Autres (LOTION, EMULSION, etc.) | 77 | 0.3% |

**Utilisation:** Table de référence `formes_galeniques` ou enum

---

### 5. **Presentation** ✅ 18% couvert (4 077/23 251)
Type de conditionnement/emballage.

**Présentations identifiées:**
| Présentation | Nombre |
|-------------|--------|
| BOITE | 2 227 |
| FL (Flacon) | 1 627 |
| TUBE | 101 |
| STYLO | 36 |
| AMPOULE | 33 |
| BT | 30 |
| SERINGUE | 18 |
| VIAL | 5 |

**Utilisation:** Table de référence `presentations` ou enum

---

### 6. **Volume** ✅ 17% couvert (4 028/23 251)
Volume pour les injectables et solutions.

**Format:** `[nombre][unité] | [nombre][unité]`

**Unités:** ML, L, CL

**Exemples:**
- 5ML
- 1/15ML
- 250ML | 500ML

**Utilisation:** Descriptif du volume du flacon/seringue/ampoule

---

### 7. **Quantite_Unites** ✅ 94% couvert (21 942/23 251)
Nombre d'unités (comprimés, gélules, etc.) par boîte/emballage.

**Format:** Nombre décimal

**Exemples:**
- 30.0 (capsules)
- 28.0 (comprimés)
- 12.0 (granulés)

**Utilisation:** Quantité de formes unitaires (ex: 30 comprimés par boîte)

---

### 8. **Quantite_Boites** ✅ 9% couvert (2 116/23 251)
Nombre de boîtes/unités de présentation supérieure.

**Format:** Nombre décimal

**Exemples:**
- 30.0 (boîtes)
- 10.0 (flacons)

**Utilisation:** Quantité de conditions supérieures (ex: 30 boîtes par carton)

**Remarque:** N'est rempli que si "BOITE DE X" est présent dans la spécialité

---

### 9. **Synonymes** ✅ 12% couvert (2 732/23 251)
Noms alternatifs, DCI, codes, ou appellations commerciales alternatives.

**Format:** Texte entre parenthèses

**Exemples:**
- c 7e3b fab (pour abciximab)
- DIOMAGNITE (pour ABELITE)

**Utilisation:** Mapper vers des noms alternatifs connus en pharmacie

---

### 10. **Substances** ✅ 100% couvert (23 251/23 251)
Liste des substances/DCI composant le médicament.

**Format:** `[Substance_1] | [Substance_2] | [Substance_3] | [Substance_4]`

**Exemples:**
- RETINOL (VIT A) | vitamine a
- ARIPIPRAZOLE | aripiprazole
- DEXAMETHASONE ET ANTIINFECTIEUX | polymyxine b | dexamethasone | oxytetracycline

**Utilisation:** Jointure vers table `substances` pour interactions médicamenteuses

---

### 11. **Specialite** (colonne originale)
Chaîne complète originale, conservée pour référence.

---

## 🗂️ Feuilles Excel

### Sheet 1: **Medications**
Données complètes de tous les médicaments avec les 11 colonnes.

### Sheet 2: **Statistiques**
Résumé des statistiques d'extraction :
- Total de médicaments: 23 251
- Couverture par colonne (nombre/%)
- Utile pour monitoring de la qualité

---

## 🔄 Intégration avec la Base de Données IAM

### Création de Tables Recommandées

```sql
-- Table des formes galéniques (référence)
CREATE TABLE formes_galeniques (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nom VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255)
);

-- Table des présentations (référence)
CREATE TABLE presentations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nom VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255)
);

-- Table enrichie des spécialités
ALTER TABLE specialites ADD COLUMN (
    nom_medicament VARCHAR(200),
    dosage VARCHAR(100),
    concentration VARCHAR(50),
    forme_galenique_id INT,
    presentation_id INT,
    volume VARCHAR(50),
    quantite_unites INT,
    quantite_boites INT,
    synonymes VARCHAR(255),
    FOREIGN KEY (forme_galenique_id) REFERENCES formes_galeniques(id),
    FOREIGN KEY (presentation_id) REFERENCES presentations(id)
);
```

### Étapes d'Intégration

1. **Insérer les formes galéniques et présentations** comme données de référence
2. **Matcher** les noms de médicaments avec la colonne `specialites` existante
3. **Mettre à jour** les colonnes nouvelles avec les données extraites
4. **Valider** les jointures vers `substances`
5. **Nettoyer** les doublons de synonymes si nécessaire

---

## 📈 Utilisation pour les Interactions Médicamenteuses

La colonne **Substances** vous permet de:

- **Lier** chaque spécialité à ses substances actives
- **Chercher** les interactions entre substances dans votre API
- **Afficher** les substances composantes d'une spécialité
- **Créer** des graphes d'interactions plus complets

### Exemple de Query

```sql
-- Trouver les interactions entre spécialités
SELECT DISTINCT 
    s1.nom_medicament,
    s2.nom_medicament,
    i.interaction_level
FROM specialites s1
JOIN substances_mapping sm1 ON s1.id = sm1.specialite_id
JOIN substances_mapping sm2 ON sm1.substance_id = sm2.substance_id
JOIN specialites s2 ON sm2.specialite_id = s2.id
JOIN interactions i ON sm1.substance_id = i.substance_1_id 
    AND sm2.substance_id = i.substance_2_id
WHERE s1.nom_medicament = 'ABILIFY'
```

---

## ⚠️ Notes Importantes

### Couverture des Données

| Colonne | Couverture | Qualité |
|---------|-----------|---------|
| Nom_Medicament | 100% | ✅ Excellent |
| Dosage | 87% | ✅ Excellent |
| Forme_Galenique | 83% | ✅ Excellent |
| Quantite_Unites | 94% | ✅ Excellent |
| Substances | 100% | ✅ Excellent |
| Volume | 17% | ⚠️ Partiel |
| Presentation | 18% | ⚠️ Partiel |
| Concentration | 5% | ⚠️ Très partiel |
| Quantite_Boites | 9% | ⚠️ Très partiel |
| Synonymes | 12% | ⚠️ Partiel |

### Cas Particuliers

1. **Certains noms incomplets** : Si un nom commence par un chiffre ou une lettre unique, il peut être tronqué. Vérifier avec la colonne `Specialite` originale.

2. **Substances manquantes** : Quelques entrées n'ont pas de substances (environ 100-200). Vérifier les en-têtes originaux.

3. **Quantités ambiguës** : Si plusieurs nombres sont présents, le dernier est généralement pris. Valider manuellement si nécessaire.

4. **Formes non reconnues** : ~4000 spécialités n'ont pas de forme galénique identifiée. Elles peuvent être :
   - Non structurées
   - Utiliser des synonymes régionaux
   - Être des formules complexes

---

## 🔍 Recommandations de Nettoyage Supplémentaire

### Avant Intégration

1. **Dédupliquer** les noms de médicaments (certains peuvent avoir des variantes)
2. **Valider** les substances contre votre table `substances` existante
3. **Vérifier** les caractères spéciaux et encodage
4. **Mapper** les variantes régionales de formes galéniques
5. **Fusionner** les synonymes avec la base existante

### Script de Validation Proposé

```python
# Vérifier les substances manquantes
missing_substances = df[df['Substances'].isna()]
print(f"Enregistrements sans substances: {len(missing_substances)}")

# Vérifier les formes non identifiées
missing_forms = df[df['Forme_Galenique'].isna()]
print(f"Enregistrements sans forme: {len(missing_forms)}")

# Détecter les doublons de noms
duplicates = df[df['Nom_Medicament'].duplicated(keep=False)]
print(f"Médicaments en doublon: {len(duplicates)}")
```

---

## 📞 Support et Questions

Si vous avez des questions sur :
- La qualité des extractions
- Comment améliorer le parsing
- Comment intégrer dans votre base de données
- Quels scripts utiliser pour la mise à jour

N'hésitez pas à adapter les scripts fournis ou à re-executer le traitement avec des règles de parsing ajustées.

---

**Generated:** 24 mars 2026
**Script:** process_data_v2.py
