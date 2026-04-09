# VALORISATEUR PARIS + PETITE COURONNE — PRD

## Problème Original
Application web complète pour estimer le prix d'achat d'appartements à Paris (intramuros) ET petite couronne (92, 93, 94 — Neuilly, Boulogne, Clichy, Levallois, Vincennes, Montreuil, etc.). L'app doit être très précise, surpassant les outils existants (PriceHubble, MeilleursAgents), en exploitant les données publiques DVF. Elle fournit des valorisations transparentes et justifiables via un waterfall chart, des comparables sur carte, des explications d'hypothèses, et un simulateur de coût total.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + Recharts + Leaflet + leaflet.heat
- **Backend**: FastAPI + MongoDB + ReportLab (PDF)
- **Intégrations**: DVF Cerema API, Géorisques API, Gemini 2.5 Flash (emergentintegrations)

## Couverture Géographique
- Paris intramuros (75001-75020)
- Hauts-de-Seine (92) — 26 communes
- Seine-Saint-Denis (93) — 14 communes
- Val-de-Marne (94) — 16 communes
- Total : ~70 codes postaux avec prix moyens DVF

## Modèle de Valorisation — RÈGLES CRITIQUES

### RÉSOLUTION SPATIALE (RÈGLE ABSOLUE)
Le modèle ne doit JAMAIS utiliser un prix moyen de zone comme point de départ.
Le point de départ est TOUJOURS les transactions DVF réelles pondérées.

### FRAÎCHEUR DES DONNÉES (RÈGLE ABSOLUE)
- Max 24 mois. Jamais au-delà.
- Pondération : 3 mois=1.0, 12 mois=0.7, 24 mois=0.4, >24 mois=exclusion
- anneemut_min=2024 dans l'appel API Cerema

### FILTRAGE DES ANOMALIES (NETTOYAGE OBLIGATOIRE)
- Prix/m² < 5 000 € ou > 20 000 € exclus (25 000 pour zones premium)
- Surface < 20 m² exclue (chambres de service)
- Surface > 200% ou < 50% de la surface cible exclue
- Doublons parcelle/date/prix exclus (lots en bloc, VEFA)
- Outliers > 2σ de la médiane exclus

### HIÉRARCHIE DES CERCLES CONCENTRIQUES
- C1 — Même rue (poids x3)
- C2 — Même type de rue dans 200m (poids x1.5)
- C3 — Rayon élargi 300-500m (poids x1)

### FIABILITÉ
- HAUTE : >= 8 comparables C1
- MOYENNE : >= 5 comparables C1+C2
- BASSE : sinon

### RÈGLE DU VERDICT
- Écart < 10% → "PRIX JUSTE / DANS LE MARCHÉ"
- 10-20% au-dessus → "SURÉVALUÉ"
- > 20% au-dessus → "TRÈS SURÉVALUÉ"
- > 15% en-dessous → "SOUS-ÉVALUÉ" + warning automatique

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

### Résolution Spatiale Fine (Done)
- Recherche DVF progressive 200m→300m→500m
- Médiane pondérée distance + fraîcheur + similarité surface
- Micro-score de localisation
- Carte de chaleur (heatmap) + cercle de rayon

### Filtrage Strict DVF (Done)
- 24 mois max (pondération dégressive 3mo=1.0 → 24mo=0.4)
- Filtrage anomalies (prix, surface, doublons, outliers 2σ)
- Segmentation par surface (±30%=1.0, ±50%=0.5, au-delà=exclusion)
- Score de pertinence 0-100 pour chaque comparable
- Raisons d'exclusion transparentes
- Cross-calibration warning

### Exclusion Manuelle + Recalcul Temps Réel (Done)
- Clic sur une ligne pour exclure un comparable
- Endpoint POST /api/valuation/recalculate
- Nouveau prix recalculé instantanément

### Cercles Concentriques + Fiabilité + Coefficient de Rue (Done)
- Classification C1/C2/C3 avec poids différenciés
- Indicateur de fiabilité (HAUTE/MOYENNE/BASSE)
- Coefficient de rue (médiane même rue / médiane zone)
- Badges visuels sur la carte et le tableau

### Listing Analyzer (Done)
- Upload fiches d'agence (PDF/images) + extraction IA (Gemini 2.5 Flash)
- Géocodage adresse → DVF local
- Analyse IA avec règle du verdict ±10%
- Export PDF de l'analyse

### PDF Report Generation (Done)
- Rapport estimation : 4 pages
- Rapport analyse listing

### Extension Petite Couronne (Done — 09/04/2026)
- ZONE_AVG_PRICES : ~70 codes postaux (75 + 92 + 93 + 94)
- Recherche d'adresses étendue : plus de filtre "Paris only"
- Labels dynamiques : "XXe arrondissement" pour Paris, nom de commune pour banlieue
- `is_paris` et `zone_label` dans les réponses API
- Formulaire mis à jour : "Arrondissement / Ville", placeholder inclusif
- Frontend adapté : HypothesesPanel, MarketPosition, ListingAnalyzer
- Zones premium étendues (Neuilly, Saint-Mandé)
- Tests : 100% backend + frontend (iteration_6)

## Backlog

### P1
- Entraîner un modèle XGBoost/LightGBM sur l'ensemble DVF Paris+PC pour gradients infra-quartier
- Micro-score de rue (bruit, ensoleillement, largeur, commerces)

### P2
- Mode comparaison (jusqu'à 3 biens côte à côte)
- Compléter le Simulateur (détail frais notaire, courtier, assurance)

### P3
- Cache DVF Cerema pour pallier les erreurs 503
- Résidu de prestige par voie
- Intégration API SeLoger/LeBonCoin pour calibration croisée automatique
- Refactoring backend : découper server.py (>2300 lignes) en modules
