import { AlertTriangle, Info, AlertCircle, Zap } from "lucide-react";

const DPE_COLORS = {
  A: "#008A00", B: "#4CAF50", C: "#8BC34A", D: "#FFC107", E: "#FF9800", F: "#FF5722", G: "#E60000"
};

const DPE_LABELS = {
  A: "Excellent", B: "Très bon", C: "Bon", D: "Moyen", E: "Médiocre", F: "Passoire", G: "Passoire critique"
};

function RiskBadge({ level }) {
  const styles = {
    critical: "bg-red-50 text-red-700 border-red-200",
    warning: "bg-amber-50 text-amber-700 border-amber-200",
    info: "bg-blue-50 text-blue-700 border-blue-200",
  };
  const icons = {
    critical: AlertCircle,
    warning: AlertTriangle,
    info: Info,
  };
  const Icon = icons[level] || Info;
  return (
    <div className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium border ${styles[level] || styles.info}`}>
      <Icon className="w-3 h-3" /> {level === "critical" ? "Critique" : level === "warning" ? "Attention" : "Info"}
    </div>
  );
}

export default function RiskPanel({ risks, dpe }) {
  return (
    <div data-testid="risk-panel">
      <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-4">Analyse de risques</p>

      {/* DPE display */}
      {dpe && (
        <div className="border border-zinc-200 p-6 mb-6" data-testid="dpe-display">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-1">Diagnostic de Performance Énergétique</p>
              <p className="text-sm text-zinc-500">{DPE_LABELS[dpe] || "Non renseigné"}</p>
            </div>
            <div className="flex items-center gap-1">
              <Zap className="w-4 h-4" style={{ color: DPE_COLORS[dpe] }} />
              <span className="font-heading font-bold text-2xl" style={{ color: DPE_COLORS[dpe] }}>{dpe}</span>
            </div>
          </div>
          <div className="flex gap-0.5">
            {["A","B","C","D","E","F","G"].map(c => (
              <div
                key={c}
                className={`flex-1 h-8 flex items-center justify-center text-xs font-bold transition-all ${c === dpe ? "ring-2 ring-black scale-110 z-10" : "opacity-60"}`}
                style={{ backgroundColor: DPE_COLORS[c], color: c === "D" || c === "E" ? "#000" : "#fff" }}
              >
                {c}
              </div>
            ))}
          </div>
          {(dpe === "F" || dpe === "G") && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200">
              <p className="text-xs text-red-700 font-medium">
                Loi Climat : ce bien est classé passoire énergétique. Interdiction progressive de location.
                {dpe === "G" && " Les logements classés G sont interdits à la location depuis 2025."}
                {dpe === "F" && " Les logements classés F seront interdits à la location à partir de 2028."}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Risk list */}
      {risks.length > 0 ? (
        <div className="space-y-px bg-zinc-200">
          {risks.map((risk, i) => (
            <div key={i} className="bg-white p-5 animate-fade-in-up" style={{ animationDelay: `${i * 0.06}s` }} data-testid={`risk-item-${i}`}>
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
      ) : (
        <div className="border border-zinc-200 p-8 text-center" data-testid="no-risks">
          <Info className="w-6 h-6 text-zinc-300 mx-auto mb-3" />
          <p className="text-sm text-zinc-500">Aucun risque majeur identifié pour ce bien.</p>
        </div>
      )}
    </div>
  );
}
