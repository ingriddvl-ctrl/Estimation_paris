import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Trash2, ExternalLink, Share2, Copy, Loader2, MapPin } from "lucide-react";

function formatPrice(n) {
  if (!n) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);
}

export default function History() {
  const [valuations, setValuations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listValuations().then(setValuations).catch(() => toast.error("Erreur de chargement")).finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id) => {
    try {
      await api.deleteValuation(id);
      setValuations(prev => prev.filter(v => v.id !== id));
      toast.success("Estimation supprimée");
    } catch {
      toast.error("Erreur de suppression");
    }
  };

  const copyShareLink = (shareId) => {
    const url = `${window.location.origin}/share/${shareId}`;
    navigator.clipboard.writeText(url);
    toast.success("Lien copié !");
  };

  return (
    <div className="min-h-screen bg-white" data-testid="history-page">
      <header className="border-b border-zinc-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3" data-testid="history-nav-home">
            <div className="w-8 h-8 bg-blue-600 rounded-xl flex items-center justify-center shadow-sm shadow-blue-600/20">
              <span className="text-white font-bold text-sm">V</span>
            </div>
            <span className="font-extrabold text-lg tracking-tight text-zinc-900">Ingrid</span><span className="font-bold text-lg text-blue-600 ml-1">Immo</span>
          </Link>
          <Link to="/new">
            <Button className="rounded-none bg-black text-white hover:bg-zinc-800 text-xs h-9" data-testid="new-valuation-from-history">Nouvelle estimation</Button>
          </Link>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8">
        <h1 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight mb-2" data-testid="history-title">Historique des estimations</h1>
        <p className="text-sm text-zinc-500 mb-8">Retrouvez et comparez toutes vos valorisations sauvegardées.</p>

        {loading ? (
          <div className="flex justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-zinc-400" /></div>
        ) : valuations.length === 0 ? (
          <div className="text-center py-20 border border-zinc-200" data-testid="history-empty">
            <MapPin className="w-8 h-8 text-zinc-300 mx-auto mb-4" />
            <p className="text-zinc-500 mb-4">Aucune estimation sauvegardée</p>
            <Link to="/new">
              <Button className="rounded-none bg-black text-white hover:bg-zinc-800 text-xs">Commencer une estimation</Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-px bg-zinc-200">
            {valuations.map((v, i) => (
              <div key={v.id} className="bg-white p-6 flex items-center justify-between hover:bg-zinc-50 transition-colors animate-fade-in-up" style={{ animationDelay: `${i * 0.05}s` }} data-testid={`history-item-${i}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-heading font-bold text-base truncate" data-testid={`history-address-${i}`}>
                      {v.request?.location?.address || "Adresse inconnue"}
                    </h3>
                    <span className="text-xs font-mono text-zinc-400 shrink-0">
                      {v.request?.characteristics?.surface_carrez || "?"} m²
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-sm font-medium" data-testid={`history-price-${i}`}>{formatPrice(v.price_median)}</span>
                    <span className="text-xs text-zinc-400 font-mono">{formatPrice(v.price_per_sqm_median)}/m²</span>
                    <span className="text-xs text-zinc-400">{v.created_at ? new Date(v.created_at).toLocaleDateString("fr-FR") : ""}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4 shrink-0">
                  <Button variant="ghost" size="sm" onClick={() => copyShareLink(v.share_id)} className="rounded-none h-8 w-8 p-0" data-testid={`history-share-${i}`}>
                    <Copy className="w-3.5 h-3.5" />
                  </Button>
                  <Link to={`/results/${v.id}`}>
                    <Button variant="ghost" size="sm" className="rounded-none h-8 w-8 p-0" data-testid={`history-view-${i}`}>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </Button>
                  </Link>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(v.id)} className="rounded-none h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50" data-testid={`history-delete-${i}`}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
