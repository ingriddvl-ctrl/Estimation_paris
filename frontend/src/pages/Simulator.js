import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { ArrowLeft, Loader2 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

function formatPrice(n) {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);
}

export default function Simulator() {
  const { id } = useParams();
  const [valuation, setValuation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [form, setForm] = useState({
    property_price: 0,
    notary_rate: 7.5,
    broker_fee: 0,
    broker_pct: 0,
    loan_amount: 0,
    interest_rate: 3.5,
    loan_duration_years: 25,
    insurance_rate: 0.34,
    down_payment: 0,
    renovation_budget: 0,
  });

  useEffect(() => {
    api.getValuation(id).then(v => {
      setValuation(v);
      setForm(prev => ({ ...prev, property_price: v.price_median || 0 }));
    }).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (form.property_price > 0) {
      api.calculateSimulation(form).then(setResult).catch(() => {});
    }
  }, [form]);

  const upd = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-zinc-400" /></div>;

  const COLORS = ["#0A0A0A", "#E60000", "#71717A", "#0022EE", "#E60000", "#71717A"];

  return (
    <div className="min-h-screen bg-white" data-testid="simulator-page">
      <header className="border-b border-zinc-200 sticky top-0 bg-white/80 backdrop-blur-xl z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3" data-testid="sim-nav-home">
            <div className="w-8 h-8 bg-gradient-to-br from-slate-800 to-slate-600 rounded-lg flex items-center justify-center"><span className="text-white font-bold text-sm">V</span></div>
            <span className="font-bold text-lg tracking-tight text-slate-800">Valorisateur</span><span className="font-medium text-lg text-teal-600 ml-1">Ingrid</span>
          </Link>
          {valuation && (
            <Link to={`/results/${id}`} className="text-xs text-zinc-500 hover:text-black flex items-center gap-1" data-testid="back-to-results">
              <ArrowLeft className="w-3.5 h-3.5" /> Retour aux résultats
            </Link>
          )}
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        <h1 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight mb-2" data-testid="simulator-title">Simulateur de coût d'achat</h1>
        <p className="text-sm text-zinc-500 mb-8">Calculez le coût total réel de votre acquisition : frais de notaire, crédit, assurance et travaux.</p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Form */}
          <div className="space-y-6">
            <div className="border border-zinc-200 p-6">
              <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-4">Prix et apport</p>
              <div className="space-y-4">
                <div>
                  <Label className="text-sm mb-1.5 block">Prix du bien (€)</Label>
                  <Input type="number" value={form.property_price} onChange={(e) => upd("property_price", parseFloat(e.target.value) || 0)} className="rounded-none h-11" data-testid="sim-price-input" />
                </div>
                <div>
                  <Label className="text-sm mb-1.5 block">Apport personnel (€)</Label>
                  <Input type="number" value={form.down_payment} onChange={(e) => upd("down_payment", parseFloat(e.target.value) || 0)} className="rounded-none h-11" data-testid="sim-apport-input" />
                </div>
                <div>
                  <Label className="text-sm mb-1.5 block">Budget travaux (€)</Label>
                  <Input type="number" value={form.renovation_budget} onChange={(e) => upd("renovation_budget", parseFloat(e.target.value) || 0)} className="rounded-none h-11" data-testid="sim-renovation-input" />
                </div>
              </div>
            </div>

            <div className="border border-zinc-200 p-6">
              <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-4">Frais</p>
              <div className="space-y-4">
                <div>
                  <Label className="text-sm mb-1.5 block">Frais de notaire (%)</Label>
                  <div className="flex items-center gap-4">
                    <Slider value={[form.notary_rate]} onValueChange={([v]) => upd("notary_rate", v)} min={2} max={12} step={0.1} className="flex-1" data-testid="sim-notary-slider" />
                    <span className="font-mono text-sm w-16 text-right">{form.notary_rate}%</span>
                  </div>
                </div>
                <div>
                  <Label className="text-sm mb-1.5 block">Frais de courtier (€)</Label>
                  <Input type="number" value={form.broker_fee} onChange={(e) => upd("broker_fee", parseFloat(e.target.value) || 0)} className="rounded-none h-11" data-testid="sim-broker-input" />
                </div>
              </div>
            </div>

            <div className="border border-zinc-200 p-6">
              <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-4">Crédit immobilier</p>
              <div className="space-y-4">
                <div>
                  <Label className="text-sm mb-1.5 block">Taux d'intérêt (%)</Label>
                  <div className="flex items-center gap-4">
                    <Slider value={[form.interest_rate]} onValueChange={([v]) => upd("interest_rate", v)} min={0.5} max={7} step={0.05} className="flex-1" data-testid="sim-rate-slider" />
                    <span className="font-mono text-sm w-16 text-right">{form.interest_rate}%</span>
                  </div>
                </div>
                <div>
                  <Label className="text-sm mb-1.5 block">Durée (années)</Label>
                  <div className="flex items-center gap-4">
                    <Slider value={[form.loan_duration_years]} onValueChange={([v]) => upd("loan_duration_years", v)} min={5} max={30} step={1} className="flex-1" data-testid="sim-duration-slider" />
                    <span className="font-mono text-sm w-16 text-right">{form.loan_duration_years} ans</span>
                  </div>
                </div>
                <div>
                  <Label className="text-sm mb-1.5 block">Assurance emprunteur (%/an)</Label>
                  <div className="flex items-center gap-4">
                    <Slider value={[form.insurance_rate]} onValueChange={([v]) => upd("insurance_rate", v)} min={0} max={1} step={0.01} className="flex-1" data-testid="sim-insurance-slider" />
                    <span className="font-mono text-sm w-16 text-right">{form.insurance_rate}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Results */}
          <div className="space-y-6">
            {result && (
              <>
                <div className="border border-zinc-200 p-6 bg-zinc-50">
                  <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-4">Résumé</p>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-zinc-600">Coût total de l'opération</span>
                      <span className="font-heading font-bold text-2xl" data-testid="sim-total-cost">{formatPrice(result.total_cost)}</span>
                    </div>
                    <div className="h-px bg-zinc-200" />
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-zinc-600">Mensualité (crédit + assurance)</span>
                      <span className="font-heading font-bold text-xl" data-testid="sim-monthly">{formatPrice(result.total_monthly)}<span className="text-sm text-zinc-400 font-normal">/mois</span></span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-zinc-600">dont crédit</span>
                      <span className="font-mono text-sm">{formatPrice(result.monthly_payment)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-zinc-600">dont assurance</span>
                      <span className="font-mono text-sm">{formatPrice(result.monthly_insurance)}</span>
                    </div>
                    <div className="h-px bg-zinc-200" />
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-zinc-600">Montant emprunté</span>
                      <span className="font-mono text-sm" data-testid="sim-loan-amount">{formatPrice(result.loan_amount)}</span>
                    </div>
                  </div>
                </div>

                <div className="border border-zinc-200 p-6">
                  <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-4">Décomposition du coût</p>
                  <div className="h-64" data-testid="sim-chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={result.cost_breakdown?.filter(d => d.value > 0)} layout="vertical" margin={{ left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                        <XAxis type="number" tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }} />
                        <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
                        <Tooltip formatter={(v) => formatPrice(v)} />
                        <Bar dataKey="value" radius={[0, 2, 2, 0]}>
                          {result.cost_breakdown?.filter(d => d.value > 0).map((entry, i) => (
                            <Cell key={i} fill={COLORS[i % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="border border-zinc-200 p-6">
                  <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-4">Détail des coûts</p>
                  <div className="space-y-2">
                    {result.cost_breakdown?.map((item, i) => (
                      <div key={i} className="flex justify-between items-center py-2 border-b border-zinc-100 last:border-0">
                        <span className="text-sm text-zinc-600">{item.name}</span>
                        <span className="font-mono text-sm">{formatPrice(item.value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
