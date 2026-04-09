import { useState } from "react";
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus, Info, ArrowRight } from "lucide-react";

function formatPrice(n) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

function ImpactBar({ value, type }) {
  const isPositive = value > 0;
  const absValue = Math.abs(value);
  const maxWidth = type === "pct" ? Math.min(absValue * 4, 100) : Math.min(absValue / 1000, 100);
  
  return (
    <div className="flex items-center gap-3 mt-2">
      <div className="w-32 h-2 bg-zinc-100 relative overflow-hidden">
        <div
          className="h-2 transition-all duration-500"
          style={{
            width: `${maxWidth}%`,
            backgroundColor: isPositive ? "#008A00" : "#E60000",
          }}
        />
      </div>
      <span className={`font-mono text-xs font-semibold ${isPositive ? "text-[#008A00]" : "text-[#E60000]"}`}>
        {isPositive ? "+" : ""}{value}{type === "pct" ? "%" : type === "flat" ? ` €` : " €/m²"}
      </span>
    </div>
  );
}

function AdjustmentCard({ adjustment, index, basePrice }) {
  const [localExpanded, setLocalExpanded] = useState(false);
  const expanded = adjustment._forceExpanded || localExpanded;
  const toggle = () => setLocalExpanded(!localExpanded);
  const isPositive = adjustment.value > 0;
  const isNegative = adjustment.value < 0;
  const Icon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;
  const borderColor = isPositive ? "border-l-[#008A00]" : isNegative ? "border-l-[#E60000]" : "border-l-zinc-300";
  
  // Calculate euro impact
  let euroImpact = 0;
  if (adjustment.type === "pct") {
    euroImpact = Math.round(basePrice * adjustment.value / 100);
  } else if (adjustment.type === "flat") {
    euroImpact = Math.round(adjustment.value);
  } else if (adjustment.type === "flat_per_sqm") {
    euroImpact = Math.round(adjustment.value);
  }

  return (
    <div
      className={`border border-zinc-200 border-l-4 ${borderColor} bg-white transition-all duration-200 hover:shadow-sm animate-fade-in-up`}
      style={{ animationDelay: `${index * 0.06}s` }}
      data-testid={`hypothesis-${index}`}
    >
      {/* Header - always visible */}
      <button
        onClick={() => toggle()}
        className="w-full text-left px-5 py-4 flex items-center justify-between group"
        data-testid={`hypothesis-toggle-${index}`}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className={`w-8 h-8 flex items-center justify-center shrink-0 ${isPositive ? "bg-green-50" : isNegative ? "bg-red-50" : "bg-zinc-50"}`}>
            <Icon className={`w-4 h-4 ${isPositive ? "text-[#008A00]" : isNegative ? "text-[#E60000]" : "text-zinc-400"}`} strokeWidth={2} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-zinc-900 truncate">{adjustment.name}</p>
            <p className="text-xs text-zinc-400">{adjustment.detail}</p>
          </div>
        </div>
        <div className="flex items-center gap-4 shrink-0 ml-4">
          <div className="text-right">
            <p className={`font-mono text-sm font-bold ${isPositive ? "text-[#008A00]" : isNegative ? "text-[#E60000]" : "text-zinc-500"}`}>
              {isPositive ? "+" : ""}{adjustment.value}{adjustment.type === "pct" ? "%" : " €"}
            </p>
            {euroImpact !== 0 && adjustment.type === "pct" && (
              <p className="font-mono text-xs text-zinc-400">
                {euroImpact > 0 ? "+" : ""}{formatPrice(euroImpact)} €/m²
              </p>
            )}
          </div>
          {expanded ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-300 group-hover:text-zinc-500 transition-colors" />}
        </div>
      </button>

      {/* Expanded content - hypothesis */}
      {expanded && adjustment.hypothesis && (
        <div className="px-5 pb-5 border-t border-zinc-100">
          <div className="pt-4 pl-11">
            <div className="flex items-start gap-2 mb-3">
              <Info className="w-3.5 h-3.5 text-zinc-400 mt-0.5 shrink-0" />
              <p className="text-xs uppercase tracking-[0.15em] text-zinc-400 font-mono font-medium">Hypothèse et justification</p>
            </div>
            <p className="text-sm text-zinc-600 leading-relaxed" data-testid={`hypothesis-text-${index}`}>
              {adjustment.hypothesis}
            </p>
            <ImpactBar value={adjustment.value} type={adjustment.type} />
          </div>
        </div>
      )}
    </div>
  );
}

export default function HypothesesPanel({ adjustments, marketData }) {
  const [allExpanded, setAllExpanded] = useState(false);
  const basePrice = marketData?.base_price_sqm || 10500;
  const arrAvg = marketData?.arrondissement_avg_sqm || 10500;
  const totalPct = marketData?.adjustment_pct || 0;
  const positiveCount = adjustments.filter(a => a.value > 0).length;
  const negativeCount = adjustments.filter(a => a.value < 0).length;

  // Calculate difference vs arrondissement average
  const finalPriceSqm = Math.round(basePrice * (1 + totalPct / 100));
  const diffVsArr = finalPriceSqm - arrAvg;
  const diffPct = arrAvg > 0 ? ((diffVsArr / arrAvg) * 100).toFixed(1) : 0;

  return (
    <div data-testid="hypotheses-panel">
      {/* Summary header */}
      <div className="border border-zinc-200 p-6 mb-6 bg-zinc-50" data-testid="hypotheses-summary">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Pourquoi ce prix ?</p>
            <h3 className="font-heading font-bold text-lg tracking-tight mb-1">
              Ce bien est estimé {diffVsArr >= 0 ? "au-dessus" : "en-dessous"} de la moyenne de l'arrondissement
            </h3>
            <p className="text-sm text-zinc-500 leading-relaxed max-w-2xl">
              Le prix médian au m² dans le {marketData?.arrondissement?.slice(-2) || "?"}e arrondissement est de <strong className="font-mono">{formatPrice(arrAvg)} €/m²</strong>.
              Votre bien est estimé à <strong className="font-mono">{formatPrice(finalPriceSqm)} €/m²</strong>, 
              soit <span className={`font-mono font-semibold ${diffVsArr >= 0 ? "text-[#008A00]" : "text-[#E60000]"}`}>
                {diffVsArr >= 0 ? "+" : ""}{diffPct}%
              </span> par rapport à cette moyenne.
              Voici pourquoi.
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-center px-4 py-2 border border-zinc-200 bg-white">
              <p className="font-mono text-xl font-bold text-[#008A00]">{positiveCount}</p>
              <p className="text-xs text-zinc-400">surcotes</p>
            </div>
            <div className="text-center px-4 py-2 border border-zinc-200 bg-white">
              <p className="font-mono text-xl font-bold text-[#E60000]">{negativeCount}</p>
              <p className="text-xs text-zinc-400">décotes</p>
            </div>
          </div>
        </div>

        {/* Price flow */}
        <div className="mt-5 flex items-center gap-3 flex-wrap">
          <div className="px-3 py-1.5 bg-white border border-zinc-200">
            <p className="text-xs text-zinc-400 font-mono">Médiane DVF locale</p>
            <p className="font-mono text-sm font-bold">{formatPrice(basePrice)} €/m²</p>
          </div>
          <ArrowRight className="w-4 h-4 text-zinc-300 shrink-0" />
          <div className="px-3 py-1.5 bg-white border border-zinc-200">
            <p className="text-xs text-zinc-400 font-mono">Ajustements</p>
            <p className={`font-mono text-sm font-bold ${totalPct >= 0 ? "text-[#008A00]" : "text-[#E60000]"}`}>
              {totalPct >= 0 ? "+" : ""}{totalPct}%
            </p>
          </div>
          <ArrowRight className="w-4 h-4 text-zinc-300 shrink-0" />
          <div className="px-3 py-1.5 bg-black text-white">
            <p className="text-xs text-zinc-400 font-mono">Prix estimé</p>
            <p className="font-mono text-sm font-bold">{formatPrice(finalPriceSqm)} €/m²</p>
          </div>
        </div>

        {marketData?.base_source && (
          <p className="text-xs text-zinc-400 mt-3 font-mono">
            Source prix de base : {marketData.base_source} ({marketData.comparables_period || ""})
            {marketData.total_comparables > 0 && ` — ${marketData.total_comparables} transactions analysées`}
          </p>
        )}

        {/* Reliability + Street Coefficient */}
        {marketData?.reliability && (
          <div className="mt-3 flex items-center gap-4 flex-wrap">
            <span className={`inline-flex items-center px-2 py-1 text-xs font-mono font-bold rounded-sm ${
              marketData.reliability === "HAUTE" ? "bg-green-50 text-[#008A00]" :
              marketData.reliability === "MOYENNE" ? "bg-amber-50 text-[#F59E0B]" :
              "bg-red-50 text-[#E60000]"
            }`} data-testid="reliability-indicator">
              Fiabilité {marketData.reliability.toLowerCase()}
            </span>
            {marketData.street_coefficient && marketData.street_coefficient !== 1.0 && (
              <span className="text-xs font-mono text-zinc-500" data-testid="street-coeff-display">
                {marketData.street_coefficient_detail}
              </span>
            )}
          </div>
        )}

        {/* Micro-score */}
        {marketData?.micro_score && marketData.micro_score.score > 0 && (
          <div className="mt-4 px-4 py-3 border border-zinc-200 bg-white flex items-center justify-between flex-wrap gap-3" data-testid="micro-score-panel">
            <div>
              <p className="text-xs text-zinc-400 font-mono mb-1">Score micro-localisation</p>
              <p className="text-sm text-zinc-600">{marketData.micro_score.detail}</p>
            </div>
            <div className="flex items-center gap-3">
              {marketData.micro_score.density_300m > 0 && (
                <div className="text-center px-3 py-1 bg-zinc-50 border border-zinc-100">
                  <p className="font-mono text-sm font-bold">{marketData.micro_score.density_300m}</p>
                  <p className="text-[10px] text-zinc-400">à 300m</p>
                </div>
              )}
              <div className="text-center px-3 py-1 bg-zinc-50 border border-zinc-100">
                <p className="font-mono text-sm font-bold" style={{ color: marketData.micro_score.local_premium_pct > 0 ? "#008A00" : marketData.micro_score.local_premium_pct < 0 ? "#E60000" : "#18181B" }}>
                  {marketData.micro_score.local_premium_pct > 0 ? "+" : ""}{marketData.micro_score.local_premium_pct}%
                </p>
                <p className="text-[10px] text-zinc-400">vs arr.</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Toggle all */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono">{adjustments.length} critères analysés</p>
        <button
          onClick={() => setAllExpanded(!allExpanded)}
          className="text-xs text-zinc-500 hover:text-black transition-colors underline underline-offset-2"
          data-testid="toggle-all-hypotheses"
        >
          {allExpanded ? "Tout replier" : "Tout déplier"}
        </button>
      </div>

      {/* Adjustments list */}
      <div className="space-y-2">
        {adjustments.map((adj, i) => (
          <AdjustmentCard
            key={i}
            adjustment={{ ...adj, _forceExpanded: allExpanded }}
            index={i}
            basePrice={basePrice}
          />
        ))}
      </div>

      {/* No adjustment message */}
      {adjustments.length === 0 && (
        <div className="border border-zinc-200 p-8 text-center">
          <p className="text-sm text-zinc-500">Aucun ajustement appliqué — le bien est à la médiane du quartier.</p>
        </div>
      )}
    </div>
  );
}
