import { useState } from "react";
import { TrendingUp, TrendingDown, Activity, AlertTriangle, ExternalLink, ChevronDown, ChevronUp } from "lucide-react";

function formatPrice(n) {
  if (!n && n !== 0) return "—";
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

function TensionGauge({ score, label }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= 70 ? "#E60000" : pct >= 50 ? "#F59E0B" : "#008A00";
  return (
    <div data-testid="tension-gauge">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider">Tension du marché</span>
        <span className="text-sm font-mono font-bold" style={{ color }}>{score}/100</span>
      </div>
      <div className="h-2.5 bg-zinc-100 w-full">
        <div className="h-full transition-all duration-700" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <p className="text-xs text-zinc-500 mt-1.5 font-mono">{label}</p>
    </div>
  );
}

function SpreadCard({ spread }) {
  if (!spread) return null;
  const isLocal = spread.spread_source === "calcul_local";
  return (
    <div className="border border-zinc-200 p-5" data-testid="spread-card">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-zinc-400" />
        <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
          Spread annonces / transactions
        </span>
        <span className={`text-[10px] px-1.5 py-0.5 font-mono ml-auto ${isLocal ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
          {isLocal ? "calcul local" : "estimation zone"}
        </span>
      </div>
      <p className="font-heading font-bold text-2xl tracking-tight mb-1">
        {spread.spread_pct}%
      </p>
      <p className="text-xs text-zinc-500 leading-relaxed">
        Les biens se vendent en moyenne <strong>{spread.spread_pct}%</strong> en dessous du prix affiché dans cette zone.
        {spread.num_listings > 0 && <> Basé sur {spread.num_listings} annonces actives et {spread.num_dvf} transactions DVF.</>}
      </p>
      {(spread.dvf_median_sqm > 0 || spread.listing_median_sqm > 0) && (
        <div className="grid grid-cols-2 gap-3 mt-4">
          <div className="bg-zinc-50 p-3">
            <p className="text-[10px] text-zinc-400 font-mono">Prix DVF (réel)</p>
            <p className="font-mono font-bold text-sm">{formatPrice(spread.dvf_median_sqm)} €/m²</p>
          </div>
          <div className="bg-zinc-50 p-3">
            <p className="text-[10px] text-zinc-400 font-mono">Prix annonces</p>
            <p className="font-mono font-bold text-sm">{formatPrice(spread.listing_median_sqm)} €/m²</p>
          </div>
        </div>
      )}
    </div>
  );
}

function TransactionEstimate({ estimate }) {
  if (!estimate) return null;
  return (
    <div className="border-2 border-black p-5" data-testid="transaction-estimate">
      <div className="flex items-center gap-2 mb-3">
        <TrendingDown className="w-4 h-4" />
        <span className="text-xs font-mono uppercase tracking-wider">
          Estimation du prix de transaction
        </span>
      </div>
      <div className="grid grid-cols-3 gap-4 mb-3">
        <div>
          <p className="text-[10px] text-zinc-400 font-mono">Prix demandé</p>
          <p className="font-mono text-sm line-through text-zinc-400">{formatPrice(estimate.asking_price)} €</p>
        </div>
        <div>
          <p className="text-[10px] text-zinc-400 font-mono">Estimation transaction</p>
          <p className="font-mono text-lg font-bold">{formatPrice(estimate.estimated_transaction_price)} €</p>
        </div>
        <div>
          <p className="text-[10px] text-zinc-400 font-mono">Décote estimée</p>
          <p className="font-mono text-lg font-bold text-[#008A00]">-{estimate.discount_pct}%</p>
        </div>
      </div>
      <div className="bg-zinc-50 p-3">
        <p className="text-[10px] text-zinc-400 font-mono mb-1">Fourchette probable</p>
        <p className="font-mono text-sm font-medium">
          {formatPrice(estimate.estimated_transaction_low)} € — {formatPrice(estimate.estimated_transaction_high)} €
        </p>
      </div>
    </div>
  );
}

function CastorusData({ castorus }) {
  if (!castorus) return null;
  return (
    <div className="border border-amber-200 bg-amber-50/30 p-5" data-testid="castorus-data">
      <div className="flex items-center gap-2 mb-3">
        <ExternalLink className="w-4 h-4 text-amber-600" />
        <span className="text-xs font-mono uppercase tracking-wider text-amber-600">Données Castorus</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {castorus.days_on_market && (
          <div>
            <p className="text-[10px] text-zinc-400 font-mono">Jours en vente</p>
            <p className="font-mono text-lg font-bold">{castorus.days_on_market}j</p>
          </div>
        )}
        {castorus.num_price_drops !== undefined && (
          <div>
            <p className="text-[10px] text-zinc-400 font-mono">Baisses de prix</p>
            <p className="font-mono text-lg font-bold">{castorus.num_price_drops}</p>
          </div>
        )}
        {castorus.total_drop_pct !== undefined && castorus.total_drop_pct !== 0 && (
          <div>
            <p className="text-[10px] text-zinc-400 font-mono">Baisse totale</p>
            <p className="font-mono text-lg font-bold text-[#008A00]">-{castorus.total_drop_pct}%</p>
          </div>
        )}
        {castorus.initial_price && (
          <div>
            <p className="text-[10px] text-zinc-400 font-mono">Prix initial</p>
            <p className="font-mono text-sm">{formatPrice(castorus.initial_price)} €</p>
          </div>
        )}
      </div>
      {castorus.price_history && castorus.price_history.length > 1 && (
        <div className="mt-3 pt-3 border-t border-amber-200">
          <p className="text-[10px] text-zinc-400 font-mono mb-2">Historique des prix</p>
          <div className="space-y-1">
            {castorus.price_history.map((h, i) => (
              <div key={i} className="flex justify-between text-xs font-mono">
                <span className="text-zinc-500">{h.date}</span>
                <span className={i > 0 && h.price < castorus.price_history[i-1].price ? "text-[#008A00] font-bold" : ""}>
                  {formatPrice(h.price)} €
                  {i > 0 && h.price < castorus.price_history[i-1].price && " ↓"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ListingsSample({ listings }) {
  const [expanded, setExpanded] = useState(false);
  if (!listings || listings.length === 0) return null;

  const shown = expanded ? listings : listings.slice(0, 5);
  return (
    <div className="border border-zinc-200" data-testid="listings-sample">
      <div className="px-4 py-2.5 bg-zinc-50 border-b border-zinc-200 flex items-center justify-between">
        <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-mono">
          Annonces actives comparables ({listings.length})
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-200 text-xs font-mono text-zinc-400">
              <th className="text-left px-4 py-2">Quartier</th>
              <th className="text-right px-4 py-2">Prix</th>
              <th className="text-right px-4 py-2">Surface</th>
              <th className="text-right px-4 py-2">€/m²</th>
              <th className="text-right px-4 py-2">Pièces</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((l, i) => (
              <tr key={i} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50" data-testid={`active-listing-${i}`}>
                <td className="px-4 py-2 text-sm max-w-[180px] truncate">{l.neighborhood || "—"}</td>
                <td className="px-4 py-2 text-sm text-right font-mono">{formatPrice(l.price)} €</td>
                <td className="px-4 py-2 text-sm text-right font-mono">{l.surface} m²</td>
                <td className="px-4 py-2 text-sm text-right font-mono font-medium">{formatPrice(l.price_per_sqm)} €</td>
                <td className="px-4 py-2 text-sm text-right font-mono">{l.rooms || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {listings.length > 5 && (
        <button onClick={() => setExpanded(!expanded)} className="w-full py-2 text-xs font-mono text-zinc-400 hover:text-zinc-600 flex items-center justify-center gap-1 border-t border-zinc-100">
          {expanded ? <><ChevronUp className="w-3 h-3" /> Réduire</> : <><ChevronDown className="w-3 h-3" /> Voir tout ({listings.length})</>}
        </button>
      )}
    </div>
  );
}

export default function ActiveMarketPanel({ activeMarket, marketData }) {
  if (!activeMarket) return null;

  const { spread, tension, market_coefficient, castorus, transaction_estimate, listings_sample, listings_count } = activeMarket;
  const hasData = listings_count > 0 || castorus || (spread && spread.spread_source !== "estimation_defaut");

  return (
    <div className="space-y-6" data-testid="active-market-panel">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-1">Analyse du marché actif</p>
        <p className="text-sm text-zinc-500 leading-relaxed max-w-2xl">
          Croisement des données DVF (transactions réelles) avec les annonces en cours.
          Le coefficient marché ajuste l'estimation pour refléter les conditions actuelles.
        </p>
      </div>

      {/* Key metrics row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-px bg-zinc-200">
        <div className="bg-white p-5">
          <p className="text-[10px] text-zinc-400 font-mono uppercase mb-1">Coefficient marché</p>
          <p className="font-heading font-bold text-2xl tracking-tight">
            {market_coefficient ? `×${market_coefficient.coefficient.toFixed(3)}` : "×1.000"}
          </p>
          <p className="text-xs text-zinc-500 mt-1">
            {market_coefficient?.explanation || "Aucune donnée d'annonces"}
          </p>
        </div>
        <div className="bg-white p-5">
          <p className="text-[10px] text-zinc-400 font-mono uppercase mb-1">Annonces actives</p>
          <p className="font-heading font-bold text-2xl tracking-tight">{listings_count || 0}</p>
          <p className="text-xs text-zinc-500 mt-1">
            {listings_count > 0 ? `${listings_count} biens comparables en vente` : "Aucune annonce trouvée"}
          </p>
        </div>
        <div className="bg-white p-5">
          <p className="text-[10px] text-zinc-400 font-mono uppercase mb-1">Marge de négociation</p>
          <p className="font-heading font-bold text-2xl tracking-tight text-[#008A00]">
            {tension?.negotiation_margin_pct || "5-8%"}
          </p>
          <p className="text-xs text-zinc-500 mt-1">Estimation basée sur la tension locale</p>
        </div>
      </div>

      {/* Tension gauge */}
      {tension && (
        <div className="border border-zinc-200 p-5">
          <TensionGauge score={tension.score} label={tension.label} />
          <p className="text-xs text-zinc-500 mt-3 leading-relaxed">{tension.detail}</p>
          {tension.stock_flow_ratio !== null && tension.stock_flow_ratio !== undefined && (
            <div className="flex gap-6 mt-3 pt-3 border-t border-zinc-100">
              <div>
                <span className="text-[10px] text-zinc-400 font-mono">Stock/Flux</span>
                <span className="ml-2 font-mono text-sm font-bold">{tension.stock_flow_ratio}</span>
              </div>
              <div>
                <span className="text-[10px] text-zinc-400 font-mono">Annonces</span>
                <span className="ml-2 font-mono text-sm font-bold">{tension.num_active_listings}</span>
              </div>
              <div>
                <span className="text-[10px] text-zinc-400 font-mono">Transactions DVF</span>
                <span className="ml-2 font-mono text-sm font-bold">{tension.num_transactions_dvf}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Spread */}
      <SpreadCard spread={spread} />

      {/* Transaction estimate (if asking price provided) */}
      <TransactionEstimate estimate={transaction_estimate} />

      {/* Castorus data */}
      <CastorusData castorus={castorus} />

      {/* Market coefficient details */}
      {market_coefficient?.details?.length > 0 && (
        <div className="border border-zinc-200 p-5" data-testid="market-coeff-details">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
              Facteurs d'ajustement (annonce spécifique)
            </span>
          </div>
          <div className="space-y-2">
            {market_coefficient.details.map((d, i) => (
              <p key={i} className="text-sm text-zinc-600 flex items-start gap-2">
                <span className="text-amber-500 font-bold mt-0.5">!</span> {d}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Active listings sample */}
      <ListingsSample listings={listings_sample} />

      {/* Manual Castorus fallback info */}
      {!castorus && (
        <div className="bg-zinc-50 border border-zinc-200 p-4" data-testid="castorus-hint">
          <p className="text-xs text-zinc-500 leading-relaxed">
            <strong className="text-zinc-700">Enrichissez l'analyse :</strong> collez l'URL SeLoger/BienIci de l'annonce dans le formulaire (champ "URL de l'annonce") pour récupérer l'historique Castorus (baisses de prix, durée de mise en vente). Vous pouvez aussi saisir manuellement les données via le champ "Données Castorus".
          </p>
        </div>
      )}
    </div>
  );
}
