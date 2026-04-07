# Valorisateur d'Appartements Paris - PRD

## Problem Statement
Application web de valorisation d'appartements à l'achat à Paris, connectée aux bases de données publiques (DVF, BAN, Géorisques), avec formulaire multi-étapes et algorithme d'estimation transparent.

## Architecture
- Frontend: React + Tailwind + Shadcn/UI + Leaflet + Recharts
- Backend: FastAPI + MongoDB
- External APIs: DVF Cerema (transactions), BAN data.gouv (géocodage), Géorisques (risques)

## User Personas
- Acheteurs immobiliers à Paris cherchant à estimer un bien
- Agents immobiliers vérifiant des prix
- Investisseurs analysant la rentabilité

## Core Requirements
1. Formulaire multi-étapes (5 étapes: localisation, bien, état, immeuble, juridique)
2. Moteur de valorisation avec DVF réel + coefficients d'ajustement
3. Visualisations (waterfall chart, carte comparables, scores localisation)
4. Simulateur de coût d'achat complet
5. Historique et sauvegarde des estimations
6. Partage en lecture seule
7. Coefficients d'algorithme éditables

## Implemented (2026-04-07)
- ✅ Landing page avec design Swiss & High-Contrast
- ✅ Formulaire multi-étapes complet (5 étapes, 40+ champs)
- ✅ Autocomplétion d'adresse via API BAN data.gouv.fr
- ✅ Moteur de valorisation connecté API DVF Cerema (transactions réelles)
- ✅ Waterfall chart de décomposition du prix
- ✅ Carte interactive Leaflet des comparables DVF
- ✅ Scores de localisation (7 sous-catégories)
- ✅ Analyse de risques (DPE, Géorisques, copropriété)
- ✅ Simulateur de coût d'achat (notaire, crédit, assurance, travaux)
- ✅ Historique des estimations avec CRUD
- ✅ Partage en lecture seule via lien
- ✅ Paramètres des coefficients éditables
- ✅ Navigation complète entre toutes les pages

## Backlog
### P0 - Critique
- (aucun)

### P1 - Important
- Export PDF du rapport de valorisation
- Mode comparaison 3 biens côte à côte
- Scores de localisation dynamiques (connexion RATP/INSEE/Bruitparif)
- Alertes sur nouvelles transactions DVF

### P2 - Nice to have  
- Analyse d'investissement (rendement locatif, TRI)
- Dark mode
- Internationalisation (EN)
- Pre-remplissage automatique DPE via API ADEME
- Intégration BDNB (Base Nationale des Bâtiments)
