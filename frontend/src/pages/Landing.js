import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { MapPin, BarChart3, Shield, Calculator, Clock, Share2, FileSearch, ArrowRight, Sparkles, TrendingUp, Zap } from "lucide-react";

const features = [
  { icon: MapPin, title: "Données DVF officielles", desc: "Transactions vérifiées des 24 derniers mois autour de votre adresse, filtrées et pondérées." },
  { icon: BarChart3, title: "Transparence totale", desc: "Chaque ajustement est détaillé : étage, DPE, vue, taille, tendance marché. Rien n'est caché." },
  { icon: Shield, title: "Analyse de risques", desc: "DPE, Loi Climat, Géorisques, copropriété — on vérifie tout pour que vous achetiez sereinement." },
  { icon: TrendingUp, title: "Projections 5-12 ans", desc: "3 scénarios de valorisation intégrant les tendances macro et l'impact DPE sur votre bien." },
  { icon: Calculator, title: "Coût réel d'acquisition", desc: "Prix + notaire + rénovation DPE + charges = le vrai budget, sans mauvaise surprise." },
  { icon: Share2, title: "Rapport PDF pro", desc: "Un rapport complet à partager avec votre banquier, notaire ou agent. Classe et convaincant." },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white" data-testid="landing-page">
      {/* Header */}
      <header className="border-b border-zinc-100 sticky top-0 bg-white/90 backdrop-blur-xl z-50" data-testid="main-header">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-600/20">
              <Sparkles className="w-5 h-5 text-white" strokeWidth={2} />
            </div>
            <div className="flex items-baseline gap-1">
              <span className="font-extrabold text-xl tracking-tight text-zinc-900">Ingrid</span>
              <span className="font-bold text-xl tracking-tight text-blue-600">Immo</span>
            </div>
          </div>
          <nav className="flex items-center gap-6">
            <Link to="/analyze" className="text-sm text-zinc-500 hover:text-blue-600 transition-colors" data-testid="nav-analyze">
              Analyser une fiche
            </Link>
            <Link to="/history" className="text-sm text-zinc-500 hover:text-blue-600 transition-colors" data-testid="nav-history">
              Historique
            </Link>
            <Link to="/settings" className="text-sm text-zinc-500 hover:text-blue-600 transition-colors" data-testid="nav-settings">
              Paramètres
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-20 pb-16">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-50 border border-yellow-200 rounded-full mb-8 animate-fade-in-up">
            <Zap className="w-4 h-4 text-yellow-500" />
            <span className="text-sm font-medium text-yellow-700">Paris & Petite Couronne — Connecté aux données DVF en temps réel</span>
          </div>
          <h1 className="font-extrabold text-5xl sm:text-6xl lg:text-7xl tracking-tight leading-[1.05] mb-6 text-zinc-900 animate-fade-in-up stagger-1" data-testid="hero-title">
            Votre bien vaut
            <br />
            <span className="text-blue-600">combien, vraiment ?</span>
          </h1>
          <p className="text-lg text-zinc-500 leading-relaxed mb-10 max-w-xl animate-fade-in-up stagger-2" data-testid="hero-subtitle">
            Fini les estimations opaques. Ingrid Immo vous montre exactement d'où vient chaque euro de votre estimation — données publiques, hypothèses modifiables, zéro boîte noire.
          </p>
          <div className="flex items-center gap-4 flex-wrap animate-fade-in-up stagger-3">
            <Button
              onClick={() => navigate("/new")}
              className="h-13 px-8 bg-blue-600 text-white hover:bg-blue-700 rounded-xl font-semibold text-base shadow-lg shadow-blue-600/25 transition-all hover:shadow-xl hover:shadow-blue-600/30 hover:-translate-y-0.5"
              data-testid="start-valuation-btn"
            >
              Lancer une estimation <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate("/analyze")}
              className="h-13 px-8 rounded-xl border-zinc-200 hover:border-blue-300 hover:bg-blue-50 font-semibold text-base transition-all"
              data-testid="analyze-listing-btn"
            >
              <FileSearch className="w-5 h-5 mr-2" /> Analyser une fiche
            </Button>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="max-w-7xl mx-auto px-6 pb-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { value: "DVF+", label: "Source officielle DGFiP", accent: "text-blue-600" },
            { value: "24 mois", label: "Transactions récentes", accent: "text-blue-600" },
            { value: "200m", label: "Rayon prioritaire", accent: "text-blue-600" },
            { value: "2026", label: "Tendance marché intégrée", accent: "text-yellow-500" },
          ].map((s) => (
            <div key={s.label} className="bg-zinc-50 rounded-xl p-5 text-center hover:bg-blue-50 transition-colors">
              <p className={`text-2xl font-extrabold ${s.accent}`}>{s.value}</p>
              <p className="text-xs text-zinc-400 mt-1 font-medium">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 pb-20">
        <div className="border-t border-zinc-100 pt-16">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-1 bg-yellow-400 rounded-full" />
            <p className="text-sm font-bold text-zinc-400 uppercase tracking-widest">Ce qu'Ingrid Immo fait pour vous</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f, i) => (
              <div
                key={f.title}
                className={`bg-white border border-zinc-100 rounded-xl p-6 hover:border-blue-200 hover:shadow-lg hover:shadow-blue-600/5 transition-all duration-200 hover:-translate-y-0.5 animate-fade-in-up stagger-${i + 1}`}
                data-testid={`feature-${i}`}
              >
                <div className="w-11 h-11 bg-blue-50 rounded-xl flex items-center justify-center mb-4">
                  <f.icon className="w-5 h-5 text-blue-600" strokeWidth={1.5} />
                </div>
                <h3 className="font-bold text-base mb-2 text-zinc-800">{f.title}</h3>
                <p className="text-sm text-zinc-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-6 pb-20">
        <div className="bg-blue-600 rounded-2xl p-10 md:p-14 text-center shadow-xl shadow-blue-600/20">
          <h2 className="text-white font-extrabold text-3xl mb-4">Prêt à estimer votre bien ?</h2>
          <p className="text-blue-200 mb-8 max-w-lg mx-auto">C'est gratuit, transparent, et ça prend 3 minutes. Vos données ne sont pas revendues.</p>
          <Button
            onClick={() => navigate("/new")}
            className="h-13 px-10 bg-yellow-400 text-zinc-900 hover:bg-yellow-300 rounded-xl font-bold text-base shadow-lg transition-all hover:-translate-y-0.5"
          >
            C'est parti ! <ArrowRight className="w-5 h-5 ml-2" />
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-100 py-8">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between text-xs text-zinc-400">
          <span>Ingrid Immo — Données publiques DVF, INSEE, ADEME, Géorisques</span>
          <span className="font-mono">2026</span>
        </div>
      </footer>
    </div>
  );
}
