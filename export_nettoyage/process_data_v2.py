#!/usr/bin/env python3
import pandas as pd
import re
import warnings
warnings.filterwarnings('ignore')

# Charger le fichier Excel
file_path = "./Lien SPECIALITES-SUBSTANCES _OK-PHARMA.xlsx"

# Lire le fichier en ignorant les premières lignes d'en-tête
df = pd.read_excel(file_path)

# Les vraies en-têtes sont à la ligne 3 (index 2)
true_headers = df.iloc[2].tolist()
df = df.iloc[3:].reset_index(drop=True)
df.columns = true_headers

# Renommer les colonnes standards
df.columns = ['Specialite', 'Substance_1', 'Substance_2', 'Substance_3', 'Substance_4']

# Supprimer les lignes complètement vides
df = df.dropna(how='all')
df = df[df['Specialite'].notna() & (df['Specialite'].str.strip() != '')]
df = df.reset_index(drop=True)

# Fonctions de parsing améliorées
def extract_synonymes(spec_str):
    """Extraire les synonymes entre parenthèses"""
    if pd.isna(spec_str):
        return None
    match = re.search(r'\((.*?)\)', str(spec_str))
    return match.group(1).strip() if match else None

def extract_nom_medicament_ameliore(spec_str):
    """Extraire intelligemment le nom du médicament"""
    if pd.isna(spec_str):
        return None
    
    spec_str = str(spec_str).strip()
    
    # Enlever les synonymes d'abord
    spec_clean = re.sub(r'\(.*?\)', '', spec_str).strip()
    
    # Pattern: chercher où commence vraiment les dosages/quantités
    # Les dosages commencent généralement par un chiffre suivi d'une unité ou %
    # Mais on doit être prudent avec les noms qui commencent par des chiffres
    
    # Chercher le dernier mot alphabétique avant une dose ou quantity
    # Pattern: nombre + unité OU nombre + BOITE/FL/FLACON ou pourcentage
    match = re.search(r'^(.*?)(?:\d+\s*[,./]?\s*\d*\s*(?:mg|g|ml|UI|%|mcg|µg|mEq|IU|U\.I|BOITE|FL|FLACON|CPR|CAPSULE|GRANULE|POUDRE|SOLUTION|SOL|SUSP|POMMADE|CRÈME|PATCH|SPRAY|GEL))', spec_clean, re.IGNORECASE)
    
    if match:
        name = match.group(1).strip()
        # Nettoyer les espaces multiples
        name = re.sub(r'\s+', ' ', name)
        return name if name else spec_clean
    
    return spec_clean

def extract_presentation(spec_str):
    """Extraire la présentation/packaging (FL, FLACON, BOITE, AMPOULE, TUBE, SERINGUE)"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str).upper()
    
    presentations = ['BOITE', 'FL', 'FLACON', 'AMPOULE', 'TUBE', 'SERINGUE', 
                     'BT', 'STICK', 'GODET', 'VIAL', 'CARTOUCHE', 'STYLO']
    
    for pres in presentations:
        if pres in spec_str:
            return pres
    return None

def extract_dosage(spec_str):
    """Extraire tous les dosages (nombres avec unités)"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str)
    # Pattern pour capturer doses: nombre + unité
    matches = re.findall(r'(\d+\s*[,./]?\s*\d*)\s*(mg|g|ml|UI|%|mcg|µg|mEq|IU|U\.I|º)', spec_str, re.IGNORECASE)
    if matches:
        return ' | '.join([f"{m[0].replace(' ', '')}{m[1]}" for m in matches])
    return None

