import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { MapPin, BarChart3, Shield, Calculator, Clock, Share2, FileSearch, ArrowRight, Building2 } from "lucide-react";

const features = [
  { icon: MapPin, title: "Données DVF réelles", desc: "Transactions vérifiées des 24 derniers mois dans votre rue, filtrées et pondérées par pertinence" },
  { icon: BarChart3, title: "Décomposition transparente", desc: "Chaque euro de surcote ou décote est justifié — étage, DPE, vue, taille, tendance marché" },
  { icon: Shield, title: "Analyse de risques", desc: "DPE, risques naturels, copropriété, urbanisme — tout est vérifié automatiquement" },
  { icon: Calculator, title: "Simulateur d'achat", desc: "Frais de notaire, crédit, assurance — le coût réel total de votre acquisition" },
  { icon: Clock, title: "Correction marché 2026", desc: "Intègre la tendance baissière post-2022 et les marges de négociation actuelles" },
  { icon: Share2, title: "Rapport PDF pro", desc: "Rapport complet exportable, partageable avec votre banquier ou notaire" },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white" data-testid="landing-page">
      {/* Header */}
      <header className="border-b border-slate-200/60 bg-white/80 backdrop-blur-xl sticky top-0 z-50" data-testid="main-header">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-slate-800 to-slate-600 rounded-lg flex items-center justify-center shadow-sm">
              <Building2 className="w-5 h-5 text-white" strokeWidth={1.5} />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-slate-800">Valorisateur</span>
              <span className="font-medium text-lg tracking-tight text-teal-600 ml-1">Ingrid</span>
            </div>
          </div>
          <nav className="flex items-center gap-6">
            <Link to="/analyze" className="text-sm text-slate-500 hover:text-slate-800 transition-colors" data-testid="nav-analyze">
              Analyser une fiche
            </Link>
            <Link to="/history" className="text-sm text-slate-500 hover:text-slate-800 transition-colors" data-testid="nav-history">
              Historique
            </Link>
            <Link to="/settings" className="text-sm text-slate-500 hover:text-slate-800 transition-colors" data-testid="nav-settings">
              Paramètres
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-20 pb-16">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-teal-50 border border-teal-200/60 rounded-full mb-6 animate-fade-in-up">
            <div className="w-2 h-2 bg-teal-500 rounded-full animate-pulse" />
            <span className="text-xs font-medium text-teal-700">Paris & Petite Couronne — Données DVF en temps réel</span>
          </div>
          <h1 className="font-bold text-4xl sm:text-5xl lg:text-6xl tracking-tight leading-[1.1] mb-6 text-slate-800 animate-fade-in-up stagger-1" data-testid="hero-title">
            Estimez au plus juste,
            <br />
            <span className="bg-gradient-to-r from-teal-600 to-emerald-600 bg-clip-text text-transparent">donnée par donnée.</span>
          </h1>
          <p className="text-base sm:text-lg text-slate-500 leading-relaxed mb-10 max-w-xl animate-fade-in-up stagger-2" data-testid="hero-subtitle">
            L'outil de valorisation le plus transparent du marché. Chaque critère est pondéré, chaque ajustement est justifié et modifiable. Connecté aux bases publiques DVF, cadastre et INSEE.
          </p>
          <div className="flex items-center gap-4 flex-wrap animate-fade-in-up stagger-3">
            <Button
              onClick={() => navigate("/new")}
              className="h-12 px-8 bg-gradient-to-r from-slate-800 to-slate-700 text-white hover:from-slate-700 hover:to-slate-600 rounded-lg font-medium text-sm tracking-wide shadow-lg shadow-slate-200"
              data-testid="start-valuation-btn"
            >
              Nouvelle estimation <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate("/analyze")}
              className="h-12 px-8 rounded-lg border-slate-300 hover:bg-slate-50 font-medium text-sm tracking-wide"
              data-testid="analyze-listing-btn"
            >
              <FileSearch className="w-4 h-4 mr-2" /> Analyser une fiche agence
            </Button>
          </div>
        </div>
      </section>

      {/* Stats bar */}
      <section className="max-w-7xl mx-auto px-6 pb-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { value: "DVF+", label: "Source officielle DGFiP" },
            { value: "24 mois", label: "Transactions récentes" },
            { value: "200m", label: "Rayon de recherche prioritaire" },
            { value: "2026", label: "Correction tendance intégrée" },
          ].map((s) => (
            <div key={s.label} className="bg-white border border-slate-200/60 rounded-lg p-5 text-center">
              <p className="text-2xl font-bold text-slate-800">{s.value}</p>
              <p className="text-xs text-slate-400 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features grid */}
      <section className="max-w-7xl mx-auto px-6 pb-20">
        <div className="border-t border-slate-200/60 pt-16">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400 font-mono mb-2">Fonctionnalités</p>
          <h2 className="text-2xl font-bold text-slate-800 mb-8">Tout ce qu'il faut pour estimer avec précision</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f, i) => (
              <div
                key={f.title}
                className={`bg-white border border-slate-200/60 rounded-lg p-6 hover:border-teal-300 hover:shadow-md transition-all duration-200 animate-fade-in-up stagger-${i + 1}`}
                data-testid={`feature-${i}`}
              >
                <div className="w-10 h-10 bg-teal-50 rounded-lg flex items-center justify-center mb-4">
                  <f.icon className="w-5 h-5 text-teal-600" strokeWidth={1.5} />
                </div>
                <h3 className="font-semibold text-base mb-2 text-slate-800">{f.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200/60 py-8 bg-white">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between text-xs text-slate-400">
          <span>Valorisateur Ingrid — Données publiques DVF, INSEE, ADEME</span>
          <span className="font-mono">2026</span>
        </div>
      </footer>
    </div>
  );
}
