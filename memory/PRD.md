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
- Formulaire multi-étapes complet (5 étapes, 40+ champs)
- Autocomplétion d'adresse via API BAN data.gouv.fr
- Moteur de valorisation connecté API DVF Cerema (transactions réelles)
- Coefficients recalibrés et plafonnés (max 18% cumulé) pour estimations réalistes
- Médiane tronquée DVF (trim 10%) pour réduire l'impact des outliers
- Waterfall chart de décomposition du prix
- Carte interactive Leaflet des comparables DVF
- Hypothèses détaillées : chaque ajustement expliqué en langage clair
- Position marché (++/+/=/−/−−) vs moyenne de l'arrondissement
- Comparables du marché (transactions récentes DVF 2023-2025) avec carte et stats
- Analyse expert : prix/pièce, charges copro, marge de négociation, coût détention 5 ans
- Upload de documents (PV AG, DPE, charges, plans, diagnostics) via object storage
- Simulateur de coût d'achat (notaire, crédit, assurance, travaux)
- Historique des estimations avec CRUD + partage en lecture seule
- Paramètres des coefficients entièrement éditables (y compris plafond cumulé)

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