def extract_forme_galenique(spec_str):
    """Extraire la forme galénique"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str).upper()
    
    formes = {
        'COMPRIMÉ': ['comprimé', 'comprimé', 'CPR', 'COMPR'],
        'CAPSULE': ['CAPSULE', 'CAP'],
        'INJECTABLE': ['INJECTION', 'INJECTABLE', 'PERFUSION', 'INTRAVEINEUSE', 'IV'],
        'SOLUTION': ['SOL', 'SOLUTION'],
        'POMMADE': ['POMMADE', 'ONGUENT', 'CRÈME', 'CREME'],
        'GRANULÉS': ['GRANULES', 'GRANULE', 'GRANULÉ'],
        'POUDRE': ['POUDRE', 'PDR'],
        'SIROP': ['SIROP'],
        'SUSPENSION': ['SUSPENSION', 'SUSP'],
        'PATCH': ['PATCH'],
        'SPRAY': ['SPRAY', 'AÉROSOL', 'AEROSOL'],
        'GEL': ['GEL'],
        'LIQUIDE': ['LIQUIDE'],
        'EMULSION': ['ÉMULSION', 'EMULSION'],
        'LOTION': ['LOTION'],
        'COLLYRE': ['COLLYRE'],
        'PÂTE': ['PÂTE', 'PASTE'],
    }
    
    for forme, keywords in formes.items():
        for keyword in keywords:
            if keyword in spec_str:
                return forme
    return None

def extract_quantite_boites(spec_str):
    """Extraire la quantité de boîtes"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str)
    
    # Chercher "BOITE DE XX" ou "X BOITE"
    match = re.search(r'(?:BOITE|BT)\s+(?:DE)?\s*(\d+)', spec_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def extract_quantite_unites(spec_str):
    """Extraire la quantité d'unités (comprimés, gélules, etc.)"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str)
    
    # Chercher les nombres à la fin, généralement les quantités d'unités
    # Exclure les quantités dans les dosages (ex: 50 dans "50 000 UI")
    
    # Pattern: nombre à la fin de la chaîne qui n'est pas précédé d'une unité métrique
    matches = re.findall(r'\s(\d+)\s*(?:BOITE|FL|FLACON|AMPOULE|TUBE|BT|STICK|SERINGUE|$)', spec_str, re.IGNORECASE)
    
    if not matches:
        # Chercher juste le dernier nombre
        all_numbers = re.findall(r'\d+(?:\.\d+)?', spec_str)
        if all_numbers:
            return int(float(all_numbers[-1]))
    
    return int(matches[-1]) if matches else None

def extract_volume(spec_str):
    """Extraire le volume pour les injectables (ex: 1/15 ML, 5ML, 250ML)"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str).upper()
    
    # Pattern pour fractions et volumes
    matches = re.findall(r'(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)\s*(ML|L|CL)', spec_str)
    if matches:
        return ' | '.join([f"{m[0]}{m[1]}" for m in matches])
    return None

def extract_concentration(spec_str):
    """Extraire la concentration (ex: %)"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str)
    
    matches = re.findall(r'(\d+(?:\.\d+)?)\s*(%)', spec_str)
    if matches:
        return ' | '.join([f"{m[0]}{m[1]}" for m in matches])
    return None

# Créer les nouvelles colonnes
print("=== EXTRACTION AMÉLIORÉE DES DONNÉES ===")
print("Parsing des spécialités...")

df['Nom_Medicament'] = df['Specialite'].apply(extract_nom_medicament_ameliore)
df['Dosage'] = df['Specialite'].apply(extract_dosage)
df['Concentration'] = df['Specialite'].apply(extract_concentration)
df['Forme_Galenique'] = df['Specialite'].apply(extract_forme_galenique)
df['Presentation'] = df['Specialite'].apply(extract_presentation)
df['Volume'] = df['Specialite'].apply(extract_volume)
df['Quantite_Unites'] = df['Specialite'].apply(extract_quantite_unites)
df['Quantite_Boites'] = df['Specialite'].apply(extract_quantite_boites)
df['Synonymes'] = df['Specialite'].apply(extract_synonymes)

# Créer une colonne pour les substances combinées
df['Substances'] = df.apply(
    lambda row: ' | '.join(filter(lambda x: pd.notna(x) and x.strip() != '', 
                                  [row['Substance_1'], row['Substance_2'], row['Substance_3'], row['Substance_4']])),
    axis=1
)
df['Substances'] = df['Substances'].replace('', None)

# Réorganiser les colonnes
colonnes_finales = [
    'Nom_Medicament',
    'Dosage',
    'Concentration',
    'Forme_Galenique',
    'Presentation',
    'Volume',
    'Quantite_Unites',
    'Quantite_Boites',
    'Synonymes',
    'Substances',
    'Specialite',
]

df_final = df[colonnes_finales].copy()

# Sauvegarder en Excel
output_path = "Lien SPECIALITES-SUBSTANCES_CLEANED.xlsx"

# Créer un writer Excel pour ajouter une sheet additionnelle
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df_final.to_excel(writer, sheet_name='Medications', index=False)
    
    # Ajouter une sheet avec les statistiques
    stats = pd.DataFrame({
        'Métrique': [
            'Total de médicaments',
            'Noms extraits',
            'Dosages extraits',
            'Concentrations extraites',
            'Formes galéniques identifiées',
            'Présentations identifiées',
            'Volumes extraits',
            'Quantités (unités) extraites',
            'Quantités (boîtes) extraites',
            'Synonymes trouvés',
        ],
        'Nombre': [
            len(df_final),
            df_final['Nom_Medicament'].notna().sum(),
            df_final['Dosage'].notna().sum(),
            df_final['Concentration'].notna().sum(),
            df_final['Forme_Galenique'].notna().sum(),
            df_final['Presentation'].notna().sum(),
            df_final['Volume'].notna().sum(),
            df_final['Quantite_Unites'].notna().sum(),
            df_final['Quantite_Boites'].notna().sum(),
            df_final['Synonymes'].notna().sum(),
        ]
    })
    
    stats.to_excel(writer, sheet_name='Statistiques', index=False)

print(f"\n✓ Fichier créé: {output_path}")
print(f"✓ Nombre de lignes: {len(df_final)}")
print(f"✓ Colonnes: {', '.join(df_final.columns)}")

# Afficher des exemples
print("\n=== EXEMPLES DE RÉSULTATS ===")
print("\nPremières 10 lignes:")
for idx in range(min(10, len(df_final))):
    row = df_final.iloc[idx]
    print(f"\n{idx+1}. {row['Nom_Medicament']}")
    if pd.notna(row['Dosage']):
        print(f"   Dosage: {row['Dosage']}")
    if pd.notna(row['Concentration']):
        print(f"   Concentration: {row['Concentration']}")
    if pd.notna(row['Forme_Galenique']):
        print(f"   Forme: {row['Forme_Galenique']}")
    if pd.notna(row['Presentation']):
        print(f"   Présentation: {row['Presentation']}")
    if pd.notna(row['Volume']):
        print(f"   Volume: {row['Volume']}")
    if pd.notna(row['Quantite_Unites']):
        print(f"   Quantité (unités): {row['Quantite_Unites']}")
    if pd.notna(row['Quantite_Boites']):
        print(f"   Quantité (boîtes): {row['Quantite_Boites']}")
    if pd.notna(row['Synonymes']):
        print(f"   Synonymes: {row['Synonymes']}")
    if pd.notna(row['Substances']):
        print(f"   Substances: {row['Substances']}")

print("\n\n=== STATISTIQUES ===")
print(f"Noms de médicaments extraits: {df_final['Nom_Medicament'].notna().sum()}/{len(df_final)}")
print(f"Dosages extraits: {df_final['Dosage'].notna().sum()}/{len(df_final)}")
print(f"Concentrations extraites: {df_final['Concentration'].notna().sum()}/{len(df_final)}")
print(f"Formes galéniques identifiées: {df_final['Forme_Galenique'].notna().sum()}/{len(df_final)}")
print(f"Présentations identifiées: {df_final['Presentation'].notna().sum()}/{len(df_final)}")
print(f"Volumes extraits: {df_final['Volume'].notna().sum()}/{len(df_final)}")
print(f"Quantités (unités) extraites: {df_final['Quantite_Unites'].notna().sum()}/{len(df_final)}")
print(f"Quantités (boîtes) extraites: {df_final['Quantite_Boites'].notna().sum()}/{len(df_final)}")
print(f"Synonymes trouvés: {df_final['Synonymes'].notna().sum()}/{len(df_final)}")

print("\n=== FORMES GALÉNIQUES UNIQUES ===")
formes = df_final['Forme_Galenique'].value_counts()
for forme, count in formes.head(15).items():
    if pd.notna(forme):
        print(f"{forme}: {count}")

print("\n=== PRÉSENTATIONS UNIQUES ===")
presentations = df_final['Presentation'].value_counts()
for pres, count in presentations.head(10).items():
    if pd.notna(pres):
        print(f"{pres}: {count}")

print("\n✓ Traitement terminé!")
