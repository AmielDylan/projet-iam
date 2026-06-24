#!/usr/bin/env python3
import pandas as pd
import re
import sys

# Charger le fichier Excel
file_path = "./Lien SPECIALITES-SUBSTANCES _OK-PHARMA.xlsx"

try:
    df = pd.read_excel(file_path)
    
    # Afficher les informations sur le fichier
    print("=== ANALYSE DU FICHIER ===")
    print(f"Dimensions: {df.shape}")
    print(f"\nColonnes: {df.columns.tolist()}")
    print(f"\nPremières 5 lignes:")
    print(df.head(5))
    print(f"\nNombre de valeurs non nulles par colonne:")
    print(df.count())
    
    # Afficher quelques exemples de la première colonne
    print("\n=== EXEMPLES DE SPÉCIALITÉS (20 premières) ===")
    first_col_name = df.columns[0]
    for i, val in enumerate(df[first_col_name].head(20).tolist()):
        print(f"{i+1}. {val}")
        
except Exception as e:
    print(f"Erreur: {e}")
    sys.exit(1)
