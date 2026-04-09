# VALORISATEUR PARIS — PRD

## Problème Original
Application web complète pour estimer le prix d'achat d'appartements à Paris (intramuros + petite couronne). L'app doit être très précise, surpassant les outils existants (PriceHubble, MeilleursAgents), en exploitant les données publiques et privées. Elle fournit des valorisations transparentes et justifiables via un waterfall chart, des comparables sur carte, des explications d'hypothèses, et un simulateur de coût total.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + Recharts + Leaflet
- **Backend**: FastAPI + MongoDB + ReportLab (PDF)
- **Intégrations**: DVF Cerema API, Géorisques API, Gemini 2.5 Flash (emergentintegrations)

## Fonctionnalités Implémentées

### MVP (Done)
- Formulaire multi-étapes (Localisation, Caractéristiques, État, Immeuble, Juridique)
- Moteur d'estimation avec médiane tronquée DVF + ajustements plafonnés
- Dashboard 7 onglets (Hypothèses, Marché, Expert, Estimation, Comparables, Risques, Documents)
- Waterfall chart, carte Leaflet des comparables
- Panel d'hypothèses transparent expliquant chaque ajustement
- Position marché (++, +, =, -, --)
- Sauvegarde/Historique/Partage
- Configuration des coefficients algorithmiques
- Upload de documents (Object Storage)
- Simulateur d'achat (frais notaire, crédit, assurance)

### Listing Analyzer (Done - 09/04/2026)
- Upload de fiches d'agence (PDF/images)
- Extraction automatique via Gemini 2.5 Flash (emergentintegrations)
- Analyse IA du prix demandé avec arguments pour/contre
- Conseils de négociation
- Route /analyze accessible depuis la landing page

### PDF Report Generation (Done - 09/04/2026)
- Génération de rapport PDF professionnel (4 pages) via ReportLab
- Couverture, caractéristiques, décomposition du prix, hypothèses, comparables, risques, méthodologie
- Bouton de téléchargement dans la page Results
- Endpoint: GET /api/report/pdf/{valuation_id}

## Backlog

### P1
- (aucun)

### P2
- Mode comparaison (jusqu'à 3 biens côte à côte)
- Compléter le Simulateur (détail frais notaire, courtier, assurance)

### P3
- Cache DVF Cerema pour pallier les erreurs 503
- Fallback robuste si l'API externe ne répond pas

## Contraintes
- Estimations conservatrices (plafonnement max_cumulative_pct à 18%)
- Langue: Français uniquement
- Toutes les API préfixées /api
