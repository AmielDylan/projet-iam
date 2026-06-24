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
# Réinitialiser les colonnes à partir de la ligne 3
true_headers = df.iloc[2].tolist()
df = df.iloc[3:].reset_index(drop=True)  # Commencer à partir de la ligne 4
df.columns = true_headers

# Remplacer les colonnes sans nom par des noms standards
df.columns = ['Specialite', 'Substance_1', 'Substance_2', 'Substance_3', 'Substance_4']

# Supprimer les lignes complètement vides
df = df.dropna(how='all')

# Réinitialiser l'index
df = df.reset_index(drop=True)

print("=== DONNÉES NETTOYÉES ===")
print(f"Dimensions après nettoyage: {df.shape}")
print(f"\nPremières 10 spécialités:")
for i, spec in enumerate(df['Specialite'].head(10)):
    print(f"{i+1}. {spec}")

print(f"\n=== ANALYSE DES PATTERNS ===")
# Analyser les patterns pour créer les colonnes
sample_specialites = df['Specialite'].dropna().head(50).tolist()

print("\nExemples de spécialités à parser:")
for i, spec in enumerate(sample_specialites[:15]):
    print(f"{i+1}. {spec}")

# Sauvegarder les dataframe pour l'analyse
df.to_csv('/tmp/cleaned_data.csv', index=False, encoding='utf-8')
print("\n\nFichier temporaire créé: /tmp/cleaned_data.csv")
