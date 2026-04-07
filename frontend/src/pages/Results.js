import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { ArrowLeft, Calculator, Share2, Copy, MapPin, TrendingUp, Shield, BarChart3, Loader2, Lightbulb } from "lucide-react";
import WaterfallChart from "@/components/WaterfallChart";
import ComparablesMap from "@/components/ComparablesMap";
import LocationScores from "@/components/LocationScores";
import RiskPanel from "@/components/RiskPanel";
import HypothesesPanel from "@/components/HypothesesPanel";

function formatPrice(n) {
  if (!n) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);
}

export default function Results() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getValuation(id).then(setData).catch(() => toast.error("Estimation introuvable")).finally(() => setLoading(false));
  }, [id]);

  const copyShareLink = () => {
    if (!data) return;
    const url = `${window.location.origin}/share/${data.share_id}`;
    navigator.clipboard.writeText(url);
    toast.success("Lien copié !");
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" data-testid="results-loading">
      <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
    </div>
  );

  if (!data) return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4" data-testid="results-not-found">
      <p className="text-zinc-500">Estimation introuvable</p>
      <Link to="/" className="text-sm underline">Retour à l'accueil</Link>
    </div>
  );

  const req = data.request || {};
  const loc = req.location || {};
  const chars = req.characteristics || {};

  return (
    <div className="min-h-screen bg-white" data-testid="results-page">
      {/* Header */}
      <header className="border-b border-zinc-200 sticky top-0 bg-white/80 backdrop-blur-xl z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3" data-testid="results-nav-home">
            <div className="w-8 h-8 bg-black flex items-center justify-center">
              <span className="text-white font-heading font-bold text-sm">V</span>
            </div>
            <span className="font-heading font-bold text-lg tracking-tight">VALORISATEUR</span>
          </Link>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={copyShareLink} className="rounded-none text-xs" data-testid="share-btn">
              <Share2 className="w-3.5 h-3.5 mr-1.5" /> Partager
            </Button>
            <Button size="sm" onClick={() => navigate(`/simulator/${id}`)} className="rounded-none bg-black text-white hover:bg-zinc-800 text-xs" data-testid="simulator-btn">
              <Calculator className="w-3.5 h-3.5 mr-1.5" /> Simuler l'achat
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Back + address */}
        <div className="flex items-center gap-3 mb-6">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="rounded-none" data-testid="back-btn">
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono">Estimation</p>
            <h1 className="font-heading font-bold text-xl sm:text-2xl tracking-tight" data-testid="result-address">{loc.address || "Adresse inconnue"}</h1>
          </div>
        </div>

        {/* Price summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-px bg-zinc-200 mb-8 animate-fade-in-up" data-testid="price-summary">
          <div className="bg-white p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Prix estimé</p>
            <p className="font-heading font-bold text-3xl tracking-tight" data-testid="price-median">{formatPrice(data.price_median)}</p>
            <p className="text-xs text-zinc-400 mt-1 font-mono">{formatPrice(data.price_low)} — {formatPrice(data.price_high)}</p>
          </div>
          <div className="bg-white p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Prix / m²</p>
            <p className="font-heading font-bold text-3xl tracking-tight" data-testid="price-per-sqm">{formatPrice(data.price_per_sqm_median)}</p>
            <p className="text-xs text-zinc-400 mt-1 font-mono">{chars.surface_carrez} m² Carrez</p>
          </div>
          <div className="bg-white p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Confiance</p>
            <p className="font-heading font-bold text-3xl tracking-tight" data-testid="confidence-score">{data.confidence_score}<span className="text-lg text-zinc-400">/100</span></p>
            <div className="w-full bg-zinc-100 h-1.5 mt-3">
              <div className="bg-black h-1.5 confidence-fill" style={{ width: `${data.confidence_score}%` }} />
            </div>
          </div>
          <div className="bg-white p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Comparables</p>
            <p className="font-heading font-bold text-3xl tracking-tight" data-testid="comparables-count">{data.comparables?.length || 0}</p>
            <p className="text-xs text-zinc-400 mt-1 font-mono">transactions DVF proches</p>
          </div>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="hypotheses" className="animate-fade-in-up stagger-2" data-testid="results-tabs">
          <TabsList className="bg-zinc-100 rounded-none p-0 h-10">
            <TabsTrigger value="hypotheses" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-5" data-testid="tab-hypotheses">
              <Lightbulb className="w-3.5 h-3.5 mr-1.5" /> Hypothèses
            </TabsTrigger>
            <TabsTrigger value="estimation" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-5" data-testid="tab-estimation">
              <BarChart3 className="w-3.5 h-3.5 mr-1.5" /> Estimation
            </TabsTrigger>
            <TabsTrigger value="comparables" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-5" data-testid="tab-comparables">
              <MapPin className="w-3.5 h-3.5 mr-1.5" /> Comparables
            </TabsTrigger>
            <TabsTrigger value="localisation" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-5" data-testid="tab-localisation">
              <TrendingUp className="w-3.5 h-3.5 mr-1.5" /> Localisation
            </TabsTrigger>
            <TabsTrigger value="risques" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-5" data-testid="tab-risques">
              <Shield className="w-3.5 h-3.5 mr-1.5" /> Risques
            </TabsTrigger>
          </TabsList>

          <TabsContent value="hypotheses" className="mt-6" data-testid="tab-content-hypotheses">
            <HypothesesPanel adjustments={data.adjustments || []} marketData={data.market_data || {}} />
          </TabsContent>

          <TabsContent value="estimation" className="mt-6" data-testid="tab-content-estimation">
            <WaterfallChart adjustments={data.adjustments || []} basePrice={data.market_data?.base_price_sqm || 0} finalPrice={data.price_per_sqm_median || 0} />
          </TabsContent>

          <TabsContent value="comparables" className="mt-6" data-testid="tab-content-comparables">
            <ComparablesMap comparables={data.comparables || []} center={[loc.latitude || 48.8566, loc.longitude || 2.3522]} estimatedPrice={data.price_per_sqm_median || 0} />
          </TabsContent>

          <TabsContent value="localisation" className="mt-6" data-testid="tab-content-localisation">
            <LocationScores scores={data.location_scores || {}} />
          </TabsContent>

          <TabsContent value="risques" className="mt-6" data-testid="tab-content-risques">
            <RiskPanel risks={data.risks || []} dpe={data.request?.condition?.dpe} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
