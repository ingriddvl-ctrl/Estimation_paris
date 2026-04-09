import { useState, useEffect, useCallback } from "react";
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, useMap } from "react-leaflet";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Loader2, Eye, EyeOff, ChevronDown, ChevronUp, RefreshCw, AlertTriangle, ExternalLink } from "lucide-react";
import "leaflet/dist/leaflet.css";

function formatPrice(n) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

function MapAutoCenter({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] && center[1]) map.setView(center, 15);
  }, [center, map]);
  return null;
}

function HeatmapLayer({ comparables }) {
  const map = useMap();
  useEffect(() => {
    if (!comparables?.length) return;
    let L;
    try {
      L = require("leaflet");
      require("leaflet.heat");
    } catch { return; }
    const points = comparables
      .filter(c => c.latitude && c.longitude)
      .map(c => [c.latitude, c.longitude, c.price_per_sqm / 100]);
    if (!points.length) return;
    const heat = L.heatLayer(points, {
      radius: 30, blur: 25, maxZoom: 17,
      max: Math.max(...comparables.map(c => c.price_per_sqm)) / 100,
      gradient: { 0.2: "#008A00", 0.5: "#FFC107", 0.8: "#FF6B00", 1: "#E60000" },
    }).addTo(map);
    return () => { map.removeLayer(heat); };
  }, [comparables, map]);
  return null;
}

function RelevanceBar({ score }) {
  const color = score >= 70 ? "#008A00" : score >= 40 ? "#F59E0B" : "#E60000";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-zinc-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
      <span className="font-mono text-xs" style={{ color }}>{score}</span>
    </div>
  );
}

const CIRCLE_LABELS = {
  1: { label: "C1", title: "Même rue", color: "#008A00", bg: "#f0fdf4" },
  2: { label: "C2", title: "Même type 200m", color: "#2563EB", bg: "#eff6ff" },
  3: { label: "C3", title: "Rayon élargi", color: "#71717A", bg: "#f4f4f5" },
};

const RELIABILITY_CONFIG = {
  "HAUTE": { color: "#008A00", bg: "#f0fdf4", label: "Fiabilité haute" },
  "MOYENNE": { color: "#F59E0B", bg: "#fffbeb", label: "Fiabilité moyenne" },
  "BASSE": { color: "#E60000", bg: "#fef2f2", label: "Fiabilité basse — estimation indicative" },
};

function CircleBadge({ circle }) {
  const cfg = CIRCLE_LABELS[circle] || CIRCLE_LABELS[3];
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono font-bold rounded-sm" style={{ color: cfg.color, backgroundColor: cfg.bg }} title={cfg.title}>
      {cfg.label}
    </span>
  );
}

