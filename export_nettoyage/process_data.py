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
df = df.reset_index(drop=True)

# Filtrer le dataframe pour garder seulement les lignes avec une spécialité
df = df[df['Specialite'].notna() & (df['Specialite'].str.strip() != '')]
df = df.reset_index(drop=True)

# Fonctions de parsing
def extract_synonymes(spec_str):
    """Extraire les synonymes entre parenthèses"""
    if pd.isna(spec_str):
        return None
    match = re.search(r'\((.*?)\)', str(spec_str))
    return match.group(1) if match else None

def extract_nom_medicament(spec_str):
    """Extraire le nom du médicament (avant les chiffres/dosages)"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str).strip()
    # Enlever les synonymes d'abord
    spec_str = re.sub(r'\(.*?\)', '', spec_str).strip()
    # Le nom est généralement avant les chiffres/dosages
    match = re.match(r'^([A-Za-zÀ-ÿ\s]+?)(\d|,)', spec_str)
    return match.group(1).strip() if match else spec_str

def extract_dosage(spec_str):
    """Extraire tous les dosages (nombres avec unités)"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str)
    # Pattern pour capturer doses: nombre + unité (mg, g, ml, UI, %, mcg, etc.)
    matches = re.findall(r'(\d+\s*[,.]?\s*\d*)\s*(mg|g|ml|UI|%|mcg|µg|mEq|IU|U\.I)', spec_str, re.IGNORECASE)
    if matches:
        return ' / '.join([f"{m[0].replace(' ', '')}{m[1]}" for m in matches])
    return None

def extract_forme_galenique(spec_str):
    """Extraire la forme galénique"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str).upper()
    
    formes = {
        'CPR': ['CPR', 'COMPRIMÉ', 'COMPRIME'],
        'CAPSULE': ['CAPSULE', 'CAP'],
        'INJECTION': ['INJECTION', 'INJECTABLE', 'PERFUSION'],
        'SOLUTION': ['SOL', 'SOLUTION'],
        'POMMADE': ['POMMADE', 'ONGUENT', 'CRÈME', 'CREME'],
        'GRANULES': ['GRANULES', 'GRANULE'],
        'POUDRE': ['POUDRE', 'PDR'],
        'SIROP': ['SIROP'],
        'SUSPENSION': ['SUSPENSION', 'SUSP'],
        'PATCH': ['PATCH'],
        'SPRAY': ['SPRAY', 'AÉROSOL'],
        'GEL': ['GEL'],
        'LIQUIDE': ['LIQUIDE'],
    }
    
    for forme, keywords in formes.items():
        for keyword in keywords:
            if keyword in spec_str:
                return forme
    return None

def extract_quantite(spec_str):
    """Extraire la quantité/nombre de boîtes/unités"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str)
    
    # Chercher des patterns comme "30", "28", "1/15"
    # Généralement à la fin de la chaîne
    matches = re.findall(r'(\d+)\s*(BOITE|FL|FLACON|AMPOULE|TUBE|BT|STICK|GODET|SERINGUE)?', spec_str, re.IGNORECASE)
    
    if matches:
        # Prendre le dernier match (généralement la quantité finale)
        last_match = matches[-1]
        qty = last_match[0]
        unit = last_match[1] if last_match[1] else ''
        return f"{qty} {unit}".strip() if unit else qty
    return None

def extract_volume(spec_str):
    """Extraire le volume pour les injectables (ex: 1/15 ML)"""
    if pd.isna(spec_str):
        return None
    spec_str = str(spec_str).upper()
    
    # Pattern pour fractions et volumes (ex: 1/15 ML, 5ML, 250ML)
    matches = re.findall(r'(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)\s*(ML|L)', spec_str, re.IGNORECASE)
    if matches:
        return ' / '.join([f"{m[0]}{m[1]}" for m in matches])
    return None

# Créer les nouvelles colonnes
print("=== EXTRACTION DES DONNÉES ===")
print("Parsing des spécialités...")

df['Synonymes'] = df['Specialite'].apply(extract_synonymes)
df['Nom_Medicament'] = df['Specialite'].apply(extract_nom_medicament)
df['Dosage'] = df['Specialite'].apply(extract_dosage)
df['Forme_Galenique'] = df['Specialite'].apply(extract_forme_galenique)
df['Quantite'] = df['Specialite'].apply(extract_quantite)
df['Volume'] = df['Specialite'].apply(extract_volume)

# Réorganiser les colonnes
colonnes_finales = [
    'Nom_Medicament',
    'Dosage', 
    'Forme_Galenique',
    'Volume',
    'Quantite',
    'Synonymes',
    'Specialite',
    'Substance_1',
    'Substance_2', 
    'Substance_3',
    'Substance_4'
]

df_final = df[colonnes_finales].copy()

# Sauvegarder en Excel
output_path = "Lien SPECIALITES-SUBSTANCES_CLEANED.xlsx"
df_final.to_excel(output_path, index=False, sheet_name='Data')

print(f"\n✓ Fichier créé: {output_path}")
print(f"✓ Nombre de lignes: {len(df_final)}")
print(f"✓ Colonnes: {', '.join(df_final.columns)}")

# Afficher des exemples
print("\n=== EXEMPLES DE RÉSULTATS ===")
print("\nPremières 10 lignes:")
for idx in range(min(10, len(df_final))):
    row = df_final.iloc[idx]
    print(f"\n{idx+1}. {row['Nom_Medicament']}")
    print(f"   Dosage: {row['Dosage']}")
    print(f"   Forme: {row['Forme_Galenique']}")
    print(f"   Volume: {row['Volume']}")
    print(f"   Quantité: {row['Quantite']}")
    if row['Synonymes']:
        print(f"   Synonymes: {row['Synonymes']}")
    print(f"   Substances: {', '.join(filter(pd.notna, [row['Substance_1'], row['Substance_2'], row['Substance_3'], row['Substance_4']]))}")

print("\n\n=== STATISTIQUES ===")
print(f"Noms de médicaments extraits: {df_final['Nom_Medicament'].notna().sum()}/{len(df_final)}")
print(f"Dosages extraits: {df_final['Dosage'].notna().sum()}/{len(df_final)}")
print(f"Formes galéniques identifiées: {df_final['Forme_Galenique'].notna().sum()}/{len(df_final)}")
print(f"Volumes extraits: {df_final['Volume'].notna().sum()}/{len(df_final)}")
print(f"Quantités extraites: {df_final['Quantite'].notna().sum()}/{len(df_final)}")
print(f"Synonymes trouvés: {df_final['Synonymes'].notna().sum()}/{len(df_final)}")

print("\n=== FORMES GALÉNIQUES UNIQUES ===")
formes = df_final['Forme_Galenique'].value_counts()
for forme, count in formes.head(15).items():
    print(f"{forme}: {count}")

print("\n✓ Traitement terminé!")
