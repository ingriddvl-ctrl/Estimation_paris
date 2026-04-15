import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { ArrowLeft, Calculator, Share2, MapPin, TrendingUp, Shield, BarChart3, Loader2, Lightbulb, ShoppingBag, FileText, Brain, Download, RefreshCw, Settings, Save } from "lucide-react";
import WaterfallChart from "@/components/WaterfallChart";
import ComparablesMap from "@/components/ComparablesMap";
import LocationScores from "@/components/LocationScores";
import RiskPanel from "@/components/RiskPanel";
import HypothesesPanel from "@/components/HypothesesPanel";
import MarketPosition from "@/components/MarketPosition";
import MarketListings from "@/components/MarketListings";
import DocumentUpload from "@/components/DocumentUpload";
import ExpertInsights from "@/components/ExpertInsights";

function formatPrice(n) {
  if (!n) return "\u2014";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);
}

const CONFIG_FIELDS = {
  floor_rdc: { label: "RDC", unit: "%", group: "\u00c9tage" },
  floor_1st: { label: "1er \u00e9tage", unit: "%", group: "\u00c9tage" },
  floor_last_with_elevator: { label: "Dernier \u00e9tage + ascenseur", unit: "%", group: "\u00c9tage" },
  floor_per_level_elevator: { label: "Par \u00e9tage au-del\u00e0 du 3e", unit: "%", group: "\u00c9tage" },
  floor_6_plus_no_elevator: { label: "6e+ sans ascenseur", unit: "%", group: "\u00c9tage" },
  south_traversant: { label: "Sud / traversant", unit: "%", group: "Exposition" },
  north_mono: { label: "Nord mono", unit: "%", group: "Exposition" },
  vis_a_vis_close: { label: "Vis-\u00e0-vis < 10m", unit: "%", group: "Vue" },
  view_monument: { label: "Vue monument", unit: "%", group: "Vue" },
  view_rooftops: { label: "Vue toits", unit: "%", group: "Vue" },
  view_garden: { label: "Vue jardin/parc", unit: "%", group: "Vue" },
  balcony_pct: { label: "Balcon", unit: "%", group: "Ext\u00e9rieur" },
  terrace_pct: { label: "Terrasse", unit: "%", group: "Ext\u00e9rieur" },
  garden_pct: { label: "Jardin", unit: "%", group: "Ext\u00e9rieur" },
  dpe_ab: { label: "DPE A-B", unit: "%", group: "DPE" },
  dpe_cd: { label: "DPE C-D", unit: "%", group: "DPE" },
  dpe_e: { label: "DPE E", unit: "%", group: "DPE" },
  dpe_f: { label: "DPE F", unit: "%", group: "DPE" },
  dpe_g: { label: "DPE G", unit: "%", group: "DPE" },
  haussmann_bonus: { label: "Pierre de taille", unit: "%", group: "Immeuble" },
  concierge_bonus: { label: "Gardien", unit: "%", group: "Immeuble" },
  ceiling_high: { label: "HSP > 2,80m", unit: "%", group: "Volumes" },
  ceiling_low: { label: "HSP < 2,50m", unit: "%", group: "Volumes" },
  parking_central: { label: "Parking central", unit: "\u20ac", group: "Parking" },
  parking_intermediate: { label: "Parking interm\u00e9diaire", unit: "\u20ac", group: "Parking" },
  parking_peripheral: { label: "Parking p\u00e9riph\u00e9rique", unit: "\u20ac", group: "Parking" },
  state_to_renovate: { label: "\u00c0 r\u00e9nover (co\u00fbt/m\u00b2)", unit: "\u20ac/m\u00b2", group: "\u00c9tat" },
  state_new: { label: "Refait \u00e0 neuf", unit: "%", group: "\u00c9tat" },
  state_luxury: { label: "Luxe", unit: "%", group: "\u00c9tat" },
  sold_occupied_discount: { label: "Vendu occup\u00e9", unit: "%", group: "Juridique" },
  max_cumulative_pct: { label: "Plafond ajustements", unit: "%", group: "Plafonnement" },
};

