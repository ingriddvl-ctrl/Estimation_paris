import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { MapPin, BarChart3, Shield, Calculator, Clock, Share2, FileSearch } from "lucide-react";

const features = [
  { icon: MapPin, title: "Données DVF réelles", desc: "Transactions vérifiées des 5 dernières années dans votre rue" },
  { icon: BarChart3, title: "Décomposition transparente", desc: "Chaque euro de surcote ou décote est justifié et explicable" },
  { icon: Shield, title: "Analyse de risques", desc: "DPE, risques naturels, copropriété, urbanisme — tout est vérifié" },
  { icon: Calculator, title: "Simulateur d'achat", desc: "Frais de notaire, crédit, assurance — le coût réel total" },
  { icon: Clock, title: "Historique", desc: "Sauvegardez et comparez vos estimations dans le temps" },
  { icon: Share2, title: "Partage", desc: "Lien partageable en lecture seule pour votre banquier ou notaire" },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white" data-testid="landing-page">
      {/* Header */}
      <header className="border-b border-zinc-200" data-testid="main-header">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-black flex items-center justify-center">
              <span className="text-white font-heading font-bold text-sm">V</span>
            </div>
            <span className="font-heading font-bold text-lg tracking-tight">VALORISATEUR</span>
          </div>
          <nav className="flex items-center gap-6">
            <Link to="/analyze" className="text-sm text-zinc-500 hover:text-black transition-colors" data-testid="nav-analyze">
              Analyser une fiche
            </Link>
            <Link to="/history" className="text-sm text-zinc-500 hover:text-black transition-colors" data-testid="nav-history">
              Historique
            </Link>
            <Link to="/settings" className="text-sm text-zinc-500 hover:text-black transition-colors" data-testid="nav-settings">
              Paramètres
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-20 pb-16">
        <div className="max-w-3xl">
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-6 animate-fade-in-up" data-testid="hero-overline">
            Valorisation immobilière — Paris
          </p>
          <h1 className="font-heading font-bold text-4xl sm:text-5xl lg:text-6xl tracking-tight leading-none mb-6 animate-fade-in-up stagger-1" data-testid="hero-title">
            Estimez au plus juste,
            <br />
            <span className="text-zinc-400">donnée par donnée.</span>
          </h1>
          <p className="text-base sm:text-lg text-zinc-500 leading-relaxed mb-10 max-w-xl animate-fade-in-up stagger-2" data-testid="hero-subtitle">
            Connecté aux bases publiques DVF, cadastre et INSEE. Chaque critère est pondéré, chaque ajustement est transparent et modifiable.
          </p>
          <div className="flex items-center gap-4 flex-wrap animate-fade-in-up stagger-3">
            <Button
              onClick={() => navigate("/new")}
              className="h-12 px-8 bg-black text-white hover:bg-zinc-800 rounded-none font-heading font-medium text-sm tracking-wide"
              data-testid="start-valuation-btn"
            >
              Nouvelle estimation
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate("/analyze")}
              className="h-12 px-8 rounded-none border-zinc-300 hover:bg-zinc-50 font-heading font-medium text-sm tracking-wide"
              data-testid="analyze-listing-btn"
            >
              <FileSearch className="w-4 h-4 mr-2" /> Analyser une fiche agence
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate("/history")}
              className="h-12 px-8 rounded-none border-zinc-300 hover:bg-zinc-50 font-heading font-medium text-sm tracking-wide"
              data-testid="view-history-btn"
            >
              Voir l'historique
            </Button>
          </div>
        </div>
      </section>

      {/* Features grid */}
      <section className="max-w-7xl mx-auto px-6 pb-20">
        <div className="border-t border-zinc-200 pt-16">
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-8">Fonctionnalités</p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-zinc-200">
            {features.map((f, i) => (
              <div
                key={f.title}
                className={`bg-white p-8 hover-lift animate-fade-in-up stagger-${i + 1}`}
                data-testid={`feature-${i}`}
              >
                <f.icon className="w-5 h-5 text-zinc-400 mb-4" strokeWidth={1.5} />
                <h3 className="font-heading font-bold text-base mb-2">{f.title}</h3>
                <p className="text-sm text-zinc-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-200 py-6">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between text-xs text-zinc-400">
          <span>Valorisateur Paris — Données publiques DVF, INSEE, ADEME</span>
          <span className="font-mono">v1.0</span>
        </div>
      </footer>
    </div>
  );
}
