import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Save, RotateCcw } from "lucide-react";

const FIELD_LABELS = {
  floor_rdc: { label: "RDC", unit: "%", group: "Étage" },
  floor_1st: { label: "1er étage", unit: "%", group: "Étage" },
  floor_2_3_no_elevator: { label: "2e-3e sans ascenseur", unit: "%", group: "Étage" },
  floor_4_5_no_elevator: { label: "4e-5e sans ascenseur", unit: "%", group: "Étage" },
  floor_6_plus_no_elevator: { label: "6e+ sans ascenseur", unit: "%", group: "Étage" },
  floor_last_with_elevator: { label: "Dernier étage + ascenseur", unit: "%", group: "Étage" },
  floor_per_level_elevator: { label: "Par étage au-delà du 3e", unit: "%", group: "Étage" },
  balcony_pct: { label: "Balcon", unit: "%", group: "Extérieur" },
  terrace_pct: { label: "Terrasse", unit: "%", group: "Extérieur" },
  garden_pct: { label: "Jardin privatif", unit: "%", group: "Extérieur" },
  south_traversant: { label: "Sud / traversant", unit: "%", group: "Exposition" },
  north_mono: { label: "Nord mono-orienté", unit: "%", group: "Exposition" },
  vis_a_vis_close: { label: "Vis-à-vis < 10m", unit: "%", group: "Exposition" },
  view_monument: { label: "Vue monument", unit: "%", group: "Vue" },
  view_rooftops: { label: "Vue toits / dégagée", unit: "%", group: "Vue" },
  view_garden: { label: "Vue jardin / parc", unit: "%", group: "Vue" },
  view_wall: { label: "Vis-à-vis mur", unit: "%", group: "Vue" },
  dpe_ab: { label: "DPE A ou B", unit: "%", group: "DPE" },
  dpe_cd: { label: "DPE C ou D", unit: "%", group: "DPE" },
  dpe_e: { label: "DPE E", unit: "%", group: "DPE" },
  dpe_f: { label: "DPE F", unit: "%", group: "DPE" },
  dpe_g: { label: "DPE G", unit: "%", group: "DPE" },
  parking_central: { label: "Parking (arr. centraux)", unit: "€", group: "Parking" },
  parking_intermediate: { label: "Parking (arr. intermédiaires)", unit: "€", group: "Parking" },
  parking_peripheral: { label: "Parking (arr. périphériques)", unit: "€", group: "Parking" },
  ceiling_low: { label: "HSP < 2,50m", unit: "%", group: "Hauteur" },
  ceiling_standard: { label: "HSP 2,50–2,80m", unit: "%", group: "Hauteur" },
  ceiling_high: { label: "HSP > 2,80m", unit: "%", group: "Hauteur" },
  state_to_renovate: { label: "À rénover (coût/m²)", unit: "€/m²", group: "État" },
  state_refresh: { label: "Rafraîchissement (coût/m²)", unit: "€/m²", group: "État" },
  state_good: { label: "Bon état", unit: "%", group: "État" },
  state_new: { label: "Refait à neuf", unit: "%", group: "État" },
  state_luxury: { label: "Standing luxe", unit: "%", group: "État" },
  haussmann_bonus: { label: "Pierre de taille", unit: "%", group: "Immeuble" },
  concierge_bonus: { label: "Gardien / concierge", unit: "%", group: "Immeuble" },
  small_building_bonus: { label: "Petit immeuble (<10 lots)", unit: "%", group: "Immeuble" },
  sold_occupied_discount: { label: "Vendu occupé", unit: "%", group: "Juridique" },
  max_cumulative_pct: { label: "Plafond cumulé ajustements", unit: "%", group: "Plafonnement" },
};

export default function Settings() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getAlgorithmConfig().then(setConfig).catch(() => toast.error("Erreur de chargement")).finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateAlgorithmConfig(config);
      toast.success("Coefficients sauvegardés !");
    } catch {
      toast.error("Erreur de sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    api.getAlgorithmConfig().then(setConfig);
    toast.info("Coefficients réinitialisés aux valeurs par défaut");
  };

  if (loading || !config) return <div className="min-h-screen flex items-center justify-center"><div className="w-6 h-6 border-2 border-zinc-200 border-t-black rounded-full animate-spin" /></div>;

  const groups = {};
  Object.entries(FIELD_LABELS).forEach(([key, meta]) => {
    if (!groups[meta.group]) groups[meta.group] = [];
    groups[meta.group].push({ key, ...meta });
  });

  return (
    <div className="min-h-screen bg-white" data-testid="settings-page">
      <header className="border-b border-zinc-200 sticky top-0 bg-white/80 backdrop-blur-xl z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3" data-testid="settings-nav-home">
            <div className="w-8 h-8 bg-gradient-to-br from-slate-800 to-slate-600 rounded-lg flex items-center justify-center"><span className="text-white font-bold text-sm">V</span></div>
            <span className="font-bold text-lg tracking-tight text-slate-800">Valorisateur</span><span className="font-medium text-lg text-teal-600 ml-1">Ingrid</span>
          </Link>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={handleReset} className="rounded-none text-xs" data-testid="reset-config-btn">
              <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Réinitialiser
            </Button>
            <Button size="sm" onClick={handleSave} disabled={saving} className="rounded-none bg-black text-white hover:bg-zinc-800 text-xs" data-testid="save-config-btn">
              <Save className="w-3.5 h-3.5 mr-1.5" /> {saving ? "Sauvegarde..." : "Sauvegarder"}
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8">
        <h1 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight mb-2" data-testid="settings-title">Coefficients de l'algorithme</h1>
        <p className="text-sm text-zinc-500 mb-8">Ajustez manuellement les coefficients de surcote et décote utilisés dans l'estimation. Les modifications s'appliquent à toutes les futures estimations.</p>

        <div className="space-y-8">
          {Object.entries(groups).map(([groupName, fields]) => (
            <div key={groupName} className="border border-zinc-200" data-testid={`config-group-${groupName.toLowerCase()}`}>
              <div className="px-6 py-3 bg-zinc-50 border-b border-zinc-200">
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-mono font-medium">{groupName}</p>
              </div>
              <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {fields.map(({ key, label, unit }) => (
                  <div key={key}>
                    <Label className="text-xs text-zinc-500 mb-1 block">{label}</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        step={unit === "€" || unit === "€/m²" ? 100 : 0.5}
                        value={config[key] ?? 0}
                        onChange={(e) => setConfig(prev => ({ ...prev, [key]: parseFloat(e.target.value) || 0 }))}
                        className="rounded-none h-9 font-mono text-sm"
                        data-testid={`config-${key}`}
                      />
                      <span className="text-xs text-zinc-400 font-mono w-10 shrink-0">{unit}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
