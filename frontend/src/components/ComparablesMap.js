import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

function formatPrice(n) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

function MapAutoCenter({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.setView(center, 15);
    }
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
    } catch {
      return;
    }
    const points = comparables
      .filter(c => c.latitude && c.longitude)
      .map(c => [c.latitude, c.longitude, c.price_per_sqm / 100]);
    if (!points.length) return;
    const heat = L.heatLayer(points, {
      radius: 30,
      blur: 25,
      maxZoom: 17,
      max: Math.max(...comparables.map(c => c.price_per_sqm)) / 100,
      gradient: { 0.2: "#008A00", 0.5: "#FFC107", 0.8: "#FF6B00", 1: "#E60000" },
    }).addTo(map);
    return () => { map.removeLayer(heat); };
  }, [comparables, map]);
  return null;
}

export default function ComparablesMap({ comparables, center, estimatedPrice, searchRadius }) {
  const getColor = (priceSqm) => {
    if (!estimatedPrice) return "#71717A";
    const diff = ((priceSqm - estimatedPrice) / estimatedPrice) * 100;
    if (diff > 5) return "#E60000";
    if (diff < -5) return "#008A00";
    return "#18181B";
  };

  const radiusM = searchRadius || 500;

  return (
    <div data-testid="comparables-map">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-1">Carte des comparables</p>
          <p className="text-sm text-zinc-500">
            {comparables.length} transactions DVF — rayon de {radiusM}m — médiane pondérée (distance + fraîcheur)
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#008A00]" /> Moins cher</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#18181B]" /> Similaire</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#E60000]" /> Plus cher</span>
        </div>
      </div>
      <div className="border border-zinc-200 h-[400px]">
        <MapContainer
          center={center}
          zoom={15}
          style={{ height: "100%", width: "100%" }}
          scrollWheelZoom={true}
        >
          <MapAutoCenter center={center} />
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />
          <HeatmapLayer comparables={comparables} />
          {/* Search radius circle */}
          <Circle
            center={center}
            radius={radiusM}
            pathOptions={{ color: "#18181B", weight: 1, dashArray: "6 4", fillOpacity: 0.03 }}
          />
          {comparables.map((c, i) => (
            <CircleMarker
              key={i}
              center={[c.latitude || center[0], c.longitude || center[1]]}
              radius={6}
              fillColor={getColor(c.price_per_sqm)}
              color="#fff"
              weight={1.5}
              opacity={1}
              fillOpacity={0.85}
            >
              <Popup>
                <div className="text-xs space-y-1 min-w-[160px]">
                  <p className="font-bold">{c.address}</p>
                  <p className="font-mono">{formatPrice(c.price)} €</p>
                  <p>{c.surface} m² — {formatPrice(c.price_per_sqm)} €/m²</p>
                  <p className="text-zinc-400">{c.rooms} pièces — {c.date}</p>
                  {c.distance_m !== undefined && <p className="text-zinc-400">Distance : {c.distance_m}m</p>}
                </div>
              </Popup>
            </CircleMarker>
          ))}
          {/* Center marker for the property */}
          <CircleMarker
            center={center}
            radius={10}
            fillColor="#0022EE"
            color="#fff"
            weight={2}
            opacity={1}
            fillOpacity={1}
          >
            <Popup><div className="text-xs font-bold">Votre bien</div></Popup>
          </CircleMarker>
        </MapContainer>
      </div>

      {/* Comparables table */}
      {comparables.length > 0 && (
        <div className="mt-6 border border-zinc-200">
          <div className="px-4 py-2 bg-zinc-50 border-b border-zinc-200">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-mono">Transactions comparables</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200">
                  <th className="text-left px-4 py-2 text-xs font-mono text-zinc-400 font-medium">Adresse</th>
                  <th className="text-right px-4 py-2 text-xs font-mono text-zinc-400 font-medium">Dist.</th>
                  <th className="text-right px-4 py-2 text-xs font-mono text-zinc-400 font-medium">Date</th>
                  <th className="text-right px-4 py-2 text-xs font-mono text-zinc-400 font-medium">Prix</th>
                  <th className="text-right px-4 py-2 text-xs font-mono text-zinc-400 font-medium">Surface</th>
                  <th className="text-right px-4 py-2 text-xs font-mono text-zinc-400 font-medium">€/m²</th>
                </tr>
              </thead>
              <tbody>
                {comparables.slice(0, 20).map((c, i) => (
                  <tr key={i} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50" data-testid={`comparable-row-${i}`}>
                    <td className="px-4 py-2.5 text-sm">{c.address}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-zinc-500">{c.distance_m !== undefined ? `${c.distance_m}m` : "—"}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-zinc-500">{c.date}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono">{formatPrice(c.price)} €</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono">{c.surface} m²</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono font-medium" style={{ color: getColor(c.price_per_sqm) }}>
                      {formatPrice(c.price_per_sqm)} €
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
