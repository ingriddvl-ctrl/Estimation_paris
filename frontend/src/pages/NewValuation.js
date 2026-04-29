import { useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { ArrowLeft, ArrowRight, MapPin, Home, Wrench, Building2, Scale, Loader2 } from "lucide-react";

const STEPS = [
  { id: 1, label: "Localisation", icon: MapPin },
  { id: 2, label: "Bien", icon: Home },
  { id: 3, label: "État", icon: Wrench },
  { id: 4, label: "Immeuble", icon: Building2 },
  { id: 5, label: "Juridique", icon: Scale },
];

const DEFAULT_FORM = {
  location: { address: "", street_number: "", street_name: "", postal_code: "", city: "", arrondissement: "", floor: 2, position: "sur_rue", latitude: 48.8566, longitude: 2.3522, iris_code: "" },
  characteristics: { surface_carrez: 50, surface_habitable: 50, rooms: 2, bedrooms: 1, bathrooms: 1, property_type: "appartement", exposure: "sud", luminosity: "bon", view: "degagee", exterior_type: "aucun", exterior_surface: 0, ceiling_height: "2.50-2.80", parking: "aucun", cave: false, cave_surface: 0, annexes: [] },
  condition: { general_state: "bon_etat", renovation_year: null, kitchen_quality: "equipee_basique", bathroom_quality: "standard", flooring: "parquet_massif", windows: "double_vitrage", insulation: "partielle", heating: "individuel_gaz", dpe: "D", ges: "D", asbestos: false, lead: false, electrical_compliance: true },
  building: { construction_era: "haussmannien", building_type: "pierre_taille", total_floors: 6, total_lots: 20, elevator: true, concierge: false, security: "digicode", common_areas_state: "bon", facade_state: "correct", roof_state: "correct", annual_charges: 2400, ongoing_procedures: "aucune", syndic_type: "professionnel" },
  legal: { ownership_type: "pleine_propriete", property_tax: 800, current_rent: 0, remaining_lease_months: 0, carrez_certified: true, servitudes: "", plu_zone: "" },
  listing_url: "",
  asking_price: 0,
  castorus_manual: null,
  market_manual: {
    meilleursagents_price_sqm: 0,
    meilleursagents_low: 0,
    meilleursagents_high: 0,
    castorus_dom: 0,
    castorus_price_drops: 0,
    castorus_initial_price: 0,
    castorus_current_price: 0,
    similar_listings: [],
  },
};

export default function NewValuation() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(() => {
    // Check if we're editing an existing estimation
    try {
      const prefill = sessionStorage.getItem("prefill_valuation");
      if (prefill) {
        sessionStorage.removeItem("prefill_valuation");
        const parsed = JSON.parse(prefill);
        // Merge with DEFAULT_FORM to ensure all fields exist
        return {
          ...DEFAULT_FORM,
          location: { ...DEFAULT_FORM.location, ...parsed.location },
          characteristics: { ...DEFAULT_FORM.characteristics, ...parsed.characteristics },
          condition: { ...DEFAULT_FORM.condition, ...parsed.condition },
          building: { ...DEFAULT_FORM.building, ...parsed.building },
          legal: { ...DEFAULT_FORM.legal, ...parsed.legal },
          listing_url: parsed.listing_url || "",
          asking_price: parsed.asking_price || 0,
          castorus_manual: parsed.castorus_manual || null,
          market_manual: { ...DEFAULT_FORM.market_manual, ...(parsed.market_manual || {}) },
        };
      }
    } catch (e) {
      console.warn("Prefill error:", e);
    }
    // Check if we're coming from a listing analysis
    try {
      const listingPrefill = sessionStorage.getItem("prefill_listing");
      if (listingPrefill) {
        sessionStorage.removeItem("prefill_listing");
        const ext = JSON.parse(listingPrefill);
        const prefilled = { ...DEFAULT_FORM };
        // Map extracted listing data to form fields
        if (ext.address) prefilled.location = { ...prefilled.location, address: ext.address };
        if (ext.postal_code) prefilled.location = { ...prefilled.location, postal_code: ext.postal_code };
        if (ext.floor !== undefined) prefilled.location = { ...prefilled.location, floor: ext.floor };
        if (ext.surface_carrez) prefilled.characteristics = { ...prefilled.characteristics, surface_carrez: ext.surface_carrez };
        if (ext.rooms) prefilled.characteristics = { ...prefilled.characteristics, rooms: ext.rooms };
        if (ext.bedrooms) prefilled.characteristics = { ...prefilled.characteristics, bedrooms: ext.bedrooms };
        if (ext.parking) prefilled.characteristics = { ...prefilled.characteristics, parking: "sous_sol" };
        if (ext.exterior_surface) {
          prefilled.characteristics = { ...prefilled.characteristics, exterior_type: "balcon", exterior_surface: ext.exterior_surface };
        }
        if (ext.dpe) prefilled.condition = { ...prefilled.condition, dpe: ext.dpe };
        if (ext.ges) prefilled.condition = { ...prefilled.condition, ges: ext.ges };
        if (ext.elevator !== undefined) prefilled.building = { ...prefilled.building, elevator: ext.elevator };
        if (ext.asking_price) prefilled.asking_price = ext.asking_price;
        return prefilled;
      }
    } catch (e) {
      console.warn("Listing prefill error:", e);
    }
    return DEFAULT_FORM;
  });
  const [addressSuggestions, setAddressSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTimeout, setSearchTimeout] = useState(null);

  const update = useCallback((section, field, value) => {
    setForm(prev => ({ ...prev, [section]: { ...prev[section], [field]: value } }));
  }, []);

  const searchAddress = useCallback(async (query) => {
    if (query.length < 3) { setAddressSuggestions([]); return; }
    if (searchTimeout) clearTimeout(searchTimeout);
    const t = setTimeout(async () => {
      try {
        const results = await api.searchAddress(query);
        setAddressSuggestions(results);
      } catch { setAddressSuggestions([]); }
    }, 300);
    setSearchTimeout(t);
  }, [searchTimeout]);

  const selectAddress = (addr) => {
    const isParis = addr.postal_code?.startsWith("75");
    setForm(prev => ({
      ...prev,
      location: {
        ...prev.location,
        address: addr.label,
        street_number: addr.street_number,
        street_name: addr.street_name,
        postal_code: addr.postal_code,
        city: addr.city,
        latitude: addr.latitude,
        longitude: addr.longitude,
        arrondissement: isParis ? addr.postal_code.slice(-2) : (addr.city || ""),
      }
    }));
    setAddressSuggestions([]);
  };

  const handleSubmit = async () => {
    if (!form.location.address || form.characteristics.surface_carrez <= 0) {
      toast.error("Veuillez renseigner au minimum l'adresse et la surface.");
      return;
    }
    setLoading(true);
    try {
      // Build castorus_manual from market_manual if user filled it
      const mm = form.market_manual || {};
      let castorus = form.castorus_manual;
      if (mm.castorus_dom > 0 || mm.castorus_price_drops > 0 || mm.castorus_initial_price > 0) {
        castorus = {
          source: "manual_input",
          days_on_market: mm.castorus_dom || null,
          num_price_drops: mm.castorus_price_drops || 0,
          initial_price: mm.castorus_initial_price || null,
          current_price: mm.castorus_current_price || null,
          total_drop_pct: (mm.castorus_initial_price && mm.castorus_current_price && mm.castorus_initial_price > 0)
            ? Math.round((mm.castorus_initial_price - mm.castorus_current_price) / mm.castorus_initial_price * 1000) / 10
            : 0,
        };
      }

      // Build browser_market_data from manual similar listings
      const similarListings = (mm.similar_listings || []).filter(l => l.price > 0 && l.surface > 0);
      let browserMarketData = null;
      if (similarListings.length > 0 || mm.meilleursagents_price_sqm > 0) {
        const listings = similarListings.map(l => ({
          price: l.price,
          surface: l.surface,
          price_per_sqm: l.surface > 0 ? Math.round(l.price / l.surface) : 0,
          url: l.url || "",
          source: "manual_input",
        }));
        browserMarketData = {
          listings,
          listing_count: listings.length,
          listing_median_sqm: listings.length > 0
            ? listings.map(l => l.price_per_sqm).sort((a, b) => a - b)[Math.floor(listings.length / 2)]
            : 0,
          meilleursagents: mm.meilleursagents_price_sqm > 0 ? {
            source: "manual_input",
            price_per_sqm: mm.meilleursagents_price_sqm,
            price_low: mm.meilleursagents_low || null,
            price_high: mm.meilleursagents_high || null,
          } : null,
          source: "manual",
        };
      }

      const payload = {
        ...form,
        castorus_manual: castorus,
        browser_market_data: browserMarketData,
      };

      const result = await api.estimateValuation(payload);

      // Merge manual market data into result for display
      if (browserMarketData) {
        if (!result.active_market || result.active_market.listings_count === 0) {
          result.active_market = {
            ...result.active_market,
            listings_count: browserMarketData.listing_count || 0,
            listings_sample: browserMarketData.listings || [],
            listing_median_sqm: browserMarketData.listing_median_sqm || 0,
            manual_source: true,
          };
        }
        if (browserMarketData.meilleursagents) {
          result.meilleursagents = browserMarketData.meilleursagents;
        }
      }

      await api.saveValuation(result);
      toast.success("Estimation calculée !");
      navigate(`/results/${result.id}`);
    } catch (err) {
      toast.error("Erreur lors du calcul. Veuillez réessayer.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const canNext = () => {
    if (step === 1) return form.location.address.length > 3;
    if (step === 2) return form.characteristics.surface_carrez > 0;
    return true;
  };

  return (
    <div className="min-h-screen bg-white" data-testid="new-valuation-page">
      {/* Header */}
      <header className="border-b border-zinc-200 sticky top-0 bg-white/80 backdrop-blur-xl z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 hover:opacity-70 transition-opacity" data-testid="nav-home">
            <div className="w-8 h-8 bg-blue-600 rounded-xl flex items-center justify-center shadow-sm shadow-blue-600/20">
              <span className="text-white font-bold text-sm">V</span>
            </div>
            <span className="font-extrabold text-lg tracking-tight text-zinc-900">Ingrid</span><span className="font-bold text-lg text-blue-600 ml-1">Immo</span>
          </Link>
          <span className="text-xs font-mono text-zinc-400">Étape {step}/5</span>
        </div>
      </header>

      {/* Step indicator */}
      <div className="max-w-5xl mx-auto px-6 py-6">
        <div className="flex items-center gap-2" data-testid="step-indicator">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center gap-2">
              <button
                onClick={() => setStep(s.id)}
                className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium transition-all ${
                  step === s.id ? "bg-black text-white" : step > s.id ? "bg-zinc-800 text-white" : "bg-zinc-100 text-zinc-400"
                }`}
                data-testid={`step-btn-${s.id}`}
              >
                <s.icon className="w-3.5 h-3.5" strokeWidth={1.5} />
                <span className="hidden sm:inline">{s.label}</span>
              </button>
              {i < STEPS.length - 1 && <div className="w-4 h-px bg-zinc-200" />}
            </div>
          ))}
        </div>
      </div>

      {/* Form */}
      <div className="max-w-5xl mx-auto px-6 pb-24">
        <div className="animate-slide-in" key={step}>
          {step === 1 && <Step1 form={form} update={update} searchAddress={searchAddress} suggestions={addressSuggestions} selectAddress={selectAddress} />}
          {step === 2 && <Step2 form={form} update={update} />}
          {step === 3 && <Step3 form={form} update={update} />}
          {step === 4 && <Step4 form={form} update={update} />}
          {step === 5 && <Step5 form={form} update={update} />}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-12 pt-6 border-t border-zinc-200">
          <Button
            variant="outline"
            onClick={() => setStep(Math.max(1, step - 1))}
            disabled={step === 1}
            className="rounded-none h-11 px-6"
            data-testid="prev-step-btn"
          >
            <ArrowLeft className="w-4 h-4 mr-2" /> Précédent
          </Button>
          {step < 5 ? (
            <Button
              onClick={() => setStep(Math.min(5, step + 1))}
              disabled={!canNext()}
              className="rounded-none h-11 px-6 bg-black text-white hover:bg-zinc-800"
              data-testid="next-step-btn"
            >
              Suivant <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={loading}
              className="rounded-none h-11 px-8 bg-black text-white hover:bg-zinc-800"
              data-testid="submit-valuation-btn"
            >
              {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Calcul en cours...</> : "Estimer le bien"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Step Components ─── */

function FieldGroup({ label, children, overline }) {
  return (
    <div className="mb-6">
      {overline && <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-4">{overline}</p>}
      {label && <Label className="text-sm font-medium text-zinc-700 mb-2 block">{label}</Label>}
      {children}
    </div>
  );
}

function Step1({ form, update, searchAddress, suggestions, selectAddress }) {
  return (
    <div data-testid="step-1-form">
      <h2 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight mb-2">Localisation exacte</h2>
      <p className="text-sm text-zinc-500 mb-8">L'adresse détermine le prix de référence via les transactions DVF du quartier.</p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <FieldGroup label="Adresse complète" overline="Adresse">
            <div className="relative">
              <Input
                value={form.location.address}
                onChange={(e) => { update("location", "address", e.target.value); searchAddress(e.target.value); }}
                placeholder="12 rue de Rivoli, Paris ou 5 av. Charles de Gaulle, Neuilly"
                className="rounded-none h-11 border-zinc-300 focus:ring-black"
                data-testid="address-input"
              />
              {suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 bg-white border border-zinc-200 z-50 max-h-48 overflow-y-auto" data-testid="address-suggestions">
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => selectAddress(s)}
                      className="w-full text-left px-4 py-2.5 text-sm hover:bg-zinc-50 border-b border-zinc-100 last:border-0 transition-colors"
                      data-testid={`address-suggestion-${i}`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </FieldGroup>
          <div className="grid grid-cols-2 gap-4">
            <FieldGroup label="Code postal">
              <Input value={form.location.postal_code} onChange={(e) => update("location", "postal_code", e.target.value)} className="rounded-none h-11" data-testid="postal-code-input" />
            </FieldGroup>
            <FieldGroup label="Arrondissement / Ville">
              <Input value={form.location.arrondissement} onChange={(e) => update("location", "arrondissement", e.target.value)} placeholder="e.g. 04 ou Neuilly" className="rounded-none h-11" data-testid="arrondissement-input" />
            </FieldGroup>
          </div>
        </div>
        <div>
          <FieldGroup label="Étage du bien" overline="Position">
            <Select value={String(form.location.floor)} onValueChange={(v) => update("location", "floor", parseInt(v))}>
              <SelectTrigger className="rounded-none h-11" data-testid="floor-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="0">RDC</SelectItem>
                {[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20].map(f => <SelectItem key={f} value={String(f)}>{f === 1 ? "1er" : `${f}e`} étage</SelectItem>)}
              </SelectContent>
            </Select>
          </FieldGroup>
          <FieldGroup label="Position dans l'immeuble">
            <Select value={form.location.position} onValueChange={(v) => update("location", "position", v)}>
              <SelectTrigger className="rounded-none h-11" data-testid="position-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="sur_rue">Sur rue</SelectItem>
                <SelectItem value="sur_cour">Sur cour</SelectItem>
                <SelectItem value="traversant">Traversant</SelectItem>
                <SelectItem value="angle">Angle</SelectItem>
              </SelectContent>
            </Select>
          </FieldGroup>
          {form.location.latitude !== 0 && (
            <div className="p-4 bg-zinc-50 border border-zinc-200 mt-4">
              <p className="text-xs font-mono text-zinc-400">GPS : {form.location.latitude.toFixed(5)}, {form.location.longitude.toFixed(5)}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Step2({ form, update }) {
  return (
    <div data-testid="step-2-form">
      <h2 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight mb-2">Caractéristiques du bien</h2>
      <p className="text-sm text-zinc-500 mb-8">Surface, pièces, exposition et extérieurs influencent directement la valorisation.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <FieldGroup label="Surface Carrez (m²)" overline="Surfaces">
          <Input type="number" value={form.characteristics.surface_carrez} onChange={(e) => update("characteristics", "surface_carrez", parseFloat(e.target.value) || 0)} className="rounded-none h-11" data-testid="surface-input" />
        </FieldGroup>
        <FieldGroup label="Surface habitable (m²)">
          <Input type="number" value={form.characteristics.surface_habitable} onChange={(e) => update("characteristics", "surface_habitable", parseFloat(e.target.value) || 0)} className="rounded-none h-11" data-testid="surface-hab-input" />
        </FieldGroup>
        <FieldGroup label="Nombre de pièces" overline="Distribution">
          <Select value={String(form.characteristics.rooms)} onValueChange={(v) => update("characteristics", "rooms", parseInt(v))}>
            <SelectTrigger className="rounded-none h-11" data-testid="rooms-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              {[1,2,3,4,5,6,7].map(r => <SelectItem key={r} value={String(r)}>{r === 1 ? "Studio/T1" : `T${r}`}</SelectItem>)}
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Chambres">
          <Input type="number" min="0" value={form.characteristics.bedrooms} onChange={(e) => update("characteristics", "bedrooms", parseInt(e.target.value) || 0)} className="rounded-none h-11" data-testid="bedrooms-input" />
        </FieldGroup>
        <FieldGroup label="Salles de bain">
          <Input type="number" min="0" value={form.characteristics.bathrooms} onChange={(e) => update("characteristics", "bathrooms", parseInt(e.target.value) || 0)} className="rounded-none h-11" data-testid="bathrooms-input" />
        </FieldGroup>
        <FieldGroup label="Type de bien">
          <Select value={form.characteristics.property_type} onValueChange={(v) => update("characteristics", "property_type", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="type-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="appartement">Appartement classique</SelectItem>
              <SelectItem value="loft">Loft</SelectItem>
              <SelectItem value="duplex">Duplex</SelectItem>
              <SelectItem value="triplex">Triplex</SelectItem>
              <SelectItem value="souplex">Souplex</SelectItem>
              <SelectItem value="chambre_service">Chambre de service</SelectItem>
              <SelectItem value="penthouse">Dernier étage / Penthouse</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        {(form.characteristics.property_type === "duplex" || form.characteristics.property_type === "triplex" || form.characteristics.property_type === "souplex") && (
          <FieldGroup label={form.characteristics.property_type === "souplex" ? "Étage inférieur (sous-sol)" : "Étage supérieur"} overline={form.characteristics.property_type.charAt(0).toUpperCase() + form.characteristics.property_type.slice(1)}>
            <Select value={String(form.characteristics.second_floor || (form.characteristics.property_type === "souplex" ? -1 : (form.location.floor || 0) + 1))} onValueChange={(v) => update("characteristics", "second_floor", parseInt(v))}>
              <SelectTrigger className="rounded-none h-11"><SelectValue /></SelectTrigger>
              <SelectContent>
                {form.characteristics.property_type === "souplex" && <SelectItem value="-1">Sous-sol</SelectItem>}
                <SelectItem value="0">RDC</SelectItem>
                {[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20].map(f => <SelectItem key={f} value={String(f)}>{f === 1 ? "1er" : `${f}e`} étage</SelectItem>)}
              </SelectContent>
            </Select>
          </FieldGroup>
        )}
        <FieldGroup label="Exposition" overline="Luminosité">
          <Select value={form.characteristics.exposure} onValueChange={(v) => update("characteristics", "exposure", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="exposure-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="nord">Nord</SelectItem>
              <SelectItem value="sud">Sud</SelectItem>
              <SelectItem value="est">Est</SelectItem>
              <SelectItem value="ouest">Ouest</SelectItem>
              <SelectItem value="multi">Multi-exposition</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Vue">
          <Select value={form.characteristics.view} onValueChange={(v) => update("characteristics", "view", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="view-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="monument">Sur monument</SelectItem>
              <SelectItem value="degagee">Dégagée / toits</SelectItem>
              <SelectItem value="jardin">Sur jardin</SelectItem>
              <SelectItem value="parc">Sur parc</SelectItem>
              <SelectItem value="cour">Cour intérieure</SelectItem>
              <SelectItem value="vis_a_vis_proche">Vis-à-vis proche (&lt;10m)</SelectItem>
              <SelectItem value="vis_a_vis_lointain">Vis-à-vis lointain (&gt;10m)</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Extérieur(s)">
          <Select value={form.characteristics.exterior_type} onValueChange={(v) => update("characteristics", "exterior_type", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="exterior-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="aucun">Aucun</SelectItem>
              <SelectItem value="balcon">Balcon</SelectItem>
              <SelectItem value="terrasse">Terrasse</SelectItem>
              <SelectItem value="loggia">Loggia</SelectItem>
              <SelectItem value="jardin">Jardin privatif</SelectItem>
              <SelectItem value="balcon_terrasse">Balcon + Terrasse</SelectItem>
              <SelectItem value="plusieurs_balcons">Plusieurs balcons</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        {form.characteristics.exterior_type !== "aucun" && (
          <FieldGroup label="Surface extérieure totale (m²)">
            <Input type="number" min="0" value={form.characteristics.exterior_surface} onChange={(e) => update("characteristics", "exterior_surface", parseFloat(e.target.value) || 0)} className="rounded-none h-11" data-testid="exterior-surface-input" />
          </FieldGroup>
        )}
        <FieldGroup label="Hauteur sous plafond" overline="Volumes">
          <Select value={form.characteristics.ceiling_height} onValueChange={(v) => update("characteristics", "ceiling_height", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="ceiling-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="<2.50">&lt; 2,50m</SelectItem>
              <SelectItem value="2.50-2.80">2,50 — 2,80m</SelectItem>
              <SelectItem value="2.80-3.20">2,80 — 3,20m</SelectItem>
              <SelectItem value=">3.20">&gt; 3,20m (haussmannien)</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Parking">
          <Select value={form.characteristics.parking} onValueChange={(v) => update("characteristics", "parking", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="parking-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="aucun">Aucun</SelectItem>
              <SelectItem value="sous_sol">Place en sous-sol</SelectItem>
              <SelectItem value="box">Box fermé</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        {form.characteristics.parking !== "aucun" && (
          <FieldGroup label="Parking inclus dans le prix ?" overline="Parking">
            <div className="space-y-3">
              <div className="flex items-center gap-3 h-11">
                <Switch checked={form.characteristics.parking_included !== false} onCheckedChange={(v) => update("characteristics", "parking_included", v)} />
                <span className="text-sm text-zinc-600">{form.characteristics.parking_included !== false ? "Inclus dans le prix" : "En sus du prix"}</span>
              </div>
              {form.characteristics.parking_included === false && (
                <Input type="number" min="0" value={form.characteristics.parking_price || 0} onChange={(e) => update("characteristics", "parking_price", parseFloat(e.target.value) || 0)} placeholder="Prix du parking (€)" className="rounded-none h-11" />
              )}
            </div>
          </FieldGroup>
        )}
        <FieldGroup label="Cave">
          <div className="flex items-center gap-3 h-11">
            <Switch checked={form.characteristics.cave} onCheckedChange={(v) => update("characteristics", "cave", v)} data-testid="cave-switch" />
            <span className="text-sm text-zinc-600">{form.characteristics.cave ? "Oui" : "Non"}</span>
          </div>
        </FieldGroup>
      </div>
    </div>
  );
}

function Step3({ form, update }) {
  return (
    <div data-testid="step-3-form">
      <h2 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight mb-2">État et qualité du bien</h2>
      <p className="text-sm text-zinc-500 mb-8">L'état intérieur, le DPE et les équipements ont un impact direct sur la valorisation.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <FieldGroup label="État général" overline="Rénovation">
          <Select value={form.condition.general_state} onValueChange={(v) => update("condition", "general_state", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="state-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="a_renover">À rénover entièrement</SelectItem>
              <SelectItem value="rafraichissement">Rafraîchissement à prévoir</SelectItem>
              <SelectItem value="bon_etat">Bon état — habitable en l'état</SelectItem>
              <SelectItem value="refait_neuf">Refait à neuf récemment</SelectItem>
              <SelectItem value="luxe">Standing luxe / architecte</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="DPE" overline="Performance énergétique">
          <Select value={form.condition.dpe} onValueChange={(v) => update("condition", "dpe", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="dpe-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              {["A","B","C","D","E","F","G"].map(c => <SelectItem key={c} value={c}>Classe {c}</SelectItem>)}
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="GES (émissions CO₂)">
          <Select value={form.condition.ges} onValueChange={(v) => update("condition", "ges", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="ges-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              {["A","B","C","D","E","F","G"].map(c => <SelectItem key={c} value={c}>Classe {c}</SelectItem>)}
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Configuration cuisine" overline="Cuisine">
          <Select value={form.condition.kitchen_config || "fermee"} onValueChange={(v) => update("condition", "kitchen_config", v)}>
            <SelectTrigger className="rounded-none h-11"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="fermee">Cuisine fermée (séparée)</SelectItem>
              <SelectItem value="semi_ouverte">Semi-ouverte</SelectItem>
              <SelectItem value="ouverte">Ouverte sur le séjour</SelectItem>
              <SelectItem value="americaine">Américaine / îlot central</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Équipement cuisine">
          <Select value={form.condition.kitchen_quality} onValueChange={(v) => update("condition", "kitchen_quality", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="kitchen-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="non_equipee">Non équipée</SelectItem>
              <SelectItem value="equipee_basique">Équipée basique</SelectItem>
              <SelectItem value="equipee_moderne">Équipée moderne</SelectItem>
              <SelectItem value="haut_gamme">Haut de gamme (Bulthaup, Poggenpohl...)</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="État de la cuisine">
          <Select value={form.condition.kitchen_state || "bon"} onValueChange={(v) => update("condition", "kitchen_state", v)}>
            <SelectTrigger className="rounded-none h-11"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="a_refaire">À refaire</SelectItem>
              <SelectItem value="correct">Correct / fonctionnel</SelectItem>
              <SelectItem value="bon">Bon état</SelectItem>
              <SelectItem value="neuf">Neuf / refait récemment</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Salle(s) de bain" overline="Sanitaires">
          <Select value={form.condition.bathroom_quality} onValueChange={(v) => update("condition", "bathroom_quality", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="bathroom-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="a_refaire">À refaire</SelectItem>
              <SelectItem value="standard">Standard / correct</SelectItem>
              <SelectItem value="recent">Récente / moderne</SelectItem>
              <SelectItem value="haut_gamme">Haut de gamme (douche italienne, design...)</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Type de sol principal" overline="Revêtements">
          <Select value={form.condition.flooring} onValueChange={(v) => update("condition", "flooring", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="flooring-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="parquet_hongrie">Parquet point de Hongrie</SelectItem>
              <SelectItem value="parquet_massif">Parquet massif classique</SelectItem>
              <SelectItem value="parquet_mosaique">Parquet mosaïque</SelectItem>
              <SelectItem value="parquet_contrecolle">Parquet contrecollé</SelectItem>
              <SelectItem value="stratifie">Stratifié / sol souple</SelectItem>
              <SelectItem value="carrelage">Carrelage</SelectItem>
              <SelectItem value="tomettes">Tomettes anciennes</SelectItem>
              <SelectItem value="beton_cire">Béton ciré</SelectItem>
              <SelectItem value="moquette">Moquette</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="État du sol">
          <Select value={form.condition.flooring_state || "bon"} onValueChange={(v) => update("condition", "flooring_state", v)}>
            <SelectTrigger className="rounded-none h-11"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="abime">Abîmé / à remplacer</SelectItem>
              <SelectItem value="use">Usé mais fonctionnel</SelectItem>
              <SelectItem value="bon">Bon état</SelectItem>
              <SelectItem value="neuf">Neuf / poncé récemment</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Fenêtres / Menuiseries" overline="Isolation">
          <Select value={form.condition.windows} onValueChange={(v) => update("condition", "windows", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="windows-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="simple_vitrage">Simple vitrage (ancien)</SelectItem>
              <SelectItem value="double_vitrage">Double vitrage</SelectItem>
              <SelectItem value="double_renforce">Double vitrage renforcé / phonique</SelectItem>
              <SelectItem value="triple_vitrage">Triple vitrage</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Chauffage">
          <Select value={form.condition.heating} onValueChange={(v) => update("condition", "heating", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="heating-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="individuel_gaz">Individuel gaz</SelectItem>
              <SelectItem value="individuel_elec">Individuel électrique</SelectItem>
              <SelectItem value="collectif_gaz">Collectif gaz</SelectItem>
              <SelectItem value="collectif_fioul">Collectif fioul</SelectItem>
              <SelectItem value="pac">Pompe à chaleur</SelectItem>
              <SelectItem value="sol">Chauffage au sol</SelectItem>
              <SelectItem value="urbain">Réseau de chaleur urbain</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        {form.condition.heating === "collectif_fioul" && (
          <div className="col-span-full bg-amber-50 border border-amber-200 p-4">
            <p className="text-sm text-amber-800"><strong>Attention :</strong> Le chauffage collectif fioul est voué à disparaître (interdiction depuis 2022). Le remplacement sera à la charge de la copropriété — coût estimé 15 000 à 40 000 € par lot. Ce risque est intégré automatiquement.</p>
          </div>
        )}
        <FieldGroup label="Diagnostics" overline="Risques techniques">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Switch checked={form.condition.asbestos} onCheckedChange={(v) => update("condition", "asbestos", v)} />
              <span className="text-sm text-zinc-600">Amiante détectée</span>
            </div>
            <div className="flex items-center gap-3">
              <Switch checked={form.condition.lead} onCheckedChange={(v) => update("condition", "lead", v)} />
              <span className="text-sm text-zinc-600">Plomb détecté (CREP positif)</span>
            </div>
            <div className="flex items-center gap-3">
              <Switch checked={form.condition.electrical_compliance} onCheckedChange={(v) => update("condition", "electrical_compliance", v)} />
              <span className="text-sm text-zinc-600">Électricité aux normes</span>
            </div>
          </div>
        </FieldGroup>
      </div>
    </div>
  );
}

function Step4({ form, update }) {
  return (
    <div data-testid="step-4-form">
      <h2 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight mb-2">Immeuble et copropriété</h2>
      <p className="text-sm text-zinc-500 mb-8">Le type d'immeuble, son état et les travaux prévus impactent fortement la valorisation.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <FieldGroup label="Année de construction" overline="Construction">
          <Input type="number" min="1700" max="2026" value={form.building.construction_year || ""} onChange={(e) => update("building", "construction_year", parseInt(e.target.value) || null)} placeholder="ex: 1972" className="rounded-none h-11" />
        </FieldGroup>
        <FieldGroup label="Style architectural">
          <Select value={form.building.construction_era} onValueChange={(v) => update("building", "construction_era", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="era-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="avant_1850">Ancien (avant 1850)</SelectItem>
              <SelectItem value="haussmannien">Haussmannien classique</SelectItem>
              <SelectItem value="post_haussmannien">Post-haussmannien / Art Déco</SelectItem>
              <SelectItem value="entre_guerres">Entre-deux-guerres (1920–1940)</SelectItem>
              <SelectItem value="post_guerre">Reconstruction (1945–1965)</SelectItem>
              <SelectItem value="70_80">Années 70–80</SelectItem>
              <SelectItem value="90_2000">Années 90–2000</SelectItem>
              <SelectItem value="contemporain">Contemporain (2000–2015)</SelectItem>
              <SelectItem value="neuf">Neuf / BBC / RT2012+ (2015+)</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Type d'immeuble">
          <Select value={form.building.building_type} onValueChange={(v) => update("building", "building_type", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="building-type-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="pierre_taille_haussmannien">Pierre de taille haussmannien</SelectItem>
              <SelectItem value="pierre_taille_autre">Pierre de taille (non haussmannien)</SelectItem>
              <SelectItem value="brique">Brique</SelectItem>
              <SelectItem value="brique_pierre">Brique et pierre</SelectItem>
              <SelectItem value="beton_standing">Béton — immeuble de standing</SelectItem>
              <SelectItem value="beton_simple">Béton — immeuble classique</SelectItem>
              <SelectItem value="residence_securisee">Résidence sécurisée récente</SelectItem>
              <SelectItem value="immeuble_neuf">Immeuble neuf / BBC</SelectItem>
              <SelectItem value="petit_immeuble">Petit immeuble / maison divisée</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Nombre d'étages de l'immeuble">
          <Input type="number" min="1" max="30" value={form.building.total_floors} onChange={(e) => update("building", "total_floors", parseInt(e.target.value) || 1)} className="rounded-none h-11" data-testid="total-floors-input" />
        </FieldGroup>
        <FieldGroup label="Nombre de lots copropriété">
          <Input type="number" min="1" value={form.building.total_lots} onChange={(e) => update("building", "total_lots", parseInt(e.target.value) || 1)} className="rounded-none h-11" data-testid="total-lots-input" />
        </FieldGroup>
        <FieldGroup label="Ascenseur" overline="Équipements">
          <div className="flex items-center gap-3 h-11">
            <Switch checked={form.building.elevator} onCheckedChange={(v) => update("building", "elevator", v)} data-testid="elevator-switch" />
            <span className="text-sm text-zinc-600">{form.building.elevator ? "Oui" : "Non"}</span>
          </div>
        </FieldGroup>
        <FieldGroup label="Gardien / Concierge">
          <div className="flex items-center gap-3 h-11">
            <Switch checked={form.building.concierge} onCheckedChange={(v) => update("building", "concierge", v)} data-testid="concierge-switch" />
            <span className="text-sm text-zinc-600">{form.building.concierge ? "Oui" : "Non"}</span>
          </div>
        </FieldGroup>
        <FieldGroup label="Sécurité">
          <Select value={form.building.security} onValueChange={(v) => update("building", "security", v)}>
            <SelectTrigger className="rounded-none h-11"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="aucune">Aucune</SelectItem>
              <SelectItem value="digicode">Digicode</SelectItem>
              <SelectItem value="interphone">Interphone</SelectItem>
              <SelectItem value="videophone">Visiophone</SelectItem>
              <SelectItem value="badge">Badge / contrôle d'accès</SelectItem>
              <SelectItem value="gardien_video">Gardien + vidéosurveillance</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="État parties communes" overline="État de l'immeuble">
          <Select value={form.building.common_areas_state} onValueChange={(v) => update("building", "common_areas_state", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="common-areas-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="mauvais">Mauvais — vétuste</SelectItem>
              <SelectItem value="correct">Correct — entretenu</SelectItem>
              <SelectItem value="bon">Bon — bien entretenu</SelectItem>
              <SelectItem value="excellent">Excellent — rénové récemment</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Charges annuelles copro (€)">
          <Input type="number" min="0" value={form.building.annual_charges} onChange={(e) => update("building", "annual_charges", parseFloat(e.target.value) || 0)} className="rounded-none h-11" data-testid="charges-input" />
        </FieldGroup>
        <FieldGroup label="Syndic">
          <Select value={form.building.syndic_type} onValueChange={(v) => update("building", "syndic_type", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="syndic-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="professionnel">Professionnel</SelectItem>
              <SelectItem value="benevole">Bénévole</SelectItem>
              <SelectItem value="cooperatif">Coopératif</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
      </div>

      {/* ── TRAVAUX DE COPROPRIÉTÉ ── */}
      <div className="mt-10 pt-6 border-t border-zinc-200">
        <h3 className="font-heading font-semibold text-lg mb-2">Travaux de copropriété</h3>
        <p className="text-sm text-zinc-500 mb-6">Les travaux votés ou à prévoir impactent directement la valeur du bien et les charges futures.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <FieldGroup label="Travaux votés en AG" overline="Travaux prévus">
            <Select value={form.building.ongoing_procedures || "aucune"} onValueChange={(v) => update("building", "ongoing_procedures", v)}>
              <SelectTrigger className="rounded-none h-11" data-testid="procedures-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="aucune">Aucun travaux voté</SelectItem>
                <SelectItem value="ravalement">Ravalement de façade</SelectItem>
                <SelectItem value="toiture">Réfection toiture</SelectItem>
                <SelectItem value="ascenseur">Mise aux normes ascenseur</SelectItem>
                <SelectItem value="chauffage">Remplacement chaudière collective</SelectItem>
                <SelectItem value="parties_communes">Rénovation parties communes</SelectItem>
                <SelectItem value="etancheite">Étanchéité / terrasse</SelectItem>
                <SelectItem value="travaux_lourds">Travaux lourds (plusieurs postes)</SelectItem>
                <SelectItem value="judiciaire">Procédure judiciaire en cours</SelectItem>
              </SelectContent>
            </Select>
          </FieldGroup>
          {form.building.ongoing_procedures && form.building.ongoing_procedures !== "aucune" && (
            <FieldGroup label="Montant estimé des travaux (votre quote-part €)">
              <Input type="number" min="0" value={form.building.works_cost || ""} onChange={(e) => update("building", "works_cost", parseFloat(e.target.value) || 0)} placeholder="ex: 8000" className="rounded-none h-11" />
            </FieldGroup>
          )}
          <FieldGroup label="Ravalement prévu dans les 5 ans ?" overline="Risques copro">
            <Select value={form.building.facade_state || "correct"} onValueChange={(v) => update("building", "facade_state", v)}>
              <SelectTrigger className="rounded-none h-11"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="recent">Non — ravalement récent (&lt;10 ans)</SelectItem>
                <SelectItem value="correct">Pas prévu à court terme</SelectItem>
                <SelectItem value="a_prevoir">Probable dans les 5 ans</SelectItem>
                <SelectItem value="urgent">Urgent — façade dégradée</SelectItem>
              </SelectContent>
            </Select>
          </FieldGroup>
          <FieldGroup label="État de la toiture">
            <Select value={form.building.roof_state || "correct"} onValueChange={(v) => update("building", "roof_state", v)}>
              <SelectTrigger className="rounded-none h-11"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="recent">Récente (&lt;10 ans)</SelectItem>
                <SelectItem value="correct">Correcte</SelectItem>
                <SelectItem value="a_surveiller">À surveiller</SelectItem>
                <SelectItem value="a_refaire">À refaire</SelectItem>
              </SelectContent>
            </Select>
          </FieldGroup>
        </div>
      </div>
    </div>
  );
}

function Step5({ form, update }) {
  const addSimilarListing = () => {
    const current = form.market_manual?.similar_listings || [];
    if (current.length >= 5) return;
    update("market_manual", "similar_listings", [...current, { price: 0, surface: 0, url: "" }]);
  };
  const updateListing = (idx, field, value) => {
    const current = [...(form.market_manual?.similar_listings || [])];
    current[idx] = { ...current[idx], [field]: value };
    update("market_manual", "similar_listings", current);
  };
  const removeListing = (idx) => {
    const current = [...(form.market_manual?.similar_listings || [])];
    current.splice(idx, 1);
    update("market_manual", "similar_listings", current);
  };

  return (
    <div data-testid="step-5-form">
      <h2 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight mb-2">Juridique et situation</h2>
      <p className="text-sm text-zinc-500 mb-8">Ces informations permettent d'ajuster l'estimation selon la situation juridique du bien.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <FieldGroup label="Régime de propriété" overline="Propriété">
          <Select value={form.legal.ownership_type} onValueChange={(v) => update("legal", "ownership_type", v)}>
            <SelectTrigger className="rounded-none h-11" data-testid="ownership-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="pleine_propriete">Pleine propriété</SelectItem>
              <SelectItem value="copropriete">Copropriété classique</SelectItem>
              <SelectItem value="viager_occupe">Viager occupé</SelectItem>
              <SelectItem value="viager_libre">Viager libre</SelectItem>
              <SelectItem value="nue_propriete">Nue-propriété</SelectItem>
              <SelectItem value="emphyteotique">Bail emphytéotique</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        <FieldGroup label="Taxe foncière annuelle (€)" overline="Fiscalité">
          <Input type="number" min="0" value={form.legal.property_tax} onChange={(e) => update("legal", "property_tax", parseFloat(e.target.value) || 0)} className="rounded-none h-11" data-testid="tax-input" />
        </FieldGroup>
        <FieldGroup label="Bien actuellement loué ?" overline="Occupation">
          <Select value={form.legal.current_rent > 0 ? "oui" : "non"} onValueChange={(v) => { if (v === "non") { update("legal", "current_rent", 0); update("legal", "remaining_lease_months", 0); } else { update("legal", "current_rent", 1); } }}>
            <SelectTrigger className="rounded-none h-11"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="non">Non — vendu libre</SelectItem>
              <SelectItem value="oui">Oui — locataire en place</SelectItem>
            </SelectContent>
          </Select>
        </FieldGroup>
        {form.legal.current_rent > 0 && (
          <>
            <FieldGroup label="Loyer mensuel actuel (€)">
              <Input type="number" min="0" value={form.legal.current_rent} onChange={(e) => update("legal", "current_rent", parseFloat(e.target.value) || 0)} placeholder="ex: 1500" className="rounded-none h-11" data-testid="rent-input" />
            </FieldGroup>
            <FieldGroup label="Durée restante du bail (mois)">
              <Input type="number" min="0" value={form.legal.remaining_lease_months} onChange={(e) => update("legal", "remaining_lease_months", parseInt(e.target.value) || 0)} placeholder="ex: 24" className="rounded-none h-11" data-testid="lease-input" />
            </FieldGroup>
          </>
        )}
        {form.legal.current_rent > 0 && (
          <div className="col-span-full bg-blue-50 border border-blue-200 p-4">
            <p className="text-sm text-blue-800">Un bien vendu avec un locataire en place subit une décote de 10 à 20% selon la durée restante du bail et le type de bail. L'acheteur ne peut pas occuper le bien immédiatement.</p>
          </div>
        )}
        <FieldGroup label="Loi Carrez certifiée" overline="Certifications">
          <div className="flex items-center gap-3 h-11">
            <Switch checked={form.legal.carrez_certified} onCheckedChange={(v) => update("legal", "carrez_certified", v)} data-testid="carrez-switch" />
            <span className="text-sm text-zinc-600">{form.legal.carrez_certified ? "Oui" : "Non"}</span>
          </div>
        </FieldGroup>
        <FieldGroup label="Servitudes ou contraintes">
          <Input value={form.legal.servitudes} onChange={(e) => update("legal", "servitudes", e.target.value)} placeholder="Droit de passage, vue protégée, ABF..." className="rounded-none h-11" data-testid="servitudes-input" />
          <p className="text-xs text-zinc-400 mt-1">Contraintes connues : droit de passage, servitude de vue, périmètre ABF (Architecte des Bâtiments de France), etc.</p>
        </FieldGroup>
      </div>

      {/* ── SECTION DONNÉES MARCHÉ ── */}
      <div className="mt-16 pt-8 border-t border-zinc-200">
        <h2 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight mb-2">Données marché (optionnel)</h2>
        <p className="text-sm text-zinc-500 mb-3">Ces données améliorent considérablement la précision de l'estimation.</p>
        <div className="bg-amber-50 border border-amber-200 p-4 mb-8">
          <p className="text-sm text-amber-800">
            <strong>Comment remplir en 2 minutes :</strong> Allez sur <a href="https://www.meilleursagents.com" target="_blank" rel="noopener noreferrer" className="underline font-medium">meilleursagents.com</a>, tapez l'adresse du bien, et copiez le prix/m² affiché. Pour Castorus, installez l'extension Chrome puis consultez l'annonce.
          </p>
        </div>

        <h3 className="font-heading font-semibold text-lg mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-blue-600 text-white flex items-center justify-center text-xs font-bold rounded">1</span>
          Prix/m² MeilleursAgents de la rue
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <FieldGroup label="Prix/m² moyen" overline="MeilleursAgents">
            <Input type="number" min="0" value={form.market_manual?.meilleursagents_price_sqm || ""} onChange={(e) => update("market_manual", "meilleursagents_price_sqm", parseFloat(e.target.value) || 0)} placeholder="ex: 9500" className="rounded-none h-11" />
          </FieldGroup>
          <FieldGroup label="Fourchette basse (€/m²)">
            <Input type="number" min="0" value={form.market_manual?.meilleursagents_low || ""} onChange={(e) => update("market_manual", "meilleursagents_low", parseFloat(e.target.value) || 0)} placeholder="ex: 8200" className="rounded-none h-11" />
          </FieldGroup>
          <FieldGroup label="Fourchette haute (€/m²)">
            <Input type="number" min="0" value={form.market_manual?.meilleursagents_high || ""} onChange={(e) => update("market_manual", "meilleursagents_high", parseFloat(e.target.value) || 0)} placeholder="ex: 11000" className="rounded-none h-11" />
          </FieldGroup>
        </div>

        <h3 className="font-heading font-semibold text-lg mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-orange-500 text-white flex items-center justify-center text-xs font-bold rounded">2</span>
          Données Castorus (si vous avez l'extension)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          <FieldGroup label="Jours en vente" overline="Castorus">
            <Input type="number" min="0" value={form.market_manual?.castorus_dom || ""} onChange={(e) => update("market_manual", "castorus_dom", parseInt(e.target.value) || 0)} placeholder="ex: 45" className="rounded-none h-11" />
          </FieldGroup>
          <FieldGroup label="Nombre de baisses de prix">
            <Input type="number" min="0" value={form.market_manual?.castorus_price_drops || ""} onChange={(e) => update("market_manual", "castorus_price_drops", parseInt(e.target.value) || 0)} placeholder="ex: 2" className="rounded-none h-11" />
          </FieldGroup>
          <FieldGroup label="Prix initial (€)">
            <Input type="number" min="0" value={form.market_manual?.castorus_initial_price || ""} onChange={(e) => update("market_manual", "castorus_initial_price", parseFloat(e.target.value) || 0)} placeholder="ex: 550000" className="rounded-none h-11" />
          </FieldGroup>
          <FieldGroup label="Prix actuel (€)">
            <Input type="number" min="0" value={form.market_manual?.castorus_current_price || ""} onChange={(e) => update("market_manual", "castorus_current_price", parseFloat(e.target.value) || 0)} placeholder="ex: 520000" className="rounded-none h-11" />
          </FieldGroup>
        </div>

        <h3 className="font-heading font-semibold text-lg mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-green-600 text-white flex items-center justify-center text-xs font-bold rounded">3</span>
          Annonces similaires dans le quartier
        </h3>
        <p className="text-sm text-zinc-500 mb-4">Ajoutez 2-3 annonces de biens similaires trouvées sur SeLoger, LeBonCoin ou BienIci.</p>

        {(form.market_manual?.similar_listings || []).map((listing, idx) => (
          <div key={idx} className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4 p-4 bg-zinc-50 border border-zinc-200">
            <FieldGroup label="Prix (€)">
              <Input type="number" min="0" value={listing.price || ""} onChange={(e) => updateListing(idx, "price", parseFloat(e.target.value) || 0)} placeholder="ex: 480000" className="rounded-none h-11" />
            </FieldGroup>
            <FieldGroup label="Surface (m²)">
              <Input type="number" min="0" value={listing.surface || ""} onChange={(e) => updateListing(idx, "surface", parseFloat(e.target.value) || 0)} placeholder="ex: 55" className="rounded-none h-11" />
            </FieldGroup>
            <FieldGroup label="URL de l'annonce">
              <Input value={listing.url || ""} onChange={(e) => updateListing(idx, "url", e.target.value)} placeholder="https://..." className="rounded-none h-11" />
            </FieldGroup>
            <div className="flex items-end">
              <Button variant="outline" onClick={() => removeListing(idx)} className="rounded-none h-11 text-red-500 border-red-200 hover:bg-red-50">
                Supprimer
              </Button>
            </div>
          </div>
        ))}

        {(form.market_manual?.similar_listings || []).length < 5 && (
          <Button variant="outline" onClick={addSimilarListing} className="rounded-none h-11 mt-2">
            + Ajouter une annonce similaire
          </Button>
        )}
      </div>
    </div>
  );
}