export default function ComparablesMap({ comparables, excludedComparables, center, estimatedPrice, searchRadius, valuationId, crossCalibrationWarning, circleStats, streetCoefficient, onRecalculate }) {
  const [excludedIds, setExcludedIds] = useState(new Set());
  const [recalculating, setRecalculating] = useState(false);
  const [showExcluded, setShowExcluded] = useState(false);
  const [recalcResult, setRecalcResult] = useState(null);

  const activeComps = recalcResult?.comparables || comparables || [];
  const activeExcluded = recalcResult?.excluded_comparables || excludedComparables || [];
  const radiusM = recalcResult?.search_radius_m || searchRadius || 500;

  const getColor = (priceSqm) => {
    const ref = recalcResult?.new_price_per_sqm_median || estimatedPrice || 10000;
    const diff = ((priceSqm - ref) / ref) * 100;
    if (diff > 5) return "#E60000";
    if (diff < -5) return "#008A00";
    return "#18181B";
  };

  const getCompId = (c) => `${c.address}_${c.date}_${c.price}`;

  const toggleExclusion = useCallback((comp) => {
    setExcludedIds(prev => {
      const next = new Set(prev);
      const id = getCompId(comp);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleRecalculate = async () => {
    if (!valuationId || excludedIds.size === 0) return;
    setRecalculating(true);
    try {
      const result = await api.recalculateValuation(valuationId, [...excludedIds]);
      setRecalcResult(result);
      if (onRecalculate) onRecalculate(result);
      toast.success(`Recalcul effectué — ${result.comparables_count} comparables retenus`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Erreur de recalcul");
    } finally {
      setRecalculating(false);
    }
  };

  const resetExclusions = () => {
    setExcludedIds(new Set());
    setRecalcResult(null);
  };

  return (
    <div data-testid="comparables-map">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-1">Carte des comparables DVF</p>
          <p className="text-sm text-zinc-500">
            {activeComps.length} retenues{activeExcluded.length > 0 && `, ${activeExcluded.length} exclues`} — rayon {radiusM}m — 24 mois max
          </p>
          {/* Circle stats + reliability */}
          {(circleStats || recalcResult?.circle_stats) && (
            <div className="flex items-center gap-3 mt-2 flex-wrap" data-testid="circle-stats">
              {(() => {
                const cs = recalcResult?.circle_stats || circleStats || {};
                const rel = cs.reliability || "BASSE";
                const relCfg = RELIABILITY_CONFIG[rel] || RELIABILITY_CONFIG["BASSE"];
                return (
                  <>
                    <span className="inline-flex items-center gap-1 text-xs px-2 py-1 font-mono font-bold" style={{ color: relCfg.color, backgroundColor: relCfg.bg }} data-testid="reliability-badge">
                      {relCfg.label}
                    </span>
                    {cs.circle_1_count > 0 && <span className="text-xs font-mono text-[#008A00]">C1: {cs.circle_1_count}</span>}
                    {cs.circle_2_count > 0 && <span className="text-xs font-mono text-[#2563EB]">C2: {cs.circle_2_count}</span>}
                    {cs.circle_3_count > 0 && <span className="text-xs font-mono text-zinc-500">C3: {cs.circle_3_count}</span>}
                  </>
                );
              })()}
            </div>
          )}
          {/* Street coefficient */}
          {(streetCoefficient || recalcResult?.street_coefficient) && (() => {
            const sc = recalcResult?.street_coefficient || streetCoefficient || {};
            if (sc.value && sc.value !== 1.0) {
              return (
                <p className="text-xs font-mono text-zinc-500 mt-1" data-testid="street-coefficient">
                  {sc.detail}
                </p>
              );
            }
            return null;
          })()}
          {recalcResult && (
            <p className="text-sm font-mono font-bold mt-1" data-testid="recalc-result">
              Nouvelle base DVF : {formatPrice(recalcResult.new_base_price_sqm)} €/m² →{" "}
              <span className="text-[#008A00]">{formatPrice(recalcResult.new_price_median)} €</span>
              {" "}({formatPrice(recalcResult.new_price_low)} – {formatPrice(recalcResult.new_price_high)})
            </p>
          )}
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#008A00]" /> Moins cher</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#18181B]" /> Similaire</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#E60000]" /> Plus cher</span>
        </div>
      </div>

      {/* Map */}
      <div className="border border-zinc-200 h-[400px]">
        <MapContainer center={center} zoom={15} style={{ height: "100%", width: "100%" }} scrollWheelZoom={true}>
          <MapAutoCenter center={center} />
          <TileLayer url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" attribution='&copy; OpenStreetMap' />
          <HeatmapLayer comparables={activeComps} />
          <Circle center={center} radius={radiusM} pathOptions={{ color: "#18181B", weight: 1, dashArray: "6 4", fillOpacity: 0.03 }} />
          {activeComps.map((c, i) => (
            <CircleMarker key={i} center={[c.latitude || center[0], c.longitude || center[1]]} radius={6}
              fillColor={excludedIds.has(getCompId(c)) ? "#D4D4D8" : getColor(c.price_per_sqm)}
              color="#fff" weight={1.5} opacity={excludedIds.has(getCompId(c)) ? 0.4 : 1} fillOpacity={excludedIds.has(getCompId(c)) ? 0.3 : 0.85}>
              <Popup>
                <div className="text-xs space-y-1 min-w-[180px]">
                  <p className="font-bold">{c.address}</p>
                  <p className="font-mono">{formatPrice(c.price)} € — {formatPrice(c.price_per_sqm)} €/m²</p>
                  <p>{c.surface} m² — {c.rooms} p. — {c.date}</p>
                  {c.distance_m !== undefined && <p>Distance : {c.distance_m}m</p>}
                  {c.relevance_score !== undefined && <p>Pertinence : {c.relevance_score}/100</p>}
                </div>
              </Popup>
            </CircleMarker>
          ))}
          <CircleMarker center={center} radius={10} fillColor="#0022EE" color="#fff" weight={2} opacity={1} fillOpacity={1}>
            <Popup><div className="text-xs font-bold">Votre bien</div></Popup>
          </CircleMarker>
        </MapContainer>
      </div>

      {/* Cross-calibration warning */}
      {crossCalibrationWarning && (
        <div className="mt-4 p-4 border border-amber-200 bg-amber-50 flex items-start gap-3" data-testid="cross-calibration-warning">
          <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-medium text-amber-800 mb-1">Calibration croisée recommandée</p>
            <p className="text-xs text-amber-700">{crossCalibrationWarning}</p>
            <div className="flex gap-3 mt-2">
              <a href="https://www.seloger.com" target="_blank" rel="noopener noreferrer" className="text-xs text-amber-800 underline flex items-center gap-1">
                SeLoger <ExternalLink className="w-3 h-3" />
              </a>
              <a href="https://www.leboncoin.fr/immobilier" target="_blank" rel="noopener noreferrer" className="text-xs text-amber-800 underline flex items-center gap-1">
                LeBonCoin <ExternalLink className="w-3 h-3" />
              </a>
              <a href="https://www.meilleursagents.com" target="_blank" rel="noopener noreferrer" className="text-xs text-amber-800 underline flex items-center gap-1">
                MeilleursAgents <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Recalculate bar */}
      {excludedIds.size > 0 && valuationId && (
        <div className="mt-4 flex items-center gap-3 p-3 border border-zinc-300 bg-zinc-50" data-testid="recalc-bar">
          <p className="text-xs text-zinc-600 flex-1">
            <span className="font-mono font-bold">{excludedIds.size}</span> comparable(s) exclu(s) manuellement
          </p>
          <Button size="sm" variant="outline" onClick={resetExclusions} className="rounded-none text-xs h-8" data-testid="reset-exclusions-btn">
            Réinitialiser
          </Button>
          <Button size="sm" onClick={handleRecalculate} disabled={recalculating} className="rounded-none bg-black text-white hover:bg-zinc-800 text-xs h-8" data-testid="recalculate-btn">
            {recalculating ? <Loader2 className="w-3 h-3 mr-1.5 animate-spin" /> : <RefreshCw className="w-3 h-3 mr-1.5" />}
            Recalculer
          </Button>
        </div>
      )}

      {/* Included comparables table */}
      {activeComps.length > 0 && (
        <div className="mt-6 border border-zinc-200">
          <div className="px-4 py-2 bg-zinc-50 border-b border-zinc-200 flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-mono">
              Transactions retenues ({activeComps.length})
            </p>
            <p className="text-xs text-zinc-400">Cliquez sur une ligne pour l'exclure</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200">
                  <th className="w-8 px-2 py-2"></th>
                  <th className="px-2 py-2 text-xs font-mono text-zinc-400 text-center">C.</th>
                  <th className="text-left px-3 py-2 text-xs font-mono text-zinc-400">Adresse</th>
                  <th className="text-right px-3 py-2 text-xs font-mono text-zinc-400">Dist.</th>
                  <th className="text-right px-3 py-2 text-xs font-mono text-zinc-400">Date</th>
                  <th className="text-right px-3 py-2 text-xs font-mono text-zinc-400">Surface</th>
                  <th className="text-right px-3 py-2 text-xs font-mono text-zinc-400">Pièces</th>
                  <th className="text-right px-3 py-2 text-xs font-mono text-zinc-400">€/m²</th>
                  <th className="text-center px-3 py-2 text-xs font-mono text-zinc-400">Score</th>
                </tr>
              </thead>
              <tbody>
                {activeComps.slice(0, 25).map((c, i) => {
                  const cId = getCompId(c);
                  const isExcl = excludedIds.has(cId);
                  return (
                    <tr key={i}
                      className={`border-b border-zinc-100 last:border-0 cursor-pointer transition-colors ${isExcl ? "bg-zinc-100 opacity-50 line-through" : "hover:bg-zinc-50"}`}
                      onClick={() => toggleExclusion(c)}
                      data-testid={`comparable-row-${i}`}
                    >
                      <td className="px-2 py-2 text-center">
                        {isExcl ? <EyeOff className="w-3.5 h-3.5 text-zinc-400 mx-auto" /> : <Eye className="w-3.5 h-3.5 text-zinc-300 mx-auto" />}
                      </td>
                      <td className="px-2 py-2 text-center">
                        {c.circle ? <CircleBadge circle={c.circle} /> : <span className="text-xs text-zinc-300">—</span>}
                      </td>
                      <td className="px-3 py-2 text-sm max-w-[200px] truncate">{c.address}</td>
                      <td className="px-3 py-2 text-sm text-right font-mono text-zinc-500">{c.distance_m}m</td>
                      <td className="px-3 py-2 text-sm text-right font-mono text-zinc-500">{String(c.date).slice(0, 10)}</td>
                      <td className="px-3 py-2 text-sm text-right font-mono">{c.surface?.toFixed(0)} m²</td>
                      <td className="px-3 py-2 text-sm text-right font-mono text-zinc-500">{c.rooms || "?"}</td>
                      <td className="px-3 py-2 text-sm text-right font-mono font-medium" style={{ color: getColor(c.price_per_sqm) }}>
                        {formatPrice(c.price_per_sqm)} €
                      </td>
                      <td className="px-3 py-2">
                        {c.relevance_score !== undefined ? <RelevanceBar score={c.relevance_score} /> : <span className="text-xs text-zinc-300">—</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Excluded comparables */}
      {activeExcluded.length > 0 && (
        <div className="mt-4 border border-zinc-200">
          <button onClick={() => setShowExcluded(!showExcluded)}
            className="w-full px-4 py-2 bg-zinc-50 border-b border-zinc-200 flex items-center justify-between hover:bg-zinc-100 transition-colors"
            data-testid="toggle-excluded">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono">
              Transactions exclues ({activeExcluded.length}) — Raisons de l'exclusion
            </p>
            {showExcluded ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
          </button>
          {showExcluded && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200">
                    <th className="text-left px-3 py-2 text-xs font-mono text-zinc-400">Adresse</th>
                    <th className="text-right px-3 py-2 text-xs font-mono text-zinc-400">€/m²</th>
                    <th className="text-right px-3 py-2 text-xs font-mono text-zinc-400">Surface</th>
                    <th className="text-right px-3 py-2 text-xs font-mono text-zinc-400">Date</th>
                    <th className="text-left px-3 py-2 text-xs font-mono text-zinc-400">Raison d'exclusion</th>
                  </tr>
                </thead>
                <tbody>
                  {activeExcluded.map((c, i) => (
                    <tr key={i} className="border-b border-zinc-100 last:border-0 bg-red-50/30" data-testid={`excluded-row-${i}`}>
                      <td className="px-3 py-2 text-sm text-zinc-400 max-w-[180px] truncate">{c.address}</td>
                      <td className="px-3 py-2 text-sm text-right font-mono text-zinc-400">{formatPrice(c.price_per_sqm)} €</td>
                      <td className="px-3 py-2 text-sm text-right font-mono text-zinc-400">{c.surface?.toFixed(0)} m²</td>
                      <td className="px-3 py-2 text-sm text-right font-mono text-zinc-400">{String(c.date).slice(0, 10)}</td>
                      <td className="px-3 py-2">
                        {(c.exclusion_reasons || []).map((r, j) => (
                          <span key={j} className="inline-block text-xs bg-red-100 text-red-700 px-2 py-0.5 mr-1 mb-0.5">{r}</span>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
