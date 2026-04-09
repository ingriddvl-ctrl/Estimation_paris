import { useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Upload, Loader2, FileText, ArrowRight, TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle, XCircle, ChevronDown, ChevronUp, Download, MapPin } from "lucide-react";

function formatPrice(n) {
  if (!n) return "—";
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

const OPINION_CONFIG = {
  "sous-évalué": { color: "#008A00", bg: "#f0fdf4", icon: CheckCircle, label: "Sous-évalué" },
  "prix_juste": { color: "#18181B", bg: "#f4f4f5", icon: Minus, label: "Prix juste" },
  "surévalué": { color: "#E60000", bg: "#fef2f2", icon: AlertTriangle, label: "Surévalué" },
  "très_surévalué": { color: "#E60000", bg: "#fef2f2", icon: XCircle, label: "Très surévalué" },
};

function ExtractedField({ label, value, unit }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-zinc-100 last:border-0">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-sm font-mono font-medium">{typeof value === "boolean" ? (value ? "Oui" : "Non") : value}{unit || ""}</span>
    </div>
  );
}

export default function ListingAnalyzer() {
  const navigate = useNavigate();
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [showAllFields, setShowAllFields] = useState(false);
  const [showComps, setShowComps] = useState(false);

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await api.analyzeListing(file);
      setResult(data);
      toast.success("Fiche analysée avec succès !");
    } catch (err) {
      const msg = err?.response?.data?.detail || "Erreur d'analyse. Réessayez.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!result?.analysis_id) return;
    setPdfLoading(true);
    try {
      await api.downloadListingPdf(result.analysis_id);
      toast.success("Rapport PDF téléchargé !");
    } catch {
      toast.error("Erreur lors de la génération du PDF");
    } finally {
      setPdfLoading(false);
    }
  };

  const handleLaunchEstimation = () => {
    if (!result?.extracted) return;
    sessionStorage.setItem("prefill_listing", JSON.stringify(result.extracted));
    navigate("/new?from=listing");
  };

  const ext = result?.extracted || {};
  const analysis = result?.analysis || {};
  const mkt = result?.market_reference || {};
  const micro = mkt.micro_score || {};
  const comps = result?.comparables || [];
  const opConfig = OPINION_CONFIG[analysis.price_opinion] || OPINION_CONFIG["prix_juste"];
  const OpIcon = opConfig?.icon || Minus;

  return (
    <div className="min-h-screen bg-white" data-testid="listing-analyzer-page">
      {/* Header */}
      <header className="border-b border-zinc-200 sticky top-0 bg-white/80 backdrop-blur-xl z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3" data-testid="analyzer-nav-home">
            <div className="w-8 h-8 bg-black flex items-center justify-center">
              <span className="text-white font-heading font-bold text-sm">V</span>
            </div>
            <span className="font-heading font-bold text-lg tracking-tight">VALORISATEUR</span>
          </Link>
          <div className="flex items-center gap-4">
            {result?.analysis_id && (
              <Button variant="outline" size="sm" onClick={handleDownloadPdf} disabled={pdfLoading} className="rounded-none text-xs" data-testid="listing-pdf-btn">
                {pdfLoading ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Download className="w-3.5 h-3.5 mr-1.5" />} PDF
              </Button>
            )}
            <Link to="/history" className="text-xs text-zinc-500 hover:text-black">Historique</Link>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        <h1 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight mb-2" data-testid="analyzer-title">
          Analyseur de fiches d'agence
        </h1>
        <p className="text-sm text-zinc-500 mb-8 max-w-2xl">
          Uploadez une fiche d'agence (PDF ou image) — l'IA extrait automatiquement les caractéristiques,
          recherche les transactions DVF proches et vous donne son avis sur le prix demandé.
        </p>

        {/* Upload zone */}
        {!result && (
          <div className="max-w-xl">
            <div
              className={`border-2 border-dashed p-10 text-center cursor-pointer transition-all ${
                file ? "border-black bg-zinc-50" : "border-zinc-300 hover:border-zinc-400"
              }`}
              onClick={() => fileRef.current?.click()}
              data-testid="listing-upload-zone"
            >
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={handleFile}
                data-testid="listing-file-input"
              />
              {file ? (
                <div>
                  <FileText className="w-8 h-8 mx-auto mb-3 text-black" />
                  <p className="font-heading font-bold text-base">{file.name}</p>
                  <p className="text-xs text-zinc-400 mt-1">{(file.size / 1024).toFixed(0)} Ko — Cliquez pour changer</p>
                </div>
              ) : (
                <div>
                  <Upload className="w-8 h-8 mx-auto mb-3 text-zinc-300" />
                  <p className="text-sm text-zinc-500">Déposez une fiche d'agence</p>
                  <p className="text-xs text-zinc-400 mt-1">PDF, JPG, PNG — max 20 Mo</p>
                </div>
              )}
            </div>
            <Button
              onClick={handleAnalyze}
              disabled={!file || loading}
              className="w-full mt-4 rounded-none h-12 bg-black text-white hover:bg-zinc-800 font-heading font-medium"
              data-testid="analyze-listing-btn"
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Analyse en cours (30-60s)...</>
              ) : (
                <>Analyser la fiche</>
              )}
            </Button>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="animate-fade-in-up space-y-6">
            {/* Summary + Opinion badge */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Extracted summary */}
              <div className="lg:col-span-2 border border-zinc-200 p-6" data-testid="listing-summary">
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-3">Fiche analysée</p>
                {result.summary && <p className="text-sm text-zinc-600 leading-relaxed mb-4">{result.summary}</p>}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                  <div className="bg-zinc-50 p-3">
                    <p className="text-xs text-zinc-400 font-mono">Surface</p>
                    <p className="font-heading font-bold text-xl">{ext.surface_carrez || "?"}<span className="text-sm text-zinc-400"> m²</span></p>
                  </div>
                  <div className="bg-zinc-50 p-3">
                    <p className="text-xs text-zinc-400 font-mono">Pièces</p>
                    <p className="font-heading font-bold text-xl">{ext.rooms || "?"}<span className="text-sm text-zinc-400"> ({ext.bedrooms || "?"} ch.)</span></p>
                  </div>
                  <div className="bg-zinc-50 p-3">
                    <p className="text-xs text-zinc-400 font-mono">Étage</p>
                    <p className="font-heading font-bold text-xl">{ext.floor || "?"}<span className="text-sm text-zinc-400">/{ext.total_floors || "?"}</span></p>
                  </div>
                  <div className="bg-zinc-50 p-3">
                    <p className="text-xs text-zinc-400 font-mono">DPE</p>
                    <p className="font-heading font-bold text-xl">{ext.dpe || "?"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-xs px-2 py-1 bg-zinc-100 font-mono">{ext.property_type || "Appartement"}</span>
                  {ext.neighborhood && <span className="text-xs px-2 py-1 bg-zinc-100">{ext.neighborhood}</span>}
                  {ext.exterior_type !== "aucun" && ext.exterior_type && <span className="text-xs px-2 py-1 bg-zinc-100">{ext.exterior_count || 1}x {ext.exterior_type}</span>}
                  {ext.cave && <span className="text-xs px-2 py-1 bg-zinc-100">{ext.cave_count || 1} cave(s)</span>}
                  {ext.parking && ext.parking !== "aucun" && <span className="text-xs px-2 py-1 bg-zinc-100">Parking</span>}
                  {ext.elevator && <span className="text-xs px-2 py-1 bg-zinc-100">Ascenseur</span>}
                  <span className="text-xs px-2 py-1 bg-zinc-100">{ext.general_state === "a_renover" ? "À rénover" : ext.general_state === "bon_etat" ? "Bon état" : ext.general_state || "?"}</span>
                </div>
              </div>

              {/* Price opinion */}
              <div className="border border-zinc-200 p-6" style={{ borderLeftWidth: "4px", borderLeftColor: opConfig.color }} data-testid="price-opinion">
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-3">Avis sur le prix</p>
                <div className="flex items-center gap-3 mb-3">
                  <OpIcon className="w-6 h-6" style={{ color: opConfig.color }} />
                  <div>
                    <p className="font-heading font-bold text-xl" style={{ color: opConfig.color }} data-testid="opinion-label">{opConfig.label}</p>
                    <p className="text-xs text-zinc-400 font-mono">{analysis.price_opinion_icon}</p>
                  </div>
                </div>
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between">
                    <span className="text-xs text-zinc-500">Prix demandé</span>
                    <span className="font-mono text-sm font-bold">{formatPrice(ext.asking_price)} €</span>
                  </div>
                  {ext.parking_price > 0 && (
                    <div className="flex justify-between">
                      <span className="text-xs text-zinc-500">+ Parking</span>
                      <span className="font-mono text-sm">{formatPrice(ext.parking_price)} €</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-xs text-zinc-500">Prix/m² demandé</span>
                    <span className="font-mono text-sm">{formatPrice(mkt.asking_price_sqm)} €</span>
                  </div>
                  <div className="h-px bg-zinc-200" />
                  <div className="flex justify-between">
                    <span className="text-xs text-zinc-500">Estimation juste</span>
                    <span className="font-mono text-sm font-bold text-[#008A00]">
                      {formatPrice(analysis.estimated_fair_price_low)} — {formatPrice(analysis.estimated_fair_price_high)} €
                    </span>
                  </div>
                  <div className="h-px bg-zinc-100" />
                  <div className="flex justify-between">
                    <span className="text-xs text-zinc-500">Médiane DVF locale</span>
                    <span className="font-mono text-sm font-bold">{formatPrice(mkt.local_dvf_median_sqm)} €/m²</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-zinc-500">Rayon de recherche</span>
                    <span className="font-mono text-sm">{mkt.search_radius_m || "?"}m ({mkt.num_comparables || 0} transactions)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-zinc-500">Moy. arrondissement</span>
                    <span className="font-mono text-sm text-zinc-400">{formatPrice(mkt.arrondissement_avg_sqm)} €/m²</span>
                  </div>
                </div>
                {micro.local_premium_pct !== undefined && micro.local_premium_pct !== 0 && (
                  <div className="text-xs px-2 py-1.5 bg-zinc-50 border border-zinc-200" data-testid="micro-score">
                    <MapPin className="w-3 h-3 inline mr-1 text-zinc-400" />
                    Micro-localisation : <span className="font-mono font-bold" style={{ color: micro.local_premium_pct > 0 ? "#008A00" : "#E60000" }}>
                      {micro.local_premium_pct > 0 ? "+" : ""}{micro.local_premium_pct}%
                    </span> vs arrondissement
                  </div>
                )}
              </div>
            </div>

            {/* Verdict */}
            {analysis.verdict && (
              <div className="border border-zinc-200 p-6 bg-zinc-50" data-testid="verdict-section">
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-3">Verdict</p>
                <p className="text-sm text-zinc-700 leading-relaxed">{analysis.verdict}</p>
              </div>
            )}

            {/* Arguments for / against */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {analysis.arguments_for?.length > 0 && (
                <div className="border border-zinc-200 p-6" data-testid="arguments-for">
                  <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-3 flex items-center gap-2">
                    <TrendingUp className="w-3.5 h-3.5 text-[#008A00]" /> Arguments pour le prix
                  </p>
                  <ul className="space-y-2">
                    {analysis.arguments_for.map((arg, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-zinc-600">
                        <span className="text-[#008A00] mt-1 shrink-0">+</span>
                        <span>{arg}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {analysis.arguments_against?.length > 0 && (
                <div className="border border-zinc-200 p-6" data-testid="arguments-against">
                  <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-3 flex items-center gap-2">
                    <TrendingDown className="w-3.5 h-3.5 text-[#E60000]" /> Arguments contre le prix
                  </p>
                  <ul className="space-y-2">
                    {analysis.arguments_against.map((arg, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-zinc-600">
                        <span className="text-[#E60000] mt-1 shrink-0">-</span>
                        <span>{arg}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Negotiation tips */}
            {analysis.negotiation_tips?.length > 0 && (
              <div className="border border-zinc-200 p-6" data-testid="negotiation-tips">
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-3">Conseils de négociation</p>
                <ul className="space-y-2">
                  {analysis.negotiation_tips.map((tip, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-zinc-600">
                      <ArrowRight className="w-3.5 h-3.5 text-zinc-400 mt-0.5 shrink-0" />
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* DVF Comparables */}
            {comps.length > 0 && (
              <div className="border border-zinc-200">
                <button
                  onClick={() => setShowComps(!showComps)}
                  className="w-full px-6 py-3 flex items-center justify-between hover:bg-zinc-50 transition-colors"
                  data-testid="toggle-comparables"
                >
                  <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-mono">
                    Transactions DVF proches ({comps.length})
                  </p>
                  {showComps ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
                </button>
                {showComps && (
                  <div className="overflow-x-auto" data-testid="comparables-table">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-t border-b border-zinc-200 bg-zinc-50">
                          <th className="text-left px-4 py-2 text-xs font-mono text-zinc-400">Adresse</th>
                          <th className="text-right px-4 py-2 text-xs font-mono text-zinc-400">Dist.</th>
                          <th className="text-right px-4 py-2 text-xs font-mono text-zinc-400">Date</th>
                          <th className="text-right px-4 py-2 text-xs font-mono text-zinc-400">Surface</th>
                          <th className="text-right px-4 py-2 text-xs font-mono text-zinc-400">€/m²</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comps.map((c, i) => (
                          <tr key={i} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50">
                            <td className="px-4 py-2 text-sm">{c.address}</td>
                            <td className="px-4 py-2 text-sm text-right font-mono text-zinc-500">{c.distance_m}m</td>
                            <td className="px-4 py-2 text-sm text-right font-mono text-zinc-500">{String(c.date).slice(0, 10)}</td>
                            <td className="px-4 py-2 text-sm text-right font-mono">{c.surface?.toFixed(0)} m²</td>
                            <td className="px-4 py-2 text-sm text-right font-mono font-medium">{formatPrice(c.price_per_sqm)} €</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* All extracted fields */}
            <div className="border border-zinc-200">
              <button
                onClick={() => setShowAllFields(!showAllFields)}
                className="w-full px-6 py-3 flex items-center justify-between hover:bg-zinc-50 transition-colors"
                data-testid="toggle-all-fields"
              >
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-mono">Toutes les données extraites</p>
                {showAllFields ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
              </button>
              {showAllFields && (
                <div className="px-6 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-x-8" data-testid="all-extracted-fields">
                  <ExtractedField label="Adresse" value={ext.address} />
                  <ExtractedField label="Code postal" value={ext.postal_code} />
                  <ExtractedField label="Quartier" value={ext.neighborhood} />
                  <ExtractedField label="Prix demandé" value={ext.asking_price ? formatPrice(ext.asking_price) : null} unit=" €" />
                  <ExtractedField label="Prix/m² affiché" value={ext.price_per_sqm_asked ? formatPrice(ext.price_per_sqm_asked) : null} unit=" €" />
                  <ExtractedField label="Parking (séparé)" value={ext.parking_price > 0 ? formatPrice(ext.parking_price) : null} unit=" €" />
                  <ExtractedField label="Surface Carrez" value={ext.surface_carrez} unit=" m²" />
                  <ExtractedField label="Type" value={ext.property_type} />
                  <ExtractedField label="Pièces" value={ext.rooms} />
                  <ExtractedField label="Chambres" value={ext.bedrooms} />
                  <ExtractedField label="SdB" value={ext.bathrooms} />
                  <ExtractedField label="Étage" value={ext.floor} />
                  <ExtractedField label="Ascenseur" value={ext.elevator} />
                  <ExtractedField label="Exposition" value={ext.exposure} />
                  <ExtractedField label="Vue" value={ext.view} />
                  <ExtractedField label="Extérieur" value={ext.exterior_type !== "aucun" ? `${ext.exterior_count || 1}x ${ext.exterior_type}` : "Aucun"} />
                  <ExtractedField label="Surface ext." value={ext.exterior_surface > 0 ? ext.exterior_surface : null} unit=" m²" />
                  <ExtractedField label="HSP" value={ext.ceiling_height} unit=" m" />
                  <ExtractedField label="Parking" value={ext.parking} />
                  <ExtractedField label="Cave(s)" value={ext.cave_count > 0 ? ext.cave_count : "Non"} />
                  <ExtractedField label="État" value={ext.general_state} />
                  <ExtractedField label="Construction" value={ext.construction_year} />
                  <ExtractedField label="Immeuble" value={ext.building_type} />
                  <ExtractedField label="DPE" value={ext.dpe} />
                  <ExtractedField label="GES" value={ext.ges} />
                  <ExtractedField label="Charges/an" value={ext.annual_charges > 0 ? formatPrice(ext.annual_charges) : null} unit=" €" />
                  <ExtractedField label="Taxe foncière" value={ext.property_tax > 0 ? formatPrice(ext.property_tax) : null} unit=" €" />
                  <ExtractedField label="Lots copro" value={ext.total_lots} />
                  <ExtractedField label="Gardien" value={ext.concierge} />
                  <ExtractedField label="Chauffage" value={ext.heating} />
                  <ExtractedField label="Vitrage" value={ext.windows} />
                  <ExtractedField label="Agence" value={ext.agency_name} />
                </div>
              )}
            </div>

            {/* Notable features & defects */}
            {(ext.notable_features?.length > 0 || ext.notable_defects?.length > 0) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {ext.notable_features?.length > 0 && (
                  <div className="border border-zinc-200 border-l-4 border-l-[#008A00] p-5" data-testid="notable-features">
                    <p className="text-xs font-mono text-zinc-400 mb-2">Points forts mentionnés</p>
                    <ul className="space-y-1">
                      {ext.notable_features.map((f, i) => <li key={i} className="text-sm text-zinc-600 flex items-start gap-2"><span className="text-[#008A00]">+</span>{f}</li>)}
                    </ul>
                  </div>
                )}
                {ext.notable_defects?.length > 0 && (
                  <div className="border border-zinc-200 border-l-4 border-l-[#E60000] p-5" data-testid="notable-defects">
                    <p className="text-xs font-mono text-zinc-400 mb-2">Points de vigilance</p>
                    <ul className="space-y-1">
                      {ext.notable_defects.map((d, i) => <li key={i} className="text-sm text-zinc-600 flex items-start gap-2"><span className="text-[#E60000]">-</span>{d}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-4 pt-4 border-t border-zinc-200 flex-wrap">
              <Button
                onClick={handleLaunchEstimation}
                className="rounded-none h-12 px-8 bg-black text-white hover:bg-zinc-800 font-heading font-medium"
                data-testid="launch-full-estimation-btn"
              >
                Lancer une estimation complète <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
              <Button
                variant="outline"
                onClick={handleDownloadPdf}
                disabled={pdfLoading || !result?.analysis_id}
                className="rounded-none h-12 px-6"
                data-testid="listing-download-pdf-btn"
              >
                {pdfLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
                Télécharger le rapport PDF
              </Button>
              <Button
                variant="outline"
                onClick={() => { setResult(null); setFile(null); }}
                className="rounded-none h-12 px-6"
                data-testid="analyze-another-btn"
              >
                Analyser une autre fiche
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
