import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";

function formatPrice(n) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

export default function WaterfallChart({ adjustments, basePrice, finalPrice }) {
  // Build waterfall data
  const data = [{ name: "Prix médian rue", value: basePrice, total: basePrice, type: "base" }];
  let running = basePrice;

  adjustments.forEach((adj) => {
    let delta = 0;
    if (adj.type === "pct") {
      delta = basePrice * adj.value / 100;
    } else if (adj.type === "flat") {
      delta = adj.value / 50; // normalize flat to per sqm approximation
    } else if (adj.type === "flat_per_sqm") {
      delta = adj.value;
    }
    running += delta;
    data.push({
      name: adj.name,
      value: Math.round(delta),
      total: Math.round(running),
      type: delta >= 0 ? "positive" : "negative",
      detail: adj.detail,
      pct: adj.type === "pct" ? adj.value : null,
    });
  });

  data.push({ name: "Prix estimé/m²", value: Math.round(finalPrice), total: Math.round(finalPrice), type: "result" });

  const getColor = (type) => {
    if (type === "base") return "#18181B";
    if (type === "positive") return "#008A00";
    if (type === "negative") return "#E60000";
    if (type === "result") return "#0022EE";
    return "#71717A";
  };

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="bg-white border border-zinc-200 p-3 shadow-sm">
        <p className="font-heading font-bold text-sm mb-1">{d.name}</p>
        {d.detail && <p className="text-xs text-zinc-500 mb-1">{d.detail}</p>}
        <p className="font-mono text-sm">
          {d.type === "positive" && "+"}{d.type === "negative" && ""}{formatPrice(d.value)} €/m²
          {d.pct !== null && <span className="text-zinc-400 ml-1">({d.pct > 0 ? "+" : ""}{d.pct}%)</span>}
        </p>
      </div>
    );
  };

  return (
    <div data-testid="waterfall-chart">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-1">Décomposition du prix au m²</p>
          <p className="text-sm text-zinc-500">Chaque barre montre l'impact d'un critère sur le prix de référence.</p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-[#008A00]" /> Surcote</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-[#E60000]" /> Décote</span>
        </div>
      </div>
      <div className="border border-zinc-200 p-4">
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10, fontFamily: "IBM Plex Sans" }}
                angle={-30}
                textAnchor="end"
                height={60}
              />
              <YAxis
                tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
                tickFormatter={(v) => `${formatPrice(v)}`}
                domain={["dataMin - 500", "dataMax + 500"]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="total" radius={[2, 2, 0, 0]}>
                {data.map((entry, i) => (
                  <Cell key={i} fill={getColor(entry.type)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Adjustment table */}
      <div className="mt-6 border border-zinc-200">
        <div className="px-4 py-2 bg-zinc-50 border-b border-zinc-200">
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-mono">Détail des ajustements</p>
        </div>
        <div className="divide-y divide-zinc-100">
          {adjustments.map((adj, i) => (
            <div key={i} className="px-4 py-3 flex items-center justify-between hover:bg-zinc-50 transition-colors" data-testid={`adjustment-${i}`}>
              <div>
                <p className="text-sm font-medium">{adj.name}</p>
                <p className="text-xs text-zinc-400">{adj.detail}</p>
              </div>
              <span className={`font-mono text-sm font-medium ${adj.value > 0 ? "text-[#008A00]" : adj.value < 0 ? "text-[#E60000]" : "text-zinc-400"}`}>
                {adj.value > 0 ? "+" : ""}{adj.value}{adj.type === "pct" ? "%" : adj.type === "flat" ? " €" : " €/m²"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
