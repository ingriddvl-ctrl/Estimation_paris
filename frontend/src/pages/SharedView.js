import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, BarChart3, MapPin, TrendingUp, Shield } from "lucide-react";
import WaterfallChart from "@/components/WaterfallChart";
import ComparablesMap from "@/components/ComparablesMap";
import LocationScores from "@/components/LocationScores";
import RiskPanel from "@/components/RiskPanel";

function formatPrice(n) {
  if (!n) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);
}

export default function SharedView() {
  const { shareId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSharedValuation(shareId).then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [shareId]);

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-zinc-400" /></div>;
  if (!data) return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4" data-testid="shared-not-found">
      <p className="text-zinc-500">Estimation introuvable ou lien expiré</p>
      <Link to="/" className="text-sm underline">Retour à l'accueil</Link>
    </div>
  );

  const loc = data.request?.location || {};
  const chars = data.request?.characteristics || {};

  return (
    <div className="min-h-screen bg-white" data-testid="shared-view-page">
      <header className="border-b border-zinc-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-black flex items-center justify-center"><span className="text-white font-heading font-bold text-sm">V</span></div>
            <span className="font-heading font-bold text-lg tracking-tight">VALORISATEUR</span>
          </div>
          <span className="text-xs font-mono text-zinc-400 bg-zinc-100 px-3 py-1">LECTURE SEULE</span>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Estimation partagée</p>
        <h1 className="font-heading font-bold text-xl sm:text-2xl tracking-tight mb-6" data-testid="shared-address">{loc.address || "Adresse"}</h1>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-px bg-zinc-200 mb-8">
          <div className="bg-white p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Prix estimé</p>
            <p className="font-heading font-bold text-3xl tracking-tight" data-testid="shared-price">{formatPrice(data.price_median)}</p>
          </div>
          <div className="bg-white p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Prix / m²</p>
            <p className="font-heading font-bold text-3xl tracking-tight">{formatPrice(data.price_per_sqm_median)}</p>
          </div>
          <div className="bg-white p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Confiance</p>
            <p className="font-heading font-bold text-3xl tracking-tight">{data.confidence_score}<span className="text-lg text-zinc-400">/100</span></p>
          </div>
          <div className="bg-white p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Surface</p>
            <p className="font-heading font-bold text-3xl tracking-tight">{chars.surface_carrez}<span className="text-lg text-zinc-400"> m²</span></p>
          </div>
        </div>

        <Tabs defaultValue="estimation" data-testid="shared-tabs">
          <TabsList className="bg-zinc-100 rounded-none p-0 h-10">
            <TabsTrigger value="estimation" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-5"><BarChart3 className="w-3.5 h-3.5 mr-1.5" /> Estimation</TabsTrigger>
            <TabsTrigger value="comparables" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-5"><MapPin className="w-3.5 h-3.5 mr-1.5" /> Comparables</TabsTrigger>
            <TabsTrigger value="localisation" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-5"><TrendingUp className="w-3.5 h-3.5 mr-1.5" /> Localisation</TabsTrigger>
            <TabsTrigger value="risques" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-5"><Shield className="w-3.5 h-3.5 mr-1.5" /> Risques</TabsTrigger>
          </TabsList>
          <TabsContent value="estimation" className="mt-6">
            <WaterfallChart adjustments={data.adjustments || []} basePrice={data.market_data?.base_price_sqm || 0} finalPrice={data.price_per_sqm_median || 0} />
          </TabsContent>
          <TabsContent value="comparables" className="mt-6">
            <ComparablesMap comparables={data.comparables || []} center={[loc.latitude || 48.8566, loc.longitude || 2.3522]} estimatedPrice={data.price_per_sqm_median || 0} />
          </TabsContent>
          <TabsContent value="localisation" className="mt-6">
            <LocationScores scores={data.location_scores || {}} />
          </TabsContent>
          <TabsContent value="risques" className="mt-6">
            <RiskPanel risks={data.risks || []} dpe={data.request?.condition?.dpe} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
