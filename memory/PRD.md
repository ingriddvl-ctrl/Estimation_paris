# VALORISATEUR PARIS — PRD

## Problème Original
Application web complète pour estimer le prix d'achat d'appartements à Paris (intramuros + petite couronne). L'app doit être très précise, surpassant les outils existants (PriceHubble, MeilleursAgents), en exploitant les données publiques et privées. Elle fournit des valorisations transparentes et justifiables via un waterfall chart, des comparables sur carte, des explications d'hypothèses, et un simulateur de coût total.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + Recharts + Leaflet + leaflet.heat
- **Backend**: FastAPI + MongoDB + ReportLab (PDF)
- **Intégrations**: DVF Cerema API, Géorisques API, Gemini 2.5 Flash (emergentintegrations)

## Modèle de Valorisation — RÈGLES CRITIQUES

### RÉSOLUTION SPATIALE (RÈGLE ABSOLUE)
Le modèle ne doit JAMAIS utiliser un prix moyen d'arrondissement comme point de départ.
Le point de départ est TOUJOURS les transactions DVF réelles pondérées.

### FRAÎCHEUR DES DONNÉES (RÈGLE ABSOLUE)
- Max 24 mois. Jamais au-delà.
- Pondération : 3 mois=1.0, 12 mois=0.7, 24 mois=0.4, >24 mois=exclusion
- anneemut_min=2024 dans l'appel API Cerema

### FILTRAGE DES ANOMALIES (NETTOYAGE OBLIGATOIRE)
- Prix/m² < 5 000 € ou > 20 000 € exclus (25 000 pour 6e/7e/8e arrondissements)
- Surface < 20 m² exclue (chambres de service)
- Surface > 200% ou < 50% de la surface cible exclue
- Doublons parcelle/date/prix exclus (lots en bloc, VEFA)
- Outliers > 2σ de la médiane exclus

### SEGMENTATION PAR TYPE
- Surface ±30% = poids 1.0, ±30-50% = poids 0.5, au-delà = exclusion

### RÈGLE DU VERDICT
- Écart < 10% → "PRIX JUSTE / DANS LE MARCHÉ"
- 10-20% au-dessus → "SURÉVALUÉ"
- > 20% au-dessus → "TRÈS SURÉVALUÉ"
- > 15% en-dessous → "SOUS-ÉVALUÉ" + warning automatique

### CALIBRATION CROISÉE
Warning incitant l'utilisateur à vérifier sur SeLoger, LeBonCoin, MeilleursAgents.
La moyenne d'arrondissement n'est PAS une référence valide.

## Fonctionnalités Implémentées

### MVP (Done)
- Formulaire multi-étapes (Localisation, Caractéristiques, État, Immeuble, Juridique)
- Moteur d'estimation avec médiane pondérée DVF + ajustements plafonnés
- Dashboard 7 onglets (Hypothèses, Marché, Expert, Estimation, Comparables, Risques, Documents)
- Waterfall chart, carte Leaflet des comparables avec heatmap
- Panel d'hypothèses transparent + micro-score de localisation
- Position marché (++, +, =, -, --)
- Sauvegarde/Historique/Partage
- Configuration des coefficients algorithmiques
- Upload de documents (Object Storage)
- Simulateur d'achat

### Résolution Spatiale Fine (Done - 09/04/2026)
- Recherche DVF progressive 200m→300m→500m
- Médiane pondérée distance + fraîcheur + similarité surface
- Micro-score de localisation
- Carte de chaleur (heatmap) + cercle de rayon

### Filtrage Strict DVF (Done - 09/04/2026)
- 24 mois max (pondération dégressive 3mo=1.0 → 24mo=0.4)
- Filtrage anomalies (prix, surface, doublons, outliers 2σ)
- Segmentation par surface (±30%=1.0, ±50%=0.5, au-delà=exclusion)
- Score de pertinence 0-100 pour chaque comparable (distance 40%, fraîcheur 35%, similarité 25%)
- Raisons d'exclusion transparentes pour chaque transaction rejetée
- Cross-calibration warning (SeLoger, LeBonCoin, MeilleursAgents)

### Exclusion Manuelle + Recalcul Temps Réel (Done - 09/04/2026)
- Clic sur une ligne pour exclure un comparable
- Endpoint POST /api/valuation/recalculate
- Nouveau prix recalculé instantanément affiché
- Bouton réinitialiser pour annuler les exclusions

### Listing Analyzer (Done - 09/04/2026)
- Upload fiches d'agence (PDF/images) + extraction IA (Gemini 2.5 Flash)
- Géocodage adresse → DVF local comme référence
- Analyse IA avec règle du verdict ±10%
- Export PDF de l'analyse

### PDF Report Generation (Done - 09/04/2026)
- Rapport estimation : 4 pages (couverture, décomposition, comparables, méthodologie)
- Rapport analyse listing : verdict, arguments, comparables DVF
- Endpoints: GET /api/report/pdf/{id} et GET /api/listing/report/pdf/{id}

## Backlog

### P1
- Entraîner un modèle XGBoost/LightGBM sur l'ensemble DVF Paris pour gradients infra-quartier
- Micro-score de rue (bruit, ensoleillement, largeur, commerces)

### P2
- Mode comparaison (jusqu'à 3 biens côte à côte)
- Compléter le Simulateur (détail frais notaire, courtier, assurance)

### P3
- Cache DVF Cerema pour pallier les erreurs 503
- Résidu de prestige par voie
- Intégration API SeLoger/LeBonCoin pour calibration croisée automatique
