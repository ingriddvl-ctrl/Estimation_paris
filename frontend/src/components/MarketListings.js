import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { Loader2 } from "lucide-react";
import "leaflet/dist/leaflet.css";

function formatPrice(n) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

function MapAutoCenter({ center }) {
  const map = useMap();
  useEffect(() => { if (center[0] && center[1]) map.setView(center, 15); }, [center, map]);
  return null;
}

export default function MarketListings({ lat, lon, estimatedPriceSqm }) {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (lat && lon) {
      api.getMarketListings(lat, lon, 800)
        .then(setListings)
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [lat, lon]);

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 animate-spin text-zinc-300" /></div>;

  const getColor = (priceSqm) => {
    if (!estimatedPriceSqm) return "#71717A";
    const diff = ((priceSqm - estimatedPriceSqm) / estimatedPriceSqm) * 100;
    if (diff > 10) return "#E60000";
    if (diff < -10) return "#008A00";
    return "#18181B";
  };

  const getLabel = (priceSqm) => {
    if (!estimatedPriceSqm) return "";
    const diff = ((priceSqm - estimatedPriceSqm) / estimatedPriceSqm) * 100;
    if (diff > 10) return "++";
    if (diff > 3) return "+";
    if (diff > -3) return "=";
    if (diff > -10) return "-";
    return "--";
  };

  // Stats
  const prices = listings.filter(l => l.price_per_sqm > 0).map(l => l.price_per_sqm);
  const avgPrice = prices.length > 0 ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0;
  const minPrice = prices.length > 0 ? Math.min(...prices) : 0;
  const maxPrice = prices.length > 0 ? Math.max(...prices) : 0;

  return (
    <div data-testid="market-listings">
      <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-1">Comparables du marché</p>
      <p className="text-sm text-zinc-500 mb-6">
        Transactions récentes (2023-2025) dans un rayon de 800m. Comparez avec votre estimation.
      </p>

      {/* Stats bar */}
      {prices.length > 0 && (
        <div className="grid grid-cols-4 gap-px bg-zinc-200 mb-6" data-testid="listings-stats">
          <div className="bg-white p-4">
            <p className="text-xs text-zinc-400 font-mono mb-1">Transactions</p>
            <p className="font-heading font-bold text-xl">{listings.length}</p>
          </div>
          <div className="bg-white p-4">
            <p className="text-xs text-zinc-400 font-mono mb-1">Moyenne €/m²</p>
            <p className="font-heading font-bold text-xl">{formatPrice(avgPrice)}</p>
          </div>
          <div className="bg-white p-4">
            <p className="text-xs text-zinc-400 font-mono mb-1">Min</p>
            <p className="font-heading font-bold text-xl text-[#008A00]">{formatPrice(minPrice)}</p>
          </div>
          <div className="bg-white p-4">
            <p className="text-xs text-zinc-400 font-mono mb-1">Max</p>
            <p className="font-heading font-bold text-xl text-[#E60000]">{formatPrice(maxPrice)}</p>
          </div>
        </div>
      )}

      {/* Map */}
      {listings.length > 0 && (
        <div className="border border-zinc-200 h-[350px] mb-6">
          <MapContainer center={[lat, lon]} zoom={15} style={{ height: "100%", width: "100%" }} scrollWheelZoom={true}>
            <MapAutoCenter center={[lat, lon]} />
            <TileLayer url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" attribution='&copy; OSM' />
            {listings.map((l, i) => (
              <CircleMarker key={i} center={[l.latitude || lat, l.longitude || lon]} radius={6}
                fillColor={getColor(l.price_per_sqm)} color="#fff" weight={1.5} fillOpacity={0.85}>
                <Popup>
                  <div className="text-xs space-y-1 min-w-[180px]">
                    <p className="font-bold">{l.address}</p>
                    <p className="font-mono">{formatPrice(l.price)} € — {l.surface} m²</p>
                    <p className="font-mono font-bold">{formatPrice(l.price_per_sqm)} €/m²</p>
                    <p className="text-zinc-400">{l.date} — {l.source}</p>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
            <CircleMarker center={[lat, lon]} radius={10} fillColor="#0022EE" color="#fff" weight={2} fillOpacity={1}>
              <Popup><div className="text-xs font-bold">Votre bien</div></Popup>
            </CircleMarker>
          </MapContainer>
        </div>
      )}

      {/* Listings table */}
      {listings.length > 0 ? (
        <div className="border border-zinc-200">
          <div className="px-4 py-2 bg-zinc-50 border-b border-zinc-200">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-mono">Détail des offres / transactions récentes</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-xs font-mono text-zinc-400">
                  <th className="text-left px-4 py-2">Adresse</th>
                  <th className="text-right px-4 py-2">Date</th>
                  <th className="text-right px-4 py-2">Prix</th>
                  <th className="text-right px-4 py-2">Surface</th>
                  <th className="text-right px-4 py-2">€/m²</th>
                  <th className="text-center px-4 py-2">vs estimation</th>
                  <th className="text-center px-4 py-2">Statut</th>
                </tr>
              </thead>
              <tbody>
                {listings.map((l, i) => (
                  <tr key={i} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50" data-testid={`listing-row-${i}`}>
                    <td className="px-4 py-2.5 text-sm max-w-[200px] truncate">{l.address}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-zinc-500">{l.date}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono">{formatPrice(l.price)} €</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono">{l.surface} m²</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono font-medium" style={{ color: getColor(l.price_per_sqm) }}>
                      {formatPrice(l.price_per_sqm)} €
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="inline-block px-2 py-0.5 text-xs font-mono font-bold" style={{
                        backgroundColor: getColor(l.price_per_sqm) === "#008A00" ? "#f0fdf4" : getColor(l.price_per_sqm) === "#E60000" ? "#fef2f2" : "#f4f4f5",
                        color: getColor(l.price_per_sqm)
                      }}>
                        {getLabel(l.price_per_sqm)}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="text-xs px-2 py-0.5 bg-zinc-100 font-mono">{l.status || "vendu"}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="border border-zinc-200 p-8 text-center" data-testid="no-listings">
          <p className="text-sm text-zinc-400">Aucune transaction récente trouvée dans ce périmètre.</p>
        </div>
      )}
    </div>
  );
}
