import { AlertTriangle, TrendingDown, Wallet, Building2, Ruler, ArrowDown, ArrowUp } from "lucide-react";

function formatPrice(n) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

function InsightCard({ icon: Icon, title, value, detail, sentiment }) {
  const sentimentColors = {
    positive: "border-l-[#008A00]",
    negative: "border-l-[#E60000]",
    neutral: "border-l-zinc-300",
    warning: "border-l-amber-400",
  };
  return (
    <div className={`border border-zinc-200 border-l-4 ${sentimentColors[sentiment] || sentimentColors.neutral} bg-white p-4`}>
      <div className="flex items-start gap-3">
        <Icon className="w-4 h-4 text-zinc-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-xs text-zinc-400 font-mono uppercase tracking-wider mb-1">{title}</p>
          <p className="font-heading font-bold text-lg tracking-tight">{value}</p>
          <p className="text-xs text-zinc-500 mt-1 leading-relaxed">{detail}</p>
        </div>
      </div>
    </div>
  );
}

export default function ExpertInsights({ data }) {
  if (!data) return null;

  const req = data.request || {};
  const chars = req.characteristics || {};
  const cond = req.condition || {};
  const bldg = req.building || {};
  const legal = req.legal || {};
  const surface = chars.surface_carrez || 1;
  const priceSqm = data.price_per_sqm_median || 0;
  const totalPrice = data.price_median || 0;

  const insights = [];

  // 1. Price per room
  const rooms = chars.rooms || 1;
  const pricePerRoom = Math.round(totalPrice / rooms);
  const avgPricePerRoom = priceSqm * 28; // ~28m² avg per room in Paris
  const roomDiff = ((pricePerRoom - avgPricePerRoom) / avgPricePerRoom * 100).toFixed(0);
  insights.push({
    icon: Ruler,
    title: "Prix par pièce",
    value: `${formatPrice(pricePerRoom)} € / pièce`,
    detail: `Pour un T${rooms} de ${surface}m², soit ${(surface / rooms).toFixed(1)}m² par pièce. ${surface / rooms > 30 ? "Pièces spacieuses, bon ratio." : surface / rooms > 20 ? "Surface par pièce standard." : "Pièces compactes, typique de Paris."}`,
    sentiment: surface / rooms > 25 ? "positive" : "neutral",
  });

  // 2. Charges analysis
  const annualCharges = bldg.annual_charges || 0;
  if (annualCharges > 0) {
    const chargesPerSqm = annualCharges / surface;
    const chargesMonthly = Math.round(annualCharges / 12);
    let chargesSentiment = "neutral";
    let chargesComment = "Charges dans la moyenne parisienne.";
    if (chargesPerSqm > 50) {
      chargesSentiment = "warning";
      chargesComment = `Charges élevées (${chargesPerSqm.toFixed(0)}€/m²/an). Vérifier : chauffage collectif, gardien, ascenseur, travaux votés. La moyenne parisienne est autour de 30-40€/m²/an.`;
    } else if (chargesPerSqm > 35) {
      chargesComment = `Charges dans la fourchette haute (${chargesPerSqm.toFixed(0)}€/m²/an). Acceptable si l'immeuble a un gardien et/ou un chauffage collectif.`;
    } else if (chargesPerSqm < 20) {
      chargesSentiment = "positive";
      chargesComment = `Charges faibles (${chargesPerSqm.toFixed(0)}€/m²/an). Bon signe : copropriété bien gérée ou charges minimales.`;
    }
    insights.push({
      icon: Wallet,
      title: "Charges de copropriété",
      value: `${formatPrice(chargesMonthly)} € / mois`,
      detail: chargesComment,
      sentiment: chargesSentiment,
    });
  }

  // 3. Negotiation margin estimate
  const marketPos = data.market_data?.market_position;
  if (marketPos) {
    let margin = "3 à 5%";
    let marginDetail = "";
    if (marketPos.diff_pct > 10) {
      margin = "5 à 10%";
      marginDetail = "Le bien est significativement au-dessus du marché. La marge de négociation est plus large — les vendeurs de biens surcotés sont souvent plus flexibles après quelques semaines sur le marché.";
    } else if (marketPos.diff_pct > 0) {
      margin = "3 à 7%";
      marginDetail = "Le bien est légèrement au-dessus du marché. Négociez entre 3 et 7%, en vous appuyant sur les comparables DVF de la rue.";
    } else if (marketPos.diff_pct > -5) {
      margin = "2 à 5%";
      marginDetail = "Le bien est dans la moyenne du marché. La marge de négociation est standard (2 à 5%). Appuyez-vous sur les défauts identifiés (DPE, travaux, vis-à-vis).";
    } else {
      margin = "0 à 3%";
      marginDetail = "Le bien est déjà en-dessous du marché. La marge de négociation est faible — le prix semble déjà ajusté. Risque de surenchère si le bien est attractif.";
    }
    insights.push({
      icon: TrendingDown,
      title: "Marge de négociation estimée",
      value: margin,
      detail: marginDetail,
      sentiment: marketPos.diff_pct > 5 ? "positive" : "neutral",
    });
  }

  // 4. Renovation cost if applicable
  if (cond.general_state === "a_renover" || cond.general_state === "rafraichissement") {
    const lowCost = cond.general_state === "a_renover" ? 800 : 200;
    const highCost = cond.general_state === "a_renover" ? 1800 : 600;
    insights.push({
      icon: Building2,
      title: "Budget travaux estimé",
      value: `${formatPrice(lowCost * surface)} — ${formatPrice(highCost * surface)} €`,
      detail: `Sur ${surface}m², soit ${lowCost} à ${highCost}€/m². ${cond.general_state === "a_renover" ? "Rénovation complète : électricité, plomberie, sols, cuisine, salle de bain, peinture. Prévoir 3 à 6 mois de travaux." : "Rafraîchissement : peintures, sols, petits ajustements. 1 à 2 mois de travaux."}`,
      sentiment: "warning",
    });
  }

  // 5. DPE cost impact
  if (cond.dpe && ["E", "F", "G"].includes(cond.dpe)) {
    const renovCost = cond.dpe === "G" ? { low: 500, high: 1500 } : cond.dpe === "F" ? { low: 300, high: 900 } : { low: 150, high: 500 };
    insights.push({
      icon: AlertTriangle,
      title: "Coût rénovation énergétique",
      value: `${formatPrice(renovCost.low * surface)} — ${formatPrice(renovCost.high * surface)} €`,
      detail: `Pour passer de la classe ${cond.dpe} à C/D. ${cond.dpe === "G" ? "Isolation complète (murs, combles, fenêtres) + changement chauffage obligatoire." : cond.dpe === "F" ? "Isolation + remplacement menuiseries nécessaires. Interdit à la location en 2028." : "Améliorations ciblées : isolation partielle, menuiseries."} Pensez aux aides (MaPrimeRénov', CEE).`,
      sentiment: "negative",
    });
  }

  // 6. Total cost of ownership (5 years)
  const taxe = legal.property_tax || 800;
  const charges5y = annualCharges * 5;
  const taxe5y = taxe * 5;
  const totalOwnership5y = totalPrice + charges5y + taxe5y;
  insights.push({
    icon: Wallet,
    title: "Coût de détention sur 5 ans",
    value: formatPrice(totalOwnership5y) + " €",
    detail: `Prix d'achat (${formatPrice(totalPrice)}) + charges (${formatPrice(charges5y)}) + taxe foncière (${formatPrice(taxe5y)}). Hors frais de notaire, crédit et travaux. Utilisez le simulateur pour le coût total.`,
    sentiment: "neutral",
  });

  return (
    <div data-testid="expert-insights">
      <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-1">Analyse expert</p>
      <p className="text-sm text-zinc-500 mb-6">
        Indicateurs avancés pour acheteurs expérimentés : ratio prix/pièce, charges, marge de négociation, coûts cachés.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {insights.map((ins, i) => (
          <InsightCard key={i} {...ins} />
        ))}
      </div>
    </div>
  );
}
