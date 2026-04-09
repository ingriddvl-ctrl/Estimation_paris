# VALORISATEUR PARIS — PRD

## Problème Original
Application web complète pour estimer le prix d'achat d'appartements à Paris (intramuros + petite couronne). L'app doit être très précise, surpassant les outils existants (PriceHubble, MeilleursAgents), en exploitant les données publiques et privées. Elle fournit des valorisations transparentes et justifiables via un waterfall chart, des comparables sur carte, des explications d'hypothèses, et un simulateur de coût total.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + Recharts + Leaflet + leaflet.heat
- **Backend**: FastAPI + MongoDB + ReportLab (PDF)
- **Intégrations**: DVF Cerema API, Géorisques API, Gemini 2.5 Flash (emergentintegrations)

## Modèle de Valorisation — RÉSOLUTION SPATIALE (RÈGLE ABSOLUE)
Le modèle ne doit JAMAIS utiliser un prix moyen d'arrondissement comme point de départ.
Le point de départ est TOUJOURS les transactions DVF réelles pondérées par:
- **Distance** : 1/(1+d/200) — les transactions proches pèsent plus
- **Fraîcheur** : les transactions récentes pèsent plus (2025=0.95, 2024=0.85, etc.)
- **Rayon progressif** : 200m → 300m → 500m → 800m (élargir uniquement si < 10 comparables)
- **Micro-score** : calcul automatique du premium/décote de micro-localisation vs arrondissement

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
- Recherche DVF progressive 200m→300m→500m→800m
- Médiane pondérée distance + fraîcheur (jamais de moyenne arrondissement comme base)
- Micro-score de localisation (premium vs arrondissement, densité 300m, homogénéité prix)
- Carte de chaleur (heatmap) sur la carte des comparables
- Cercle de rayon de recherche affiché sur la carte
- Distance (en mètres) affichée pour chaque comparable

### Listing Analyzer (Done - 09/04/2026)
- Upload de fiches d'agence (PDF/images)
- Extraction automatique via Gemini 2.5 Flash
- Géocodage de l'adresse extraite → recherche DVF locale (pas la moyenne arrondissement)
- Analyse IA avec données DVF locales comme référence
- Affichage des comparables DVF dans l'analyse
- Export PDF de l'analyse
- Sauvegarde en MongoDB pour réutilisation

### PDF Report Generation (Done - 09/04/2026)
- Rapport estimation : 4 pages (couverture, décomposition, comparables, méthodologie)
- Rapport analyse listing : verdict, arguments, comparables DVF, caractéristiques extraites
- Endpoints: GET /api/report/pdf/{id} et GET /api/listing/report/pdf/{id}

## Backlog

### P2
- Mode comparaison (jusqu'à 3 biens côte à côte)
- Compléter le Simulateur (détail frais notaire, courtier, assurance)
- Entraîner un modèle XGBoost/LightGBM sur l'ensemble DVF Paris pour gradients infra-quartier

### P3
- Cache DVF Cerema pour pallier les erreurs 503
- Micro-score de rue (bruit, ensoleillement, largeur, commerces)
- Résidu de prestige par voie

## Contraintes
- Estimations conservatrices (plafonnement max_cumulative_pct à 18%)
- Langue: Français uniquement
- Toutes les API préfixées /api
- Base prix = TOUJOURS médiane pondérée DVF locale, JAMAIS moyenne arrondissement
