import { useState } from "react";
import { AlertTriangle, Info, AlertCircle, Zap, TrendingUp, TrendingDown, Calendar, ChevronDown, ChevronUp, Banknote, Shield } from "lucide-react";

const DPE_COLORS = {
  A: "#008A00", B: "#4CAF50", C: "#8BC34A", D: "#FFC107", E: "#FF9800", F: "#FF5722", G: "#E60000"
};
const DPE_LABELS = {
  A: "Excellent", B: "Très bon", C: "Bon", D: "Moyen", E: "Médiocre", F: "Passoire", G: "Passoire critique"
};

function fmt(n) {
  if (!n && n !== 0) return "—";
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

function RiskBadge({ level }) {
  const styles = {
    critical: "bg-red-50 text-red-700 border-red-200",
    warning: "bg-amber-50 text-amber-700 border-amber-200",
    info: "bg-blue-50 text-blue-700 border-blue-200",
  };
  const icons = { critical: AlertCircle, warning: AlertTriangle, info: Info };
  const Icon = icons[level] || Info;
  return (
    <div className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium border ${styles[level] || styles.info}`}>
      <Icon className="w-3 h-3" /> {level === "critical" ? "Critique" : level === "warning" ? "Attention" : "Info"}
    </div>
  );
}

export default function RiskPanel({ risks = [], dpe, currentPrice = 0, surface = 0, charges = 0, taxeFonciere = 0 }) {
  const [showProjections, setShowProjections] = useState(false);
  const price = currentPrice || 0;
  const notaryFees = Math.round(price * 0.075);
  const renovCostMap = { A: 0, B: 0, C: 0, D: 0, E: 300, F: 600, G: 1000 };
  const renovCost = Math.round((renovCostMap[dpe] || 0) * (surface || 70));
  const totalAcquisition = price + notaryFees + renovCost;
  const annualCharges = (charges || 0) + (taxeFonciere || 0);

  const scenarios = [
    {
      name: "Optimiste", color: "#008A00",
      desc: "Baisse des taux vers 2.5%, reprise de la demande",
      hypotheses: "Taux BCE en baisse vers 2%, taux immobiliers \u00e0 2.5% sur 20 ans, croissance PIB +1.5%, ch\u00f4mage stable, reprise des transactions (+15%), retour des investisseurs institutionnels, r\u00e9formes fiscales favorables.",
      rates: { 5: 12, 7: 18, 10: 28, 12: 35 }
    },
    {
      name: "Central", color: "#F59E0B",
      desc: "Taux stables 3-3.5%, reprise mod\u00e9r\u00e9e",
      hypotheses: "Taux BCE stables \u00e0 3%, taux immobiliers 3-3.5%, croissance molle +0.8%, march\u00e9 s\u00e9lectif (bons DPE OK, passoires en baisse), volumes en l\u00e9g\u00e8re hausse, prix stables puis +2-3%/an \u00e0 partir de 2027.",
      rates: { 5: 4, 7: 7, 10: 12, 12: 16 }
    },
    {
      name: "Pessimiste", color: "#E60000",
      desc: "Taux en hausse, r\u00e9cession, correction prolong\u00e9e",
      hypotheses: "OAT 10 ans en hausse (tensions g\u00e9opolitiques, d\u00e9ficit public), taux immobiliers repassent au-dessus de 4%, r\u00e9cession europ\u00e9enne, ch\u00f4mage en hausse, volumes en chute (-20%), prix en baisse sur Paris de -5 \u00e0 -10% suppl\u00e9mentaires.",
      rates: { 5: -6, 7: -8, 10: -5, 12: -2 }
    },
  ];

  const dpeMalus = { A: 2, B: 1, C: 0, D: 0, E: -1, F: -4, G: -8 };
  const malus = dpeMalus[dpe] || 0;

  const marketFactors = [
    { label: "Correction depuis 2022", value: "-10 à -15%", detail: "Les prix ont reculé après le pic, correction la plus importante depuis 2008", dot: "bg-red-500" },
    { label: "Taux d'intérêt", value: "3.0 – 3.5%", detail: "Stabilisés après le pic de 4.5% fin 2023, la BCE a amorcé une détente", dot: "bg-amber-500" },
    { label: "Marge de négociation", value: "5 – 8%", detail: "Marché acheteur en 2026, rapport de force favorable aux acquéreurs", dot: "bg-amber-500" },
    { label: "Volume de transactions", value: "-25%", detail: "Par rapport au pic 2022, mais en reprise de +8% vs 2024", dot: "bg-amber-500" },
    { label: "DPE F-G", value: "Décote -10 à -20%", detail: "Interdiction de location G depuis 2025, F à partir de 2028", dot: "bg-red-500" },
    { label: "Perspectives 2026-2027", value: "Stabilisation", detail: "Reprise modérée attendue de +2-3% en 2027 si les taux restent stables", dot: "bg-green-500" },
  ];

  return (
    <div data-testid="risk-panel" className="space-y-6">
      <p className="text-xs uppercase tracking-widest text-zinc-400 font-mono">Analyse complète — Risques & Projections</p>

      {/* ── DPE ── */}
      {dpe && (
        <div className="border border-zinc-200 p-6" data-testid="dpe-display">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs uppercase tracking-widest text-zinc-400 font-mono mb-1">Diagnostic de Performance Énergétique</p>
              <p className="text-sm text-zinc-500">{DPE_LABELS[dpe] || "Non renseigné"}</p>
            </div>
            <div className="flex items-center gap-1">
              <Zap className="w-4 h-4" style={{ color: DPE_COLORS[dpe] }} />
              <span className="font-bold text-2xl" style={{ color: DPE_COLORS[dpe] }}>{dpe}</span>
            </div>
          </div>
          <div className="flex gap-0.5">
            {["A","B","C","D","E","F","G"].map(c => (
              <div key={c}
                className={`flex-1 h-8 flex items-center justify-center text-xs font-bold transition-all ${c === dpe ? "ring-2 ring-black scale-110 z-10" : "opacity-60"}`}
                style={{ backgroundColor: DPE_COLORS[c], color: c === "D" || c === "E" ? "#000" : "#fff" }}
              >{c}</div>
            ))}
          </div>
          {(dpe === "F" || dpe === "G") && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200">
              <p className="text-xs text-red-700 font-medium">
                Loi Climat : passoire énergétique. {dpe === "G" ? "Interdit à la location depuis 2025." : "Interdit à la location à partir de 2028."}
              </p>
            </div>
          )}
          {dpe === "E" && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200">
              <p className="text-xs text-amber-700 font-medium">
                Loi Climat : les logements classés E seront interdits à la location à partir de 2034.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── CONTEXTE MARCHÉ 2026 ── */}
      <div className="border border-zinc-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <TrendingDown className="w-5 h-5 text-zinc-400" />
          <div>
            <p className="font-semibold text-sm">Contexte marché 2026</p>
            <p className="text-xs text-zinc-500">Facteurs macroéconomiques impactant votre estimation</p>
          </div>
        </div>
        <div className="space-y-3">
          {marketFactors.map((item, i) => (
            <div key={i} className="flex items-start gap-3 py-1">
              <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${item.dot}`} />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">{item.label}</p>
                  <span className="text-xs font-mono font-bold text-zinc-600">{item.value}</span>
                </div>
                <p className="text-xs text-zinc-500 mt-0.5">{item.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── COÛT TOTAL D'ACQUISITION ── */}
      {price > 0 && (
        <div className="border border-zinc-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Banknote className="w-5 h-5 text-zinc-400" />
            <div>
              <p className="font-semibold text-sm">Coût total d'acquisition</p>
              <p className="text-xs text-zinc-500">Frais de notaire + rénovation énergétique éventuelle</p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <div className="bg-zinc-50 p-3">
              <p className="text-[10px] text-zinc-400 font-mono uppercase">Prix du bien</p>
              <p className="font-bold text-sm">{fmt(price)} €</p>
            </div>
            <div className="bg-zinc-50 p-3">
              <p className="text-[10px] text-zinc-400 font-mono uppercase">Frais de notaire (~7.5%)</p>
              <p className="font-bold text-sm">{fmt(notaryFees)} €</p>
            </div>
            {renovCost > 0 && (
              <div className="bg-red-50 p-3">
                <p className="text-[10px] text-red-500 font-mono uppercase">Rénovation DPE {dpe}</p>
                <p className="font-bold text-sm text-red-700">{fmt(renovCost)} €</p>
              </div>
            )}
            <div className="bg-emerald-50 p-3">
              <p className="text-[10px] text-emerald-600 font-mono uppercase">Total acquisition</p>
              <p className="font-bold text-lg text-emerald-700">{fmt(totalAcquisition)} €</p>
            </div>
          </div>
          {annualCharges > 0 && (
            <p className="text-xs text-zinc-500 border-t border-zinc-100 pt-3">
              Charges récurrentes : <strong>{fmt(annualCharges)} €/an</strong> ({fmt(Math.round(annualCharges / 12))} €/mois) — charges copro + taxe foncière
            </p>
          )}
        </div>
      )}

      {/* ── PROJECTIONS 5/7/10/12 ANS ── */}
      {price > 0 && (
        <div className="border border-zinc-200">
          <button
            onClick={() => setShowProjections(!showProjections)}
            className="w-full flex items-center justify-between p-5 bg-zinc-50 hover:bg-zinc-100 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-zinc-400" />
              <div className="text-left">
                <p className="font-semibold text-sm">Projections à 5, 7, 10 et 12 ans</p>
                <p className="text-xs text-zinc-500">3 scénarios basés sur l'analyse du marché 2026</p>
              </div>
            </div>
            {showProjections ? <ChevronUp className="w-5 h-5 text-zinc-400" /> : <ChevronDown className="w-5 h-5 text-zinc-400" />}
          </button>

          {showProjections && (
            <div className="p-5 space-y-5">
              <div className="bg-zinc-50 p-4">
                <p className="text-xs text-zinc-500 mb-1">Prix actuel estimé</p>
                <p className="text-2xl font-bold">{fmt(price)} €</p>
              </div>

              {scenarios.map((sc) => (
                <div key={sc.name} className="border border-zinc-200">
                  <div className="px-4 py-3 flex items-center gap-2 border-b" style={{ borderBottomColor: sc.color }}>
                    {sc.rates[5] >= 0
                      ? <TrendingUp className="w-4 h-4" style={{ color: sc.color }} />
                      : <TrendingDown className="w-4 h-4" style={{ color: sc.color }} />}
                    <span className="font-semibold text-sm" style={{ color: sc.color }}>{sc.name}</span>
                    <span className="text-xs text-zinc-500 ml-auto hidden sm:inline">{sc.desc}</span>
                  </div>
                  <div className="px-4 py-2 bg-zinc-50 border-b border-zinc-100">
                    <p className="text-xs text-zinc-500"><strong>Hypothèses :</strong> {sc.hypotheses}</p>
                  </div>
                  <div className="grid grid-cols-4 gap-0">
                    {[5, 7, 10, 12].map((y) => {
                      const rate = (sc.rates[y] + malus * (y / 10)) / 100;
                      const projected = Math.round(price * (1 + rate));
                      const gain = projected - price;
                      const ratePct = Math.round(rate * 1000) / 10;
                      return (
                        <div key={y} className="p-3 text-center border-r last:border-r-0 border-zinc-100">
                          <p className="text-xs text-zinc-400 font-mono mb-1">{y} ans</p>
                          <p className="text-sm sm:text-base font-bold">{fmt(projected)} €</p>
                          <p className="text-xs font-mono mt-1" style={{ color: gain >= 0 ? "#008A00" : "#E60000" }}>
                            {gain >= 0 ? "+" : ""}{fmt(gain)} €
                          </p>
                          <p className="text-[10px] text-zinc-400">{gain >= 0 ? "+" : ""}{ratePct}%</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}

              <div className="bg-amber-50 border border-amber-200 p-3">
                <p className="text-xs text-amber-800">
                  <strong>Avertissement :</strong> Ces projections sont indicatives. Le DPE influence fortement la projection (les passoires F-G risquent de perdre de la valeur sans rénovation). Projections hors inflation et travaux.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── RISQUES IDENTIFIÉS ── */}
      {risks.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-widest text-zinc-400 font-mono mb-3">Risques identifiés</p>
          <div className="space-y-px bg-zinc-200">
            {risks.map((risk, i) => (
              <div key={i} className="bg-white p-5" data-testid={`risk-item-${i}`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium mb-1">{risk.type}</p>
                    <p className="text-xs text-zinc-500">{risk.detail}</p>
                    {risk.source && <p className="text-xs text-zinc-400 mt-1 font-mono">Source : {risk.source}</p>}
                  </div>
                  <RiskBadge level={risk.level} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {risks.length === 0 && (
        <div className="border border-zinc-200 p-8 text-center" data-testid="no-risks">
          <Shield className="w-6 h-6 text-zinc-300 mx-auto mb-3" />
          <p className="text-sm text-zinc-500">Aucun risque majeur identifié pour ce bien.</p>
        </div>
      )}
    </div>
  );
}
