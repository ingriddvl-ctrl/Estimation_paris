import { TrendingUp, TrendingDown, Minus, ArrowUpRight, ArrowDownRight } from "lucide-react";

function formatPrice(n) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

const POSITION_CONFIG = {
  "++": { color: "#008A00", bg: "#f0fdf4", border: "#bbf7d0", icon: TrendingUp, label: "Nettement au-dessus" },
  "+":  { color: "#008A00", bg: "#f0fdf4", border: "#bbf7d0", icon: ArrowUpRight, label: "Au-dessus" },
  "=":  { color: "#18181B", bg: "#f4f4f5", border: "#e4e4e7", icon: Minus, label: "Dans la moyenne" },
  "-":  { color: "#E60000", bg: "#fef2f2", border: "#fecaca", icon: ArrowDownRight, label: "En-dessous" },
  "--": { color: "#E60000", bg: "#fef2f2", border: "#fecaca", icon: TrendingDown, label: "Nettement en-dessous" },
};

export default function MarketPosition({ position, surface, totalPrice }) {
  if (!position) return null;

  const config = POSITION_CONFIG[position.label] || POSITION_CONFIG["="];
  const Icon = config.icon;
  const pricePerRoom = totalPrice && surface ? Math.round(totalPrice / Math.max(surface / 25, 1)) : null;

  return (
    <div data-testid="market-position">
      {/* Main position badge */}
      <div className="border border-zinc-200 p-6 mb-4" data-testid="position-badge">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-2">Position marché</p>
            <p className="text-sm text-zinc-600 mb-1">{position.description}</p>
            <p className="text-xs text-zinc-400 font-mono">
              {formatPrice(position.estimated_sqm)} €/m² estimé vs {formatPrice(position.arr_avg)} €/m² moyenne arr.
            </p>
          </div>
          <div
            className="flex items-center gap-3 px-5 py-3 border"
            style={{ backgroundColor: config.bg, borderColor: config.border }}
          >
            <Icon className="w-5 h-5" style={{ color: config.color }} />
            <div>
              <p className="font-heading font-bold text-3xl tracking-tight" style={{ color: config.color }} data-testid="position-label">
                {position.label}
              </p>
              <p className="text-xs font-mono" style={{ color: config.color }}>
                {position.diff_pct > 0 ? "+" : ""}{position.diff_pct}% vs arr.
              </p>
            </div>
          </div>
        </div>

        {/* Visual bar */}
        <div className="mt-5">
          <div className="relative h-8 bg-zinc-100">
            {/* Scale markers */}
            <div className="absolute inset-0 flex">
              <div className="flex-1 border-r border-zinc-200" />
              <div className="flex-1 border-r border-zinc-200" />
              <div className="flex-1 border-r border-zinc-300 bg-zinc-50" />
              <div className="flex-1 border-r border-zinc-200" />
              <div className="flex-1" />
            </div>
            <div className="absolute bottom-0 left-0 right-0 flex justify-between px-1 text-[9px] font-mono text-zinc-400">
              <span>--</span><span>-</span><span>=</span><span>+</span><span>++</span>
            </div>
            {/* Position indicator */}
            <div
              className="absolute top-0 bottom-0 w-1 transition-all duration-700"
              style={{
                left: `${Math.min(95, Math.max(5, 50 + position.diff_pct * 1.5))}%`,
                backgroundColor: config.color,
              }}
            >
              <div className="absolute -top-1 -left-1.5 w-4 h-4 rounded-full border-2 border-white" style={{ backgroundColor: config.color }} />
            </div>
          </div>
        </div>
      </div>

      {/* Quick insights */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-px bg-zinc-200" data-testid="position-insights">
        <div className="bg-white p-4">
          <p className="text-xs text-zinc-400 font-mono mb-1">Votre bien</p>
          <p className="font-mono font-bold text-lg">{formatPrice(position.estimated_sqm)} <span className="text-xs text-zinc-400">€/m²</span></p>
        </div>
        <div className="bg-white p-4">
          <p className="text-xs text-zinc-400 font-mono mb-1">Moy. arrondissement</p>
          <p className="font-mono font-bold text-lg">{formatPrice(position.arr_avg)} <span className="text-xs text-zinc-400">€/m²</span></p>
        </div>
        <div className="bg-white p-4">
          <p className="text-xs text-zinc-400 font-mono mb-1">Écart</p>
          <p className="font-mono font-bold text-lg" style={{ color: config.color }}>
            {position.diff_pct > 0 ? "+" : ""}{position.diff_pct}%
            <span className="text-xs text-zinc-400 ml-1">
              ({position.diff_pct > 0 ? "+" : ""}{formatPrice(position.estimated_sqm - position.arr_avg)} €/m²)
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