function ConfigPanel({ valuationId, onRecalculate }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getAlgorithmConfig().then(setConfig).catch(() => toast.error("Erreur chargement config")).finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateAlgorithmConfig(config);
      toast.success("Coefficients sauvegard\u00e9s ! Relancez l'estimation pour voir l'impact.");
    } catch {
      toast.error("Erreur de sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  if (loading || !config) return <div className="flex items-center justify-center py-12"><Loader2 className="w-5 h-5 animate-spin text-zinc-400" /></div>;

  const groups = {};
  Object.entries(CONFIG_FIELDS).forEach(([key, meta]) => {
    if (!groups[meta.group]) groups[meta.group] = [];
    groups[meta.group].push({ key, ...meta });
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-zinc-400 font-mono">Param\u00e8tres du mod\u00e8le</p>
          <p className="text-sm text-zinc-500 mt-1">Modifiez les coefficients puis relancez l'estimation pour voir l'impact.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={handleSave} disabled={saving} className="rounded-none text-xs">
            <Save className="w-3.5 h-3.5 mr-1.5" /> {saving ? "Sauvegarde..." : "Enregistrer"}
          </Button>
          {onRecalculate && (
            <Button size="sm" onClick={onRecalculate} className="rounded-none bg-blue-600 text-white hover:bg-blue-700 text-xs">
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Relancer l'estimation
            </Button>
          )}
        </div>
      </div>

      {Object.entries(groups).map(([groupName, fields]) => (
        <div key={groupName} className="border border-zinc-200">
          <div className="px-4 py-2.5 bg-zinc-50 border-b border-zinc-200">
            <p className="text-xs uppercase tracking-widest text-zinc-500 font-mono font-medium">{groupName}</p>
          </div>
          <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {fields.map(({ key, label, unit }) => (
              <div key={key}>
                <Label className="text-[11px] text-zinc-500 mb-1 block">{label}</Label>
                <div className="flex items-center gap-1.5">
                  <Input
                    type="number"
                    step={unit === "\u20ac" || unit === "\u20ac/m\u00b2" ? 100 : 0.5}
                    value={config[key] ?? 0}
                    onChange={(e) => setConfig(prev => ({ ...prev, [key]: parseFloat(e.target.value) || 0 }))}
                    className="rounded-none h-8 font-mono text-xs"
                  />
                  <span className="text-[10px] text-zinc-400 font-mono w-8 shrink-0">{unit}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      <div className="bg-amber-50 border border-amber-200 p-4">
        <p className="text-xs text-amber-800">
          <strong>Note :</strong> Ces coefficients s'appliquent globalement \u00e0 toutes les estimations. Apr\u00e8s modification, cliquez sur "Relancer l'estimation" pour recalculer avec les nouveaux param\u00e8tres.
        </p>
      </div>
    </div>
  );
}

export default function Results() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [recalculating, setRecalculating] = useState(false);

  useEffect(() => {
    api.getValuation(id).then(setData).catch(() => toast.error("Estimation introuvable")).finally(() => setLoading(false));
  }, [id]);

  const copyShareLink = () => {
    if (!data) return;
    const url = `${window.location.origin}/share/${data.share_id}`;
    navigator.clipboard.writeText(url);
    toast.success("Lien copi\u00e9 !");
  };

  const handleDownloadPdf = async () => {
    setPdfLoading(true);
    try {
      await api.downloadPdfReport(id);
      toast.success("Rapport PDF t\u00e9l\u00e9charg\u00e9 !");
    } catch {
      toast.error("Erreur lors de la g\u00e9n\u00e9ration du PDF");
    } finally {
      setPdfLoading(false);
    }
  };

  const handleRecalculate = async () => {
    if (!data?.request) return;
    setRecalculating(true);
    try {
      toast.info("Recalcul en cours...");
      const result = await api.estimateValuation(data.request);
      await api.saveValuation(result);
      toast.success("Estimation recalcul\u00e9e !");
      navigate(`/results/${result.id}`);
      window.location.reload();
    } catch (err) {
      toast.error("Erreur lors du recalcul");
      console.error(err);
    } finally {
      setRecalculating(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" data-testid="results-loading">
      <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
    </div>
  );

  if (!data) return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4" data-testid="results-not-found">
      <p className="text-zinc-500">Estimation introuvable</p>
      <Link to="/" className="text-sm underline">Retour \u00e0 l'accueil</Link>
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
            <div className="w-8 h-8 bg-blue-600 rounded-xl flex items-center justify-center shadow-sm shadow-blue-600/20">
              <span className="text-white font-bold text-sm">V</span>
            </div>
            <span className="font-extrabold text-lg tracking-tight text-zinc-900">Ingrid</span><span className="font-bold text-lg text-blue-600 ml-1">Immo</span>
          </Link>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleRecalculate} disabled={recalculating} className="rounded-none text-xs">
              {recalculating ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5 mr-1.5" />}
              Relancer
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownloadPdf} disabled={pdfLoading} className="rounded-none text-xs" data-testid="download-pdf-btn">
              {pdfLoading ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Download className="w-3.5 h-3.5 mr-1.5" />} PDF
            </Button>
            <Button variant="outline" size="sm" onClick={copyShareLink} className="rounded-none text-xs" data-testid="share-btn">
              <Share2 className="w-3.5 h-3.5 mr-1.5" /> Partager
            </Button>
            <Button size="sm" onClick={() => navigate(`/simulator/${id}`)} className="rounded-none bg-black text-white hover:bg-zinc-800 text-xs" data-testid="simulator-btn">
              <Calculator className="w-3.5 h-3.5 mr-1.5" /> Simuler
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
        <div className="grid grid-cols-1 md:grid-cols-5 gap-px bg-zinc-200 mb-8 animate-fade-in-up" data-testid="price-summary">
          <div className="bg-white p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Prix estim\u00e9</p>
            <p className="font-heading font-bold text-3xl tracking-tight" data-testid="price-median">{formatPrice(data.price_median)}</p>
            <p className="text-xs text-zinc-400 mt-1 font-mono">{formatPrice(data.price_low)} \u2014 {formatPrice(data.price_high)}</p>
          </div>
          <div className="bg-white p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Prix / m\u00b2</p>
            <p className="font-heading font-bold text-3xl tracking-tight" data-testid="price-per-sqm">{formatPrice(data.price_per_sqm_median)}</p>
            <p className="text-xs text-zinc-400 mt-1 font-mono">{chars.surface_carrez} m\u00b2 Carrez</p>
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
          {data.market_data?.market_position && (
            <div className="bg-white p-6">
              <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Position march\u00e9</p>
              <p className="font-heading font-bold text-3xl tracking-tight" data-testid="market-position-badge" style={{
                color: data.market_data.market_position.diff_pct > 5 ? "#008A00" : data.market_data.market_position.diff_pct < -5 ? "#E60000" : "#18181B"
              }}>
                {data.market_data.market_position.label}
              </p>
              <p className="text-xs text-zinc-400 mt-1 font-mono">
                {data.market_data.market_position.diff_pct > 0 ? "+" : ""}{data.market_data.market_position.diff_pct}% vs {data.market_data?.zone_label || "zone"}
              </p>
            </div>
          )}
        </div>

        {/* Tabs */}
        <Tabs defaultValue="hypotheses" className="animate-fade-in-up stagger-2" data-testid="results-tabs">
          <TabsList className="bg-zinc-100 rounded-none p-0 h-10 flex-wrap">
            <TabsTrigger value="hypotheses" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-4" data-testid="tab-hypotheses">
              <Lightbulb className="w-3.5 h-3.5 mr-1.5" /> Hypoth\u00e8ses
            </TabsTrigger>
            <TabsTrigger value="marche" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-4" data-testid="tab-marche">
              <ShoppingBag className="w-3.5 h-3.5 mr-1.5" /> March\u00e9
            </TabsTrigger>
            <TabsTrigger value="expert" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-4" data-testid="tab-expert">
              <Brain className="w-3.5 h-3.5 mr-1.5" /> Expert
            </TabsTrigger>
            <TabsTrigger value="estimation" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-4" data-testid="tab-estimation">
              <BarChart3 className="w-3.5 h-3.5 mr-1.5" /> Estimation
            </TabsTrigger>
            <TabsTrigger value="comparables" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-4" data-testid="tab-comparables">
              <MapPin className="w-3.5 h-3.5 mr-1.5" /> Comparables
            </TabsTrigger>
            <TabsTrigger value="risques" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-4" data-testid="tab-risques">
              <Shield className="w-3.5 h-3.5 mr-1.5" /> Risques & Projections
            </TabsTrigger>
            <TabsTrigger value="parametres" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-4" data-testid="tab-parametres">
              <Settings className="w-3.5 h-3.5 mr-1.5" /> Param\u00e8tres
            </TabsTrigger>
            <TabsTrigger value="documents" className="rounded-none text-xs data-[state=active]:bg-black data-[state=active]:text-white h-10 px-4" data-testid="tab-documents">
              <FileText className="w-3.5 h-3.5 mr-1.5" /> Documents
            </TabsTrigger>
          </TabsList>

          <TabsContent value="hypotheses" className="mt-6" data-testid="tab-content-hypotheses">
            <HypothesesPanel adjustments={data.adjustments || []} marketData={data.market_data || {}} />
          </TabsContent>

          <TabsContent value="marche" className="mt-6" data-testid="tab-content-marche">
            <MarketPosition position={data.market_data?.market_position} surface={chars.surface_carrez} totalPrice={data.price_median} marketData={data.market_data} />
            <div className="mt-8">
              <MarketListings lat={loc.latitude} lon={loc.longitude} estimatedPriceSqm={data.price_per_sqm_median} />
            </div>
          </TabsContent>

          <TabsContent value="expert" className="mt-6" data-testid="tab-content-expert">
            <ExpertInsights data={data} />
          </TabsContent>

          <TabsContent value="estimation" className="mt-6" data-testid="tab-content-estimation">
            <WaterfallChart adjustments={data.adjustments || []} basePrice={data.market_data?.base_price_sqm || 0} finalPrice={data.price_per_sqm_median || 0} />
          </TabsContent>

          <TabsContent value="comparables" className="mt-6" data-testid="tab-content-comparables">
            <ComparablesMap
              comparables={data.comparables || []}
              excludedComparables={data.excluded_comparables || []}
              center={[loc.latitude || 48.8566, loc.longitude || 2.3522]}
              estimatedPrice={data.price_per_sqm_median || 0}
              searchRadius={data.market_data?.search_radius_m}
              valuationId={id}
              crossCalibrationWarning={data.cross_calibration_warning}
              circleStats={data.circle_stats}
              streetCoefficient={data.street_coefficient}
            />
          </TabsContent>

          <TabsContent value="risques" className="mt-6" data-testid="tab-content-risques">
            <RiskPanel
              risks={data.risks || []}
              dpe={data.request?.condition?.dpe}
              currentPrice={data.price_median}
              surface={chars.surface_carrez}
              charges={data.request?.building?.annual_charges}
              taxeFonciere={data.request?.legal?.property_tax}
            />
          </TabsContent>

          <TabsContent value="parametres" className="mt-6" data-testid="tab-content-parametres">
            <ConfigPanel valuationId={id} onRecalculate={handleRecalculate} />
          </TabsContent>

          <TabsContent value="documents" className="mt-6" data-testid="tab-content-documents">
            <DocumentUpload valuationId={id} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
