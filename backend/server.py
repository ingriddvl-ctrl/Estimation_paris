from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import httpx
import math
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── Models ───

class PropertyLocation(BaseModel):
    address: str = ""
    street_number: str = ""
    street_name: str = ""
    postal_code: str = ""
    city: str = "Paris"
    arrondissement: str = ""
    floor: int = 0
    position: str = "sur_rue"
    latitude: float = 0.0
    longitude: float = 0.0
    iris_code: str = ""

class PropertyCharacteristics(BaseModel):
    surface_carrez: float = 0.0
    surface_habitable: float = 0.0
    rooms: int = 1
    bedrooms: int = 1
    bathrooms: int = 1
    property_type: str = "appartement"
    exposure: str = "sud"
    luminosity: str = "bon"
    view: str = "degagee"
    exterior_type: str = "aucun"
    exterior_surface: float = 0.0
    ceiling_height: str = "2.50-2.80"
    parking: str = "aucun"
    cave: bool = False
    cave_surface: float = 0.0
    annexes: List[str] = []

class PropertyCondition(BaseModel):
    general_state: str = "bon_etat"
    renovation_year: Optional[int] = None
    kitchen_quality: str = "equipee_basique"
    bathroom_quality: str = "standard"
    flooring: str = "parquet_massif"
    windows: str = "double_vitrage"
    insulation: str = "partielle"
    heating: str = "individuel_gaz"
    dpe: str = "D"
    ges: str = "D"
    asbestos: bool = False
    lead: bool = False
    electrical_compliance: bool = True

class BuildingInfo(BaseModel):
    construction_era: str = "haussmannien"
    building_type: str = "pierre_taille"
    total_floors: int = 6
    total_lots: int = 20
    elevator: bool = True
    concierge: bool = False
    security: str = "digicode"
    common_areas_state: str = "bon"
    facade_state: str = "correct"
    roof_state: str = "correct"
    annual_charges: float = 0.0
    ongoing_procedures: str = "aucune"
    syndic_type: str = "professionnel"

class LegalInfo(BaseModel):
    ownership_type: str = "pleine_propriete"
    property_tax: float = 0.0
    current_rent: float = 0.0
    remaining_lease_months: int = 0
    carrez_certified: bool = True
    servitudes: str = ""
    plu_zone: str = ""

class ValuationRequest(BaseModel):
    location: PropertyLocation
    characteristics: PropertyCharacteristics
    condition: PropertyCondition
    building: BuildingInfo
    legal: LegalInfo

class ValuationResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    share_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request: ValuationRequest
    price_low: float = 0.0
    price_median: float = 0.0
    price_high: float = 0.0
    price_per_sqm_low: float = 0.0
    price_per_sqm_median: float = 0.0
    price_per_sqm_high: float = 0.0
    confidence_score: int = 0
    adjustments: List[Dict[str, Any]] = []
    comparables: List[Dict[str, Any]] = []
    location_scores: Dict[str, Any] = {}
    risks: List[Dict[str, Any]] = []
    market_data: Dict[str, Any] = {}

class AlgorithmConfig(BaseModel):
    floor_rdc: float = -12.0
    floor_1st: float = -6.0
    floor_2_3_no_elevator: float = 0.0
    floor_4_5_no_elevator: float = -5.0
    floor_6_plus_no_elevator: float = -15.0
    floor_last_with_elevator: float = 10.0
    floor_per_level_elevator: float = 1.5
    balcony_pct: float = 4.0
    terrace_pct: float = 10.0
    garden_pct: float = 15.0
    south_traversant: float = 4.0
    north_mono: float = -4.0
    vis_a_vis_close: float = -6.0
    view_monument: float = 12.0
    view_rooftops: float = 5.0
    view_garden: float = 3.0
    view_wall: float = -6.0
    dpe_ab: float = 4.0
    dpe_cd: float = 0.0
    dpe_e: float = -4.0
    dpe_f: float = -12.0
    dpe_g: float = -20.0
    parking_central: float = 40000.0
    parking_intermediate: float = 27000.0
    parking_peripheral: float = 20000.0
    ceiling_low: float = -7.0
    ceiling_standard: float = 0.0
    ceiling_high: float = 5.0
    state_to_renovate: float = -1200.0
    state_refresh: float = -400.0
    state_good: float = 0.0
    state_new: float = 10.0
    state_luxury: float = 15.0
    haussmann_bonus: float = 7.0
    concierge_bonus: float = 3.0
    small_building_bonus: float = 3.0
    sold_occupied_discount: float = -15.0

class SimulationRequest(BaseModel):
    property_price: float
    notary_rate: float = 7.5
    broker_fee: float = 0.0
    broker_pct: float = 0.0
    loan_amount: float = 0.0
    interest_rate: float = 3.5
    loan_duration_years: int = 25
    insurance_rate: float = 0.34
    down_payment: float = 0.0
    renovation_budget: float = 0.0

# ─── Default algorithm config ───

DEFAULT_CONFIG = AlgorithmConfig()

async def get_algorithm_config() -> AlgorithmConfig:
    doc = await db.algorithm_config.find_one({"active": True}, {"_id": 0})
    if doc:
        return AlgorithmConfig(**doc)
    return DEFAULT_CONFIG

# ─── External API proxies ───

@api_router.get("/address/search")
async def search_address(q: str = Query(..., min_length=3)):
    async with httpx.AsyncClient(timeout=10) as client_http:
        resp = await client_http.get(
            "https://api-adresse.data.gouv.fr/search/",
            params={"q": q, "limit": 8, "type": "housenumber", "citycode": "75056"}
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for f in data.get("features", []):
                props = f.get("properties", {})
                coords = f.get("geometry", {}).get("coordinates", [0, 0])
                results.append({
                    "label": props.get("label", ""),
                    "street_number": props.get("housenumber", ""),
                    "street_name": props.get("street", ""),
                    "postal_code": props.get("postcode", ""),
                    "city": props.get("city", "Paris"),
                    "longitude": coords[0],
                    "latitude": coords[1],
                    "context": props.get("context", "")
                })
            return results
        return []

@api_router.get("/dvf/search")
async def search_dvf(
    lat: float = Query(...),
    lon: float = Query(...),
    radius: int = Query(default=500)
):
    async with httpx.AsyncClient(timeout=15) as client_http:
        resp = await client_http.get(
            "https://api.cquest.org/dvf",
            params={
                "lat": lat, "lon": lon,
                "dist": radius
            }
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for r in data.get("resultats", [])[:50]:
                if r.get("nature_mutation") == "Vente" and r.get("type_local") == "Appartement":
                    results.append({
                        "date": r.get("date_mutation", ""),
                        "price": r.get("valeur_fonciere", 0),
                        "surface": r.get("surface_reelle_bati", 0),
                        "rooms": r.get("nombre_pieces_principales", 0),
                        "address": f"{r.get('adresse_numero', '')} {r.get('adresse_nom_voie', '')}",
                        "postal_code": r.get("code_postal", ""),
                        "latitude": r.get("latitude", lat),
                        "longitude": r.get("longitude", lon),
                        "price_per_sqm": round(r.get("valeur_fonciere", 0) / max(r.get("surface_reelle_bati", 1), 1))
                    })
            return results
        return []

@api_router.get("/geo/risks")
async def get_geo_risks(lat: float = Query(...), lon: float = Query(...)):
    risks = []
    try:
        async with httpx.AsyncClient(timeout=10) as client_http:
            resp = await client_http.get(
                "https://georisques.gouv.fr/api/v1/gaspar/risques",
                params={"latlon": f"{lon},{lat}", "rayon": 500, "page": 1, "page_size": 10}
            )
            if resp.status_code == 200:
                data = resp.json()
                for r in data.get("data", []):
                    risks.append({
                        "type": r.get("libelle_risque_long", r.get("libelle_risque", "Risque inconnu")),
                        "level": "info",
                        "source": "Géorisques"
                    })
    except Exception as e:
        logger.warning(f"Georisques API error: {e}")
    return risks

# ─── Valuation Engine ───

def get_arrondissement_zone(postal_code: str) -> str:
    central = ["75001", "75002", "75003", "75004", "75005", "75006", "75007"]
    intermediate = ["75008", "75009", "75010", "75011", "75012", "75014", "75015", "75016", "75017"]
    if postal_code in central:
        return "central"
    elif postal_code in intermediate:
        return "intermediate"
    return "peripheral"

def compute_floor_adjustment(floor: int, elevator: bool, config: AlgorithmConfig) -> tuple:
    if floor == 0:
        return config.floor_rdc, "RDC : décote standard"
    elif floor == 1:
        return config.floor_1st, "1er étage : légère décote"
    elif floor <= 3 and not elevator:
        return config.floor_2_3_no_elevator, "2e-3e sans ascenseur : référence"
    elif floor <= 5 and not elevator:
        return config.floor_4_5_no_elevator, "4e-5e sans ascenseur : décote effort"
    elif floor >= 6 and not elevator:
        return config.floor_6_plus_no_elevator, "6e+ sans ascenseur : forte décote"
    elif elevator:
        bonus = config.floor_last_with_elevator if floor >= 6 else config.floor_per_level_elevator * max(0, floor - 3)
        label = f"Étage {floor} avec ascenseur : surcote"
        return bonus, label
    return 0.0, "Étage standard"

@api_router.post("/valuation/estimate")
async def estimate_valuation(req: ValuationRequest):
    config = await get_algorithm_config()
    loc = req.location
    chars = req.characteristics
    cond = req.condition
    bldg = req.building
    legal = req.legal

    # 1. Fetch DVF comparables
    comparables = []
    base_price_sqm = 10500.0  # Paris average fallback
    try:
        async with httpx.AsyncClient(timeout=15) as client_http:
            resp = await client_http.get(
                "https://api.cquest.org/dvf",
                params={"lat": loc.latitude, "lon": loc.longitude, "dist": 500}
            )
            if resp.status_code == 200:
                data = resp.json()
                for r in data.get("resultats", [])[:50]:
                    if (r.get("nature_mutation") == "Vente" and
                        r.get("type_local") == "Appartement" and
                        r.get("surface_reelle_bati", 0) > 9):
                        surface = r["surface_reelle_bati"]
                        price = r.get("valeur_fonciere", 0)
                        if price > 0:
                            comparables.append({
                                "date": r.get("date_mutation", ""),
                                "price": price,
                                "surface": surface,
                                "rooms": r.get("nombre_pieces_principales", 0),
                                "address": f"{r.get('adresse_numero', '')} {r.get('adresse_nom_voie', '')}".strip(),
                                "postal_code": r.get("code_postal", ""),
                                "latitude": r.get("latitude", loc.latitude),
                                "longitude": r.get("longitude", loc.longitude),
                                "price_per_sqm": round(price / surface)
                            })
    except Exception as e:
        logger.warning(f"DVF API error: {e}")

    # Calculate median from comparables
    if comparables:
        prices = sorted([c["price_per_sqm"] for c in comparables])
        n = len(prices)
        base_price_sqm = prices[n // 2] if n % 2 == 1 else (prices[n // 2 - 1] + prices[n // 2]) / 2
    
    confidence = min(95, 30 + len(comparables) * 3)

    # 2. Apply adjustments
    adjustments = []
    total_pct_adjustment = 0.0
    total_flat_adjustment = 0.0

    # Floor
    floor_adj, floor_label = compute_floor_adjustment(chars.floor if hasattr(chars, 'floor') else loc.floor, bldg.elevator, config)
    if floor_adj != 0:
        adjustments.append({"name": "Étage", "value": floor_adj, "type": "pct", "detail": floor_label})
        total_pct_adjustment += floor_adj

    # Exposure
    if chars.exposure in ["sud", "multi"]:
        adj = config.south_traversant
        adjustments.append({"name": "Exposition", "value": adj, "type": "pct", "detail": f"Exposition {chars.exposure} : surcote"})
        total_pct_adjustment += adj
    elif chars.exposure == "nord":
        adj = config.north_mono
        adjustments.append({"name": "Exposition", "value": adj, "type": "pct", "detail": "Exposition nord : décote"})
        total_pct_adjustment += adj

    # View
    view_map = {
        "monument": (config.view_monument, "Vue monument : forte surcote"),
        "degagee": (config.view_rooftops, "Vue dégagée : surcote"),
        "jardin": (config.view_garden, "Vue sur jardin : surcote"),
        "vis_a_vis_proche": (config.view_wall, "Vis-à-vis proche : décote"),
        "vis_a_vis_lointain": (0.0, ""),
        "cour": (1.0, "Vue cour intérieure"),
        "parc": (config.view_garden, "Vue sur parc : surcote")
    }
    if chars.view in view_map and view_map[chars.view][0] != 0:
        adj, label = view_map[chars.view]
        adjustments.append({"name": "Vue", "value": adj, "type": "pct", "detail": label})
        total_pct_adjustment += adj

    # Exterior
    if chars.exterior_type == "balcon" and chars.exterior_surface > 0:
        adj = config.balcony_pct
        adjustments.append({"name": "Balcon", "value": adj, "type": "pct", "detail": f"Balcon {chars.exterior_surface}m²"})
        total_pct_adjustment += adj
    elif chars.exterior_type == "terrasse" and chars.exterior_surface > 0:
        adj = config.terrace_pct
        adjustments.append({"name": "Terrasse", "value": adj, "type": "pct", "detail": f"Terrasse {chars.exterior_surface}m²"})
        total_pct_adjustment += adj
    elif chars.exterior_type == "jardin" and chars.exterior_surface > 0:
        adj = config.garden_pct
        adjustments.append({"name": "Jardin privatif", "value": adj, "type": "pct", "detail": f"Jardin {chars.exterior_surface}m²"})
        total_pct_adjustment += adj

    # DPE
    dpe_map = {"A": config.dpe_ab, "B": config.dpe_ab, "C": config.dpe_cd, "D": config.dpe_cd,
               "E": config.dpe_e, "F": config.dpe_f, "G": config.dpe_g}
    dpe_adj = dpe_map.get(cond.dpe, 0)
    if dpe_adj != 0:
        adjustments.append({"name": "DPE", "value": dpe_adj, "type": "pct", "detail": f"DPE classe {cond.dpe}"})
        total_pct_adjustment += dpe_adj

    # Ceiling height
    ceiling_map = {"<2.50": config.ceiling_low, "2.50-2.80": config.ceiling_standard,
                   "2.80-3.20": config.ceiling_high, ">3.20": config.ceiling_high}
    ceil_adj = ceiling_map.get(chars.ceiling_height, 0)
    if ceil_adj != 0:
        adjustments.append({"name": "Hauteur sous plafond", "value": ceil_adj, "type": "pct", "detail": f"HSP {chars.ceiling_height}m"})
        total_pct_adjustment += ceil_adj

    # General state
    state_map = {
        "a_renover": (config.state_to_renovate, "flat", "À rénover : coût travaux estimé"),
        "rafraichissement": (config.state_refresh, "flat", "Rafraîchissement à prévoir"),
        "bon_etat": (config.state_good, "pct", "Bon état : référence"),
        "refait_neuf": (config.state_new, "pct", "Refait à neuf : surcote"),
        "luxe": (config.state_luxury, "pct", "Standing luxe : forte surcote")
    }
    if cond.general_state in state_map:
        val, adj_type, label = state_map[cond.general_state]
        if val != 0:
            if adj_type == "flat":
                adjustments.append({"name": "État général", "value": val, "type": "flat_per_sqm", "detail": label})
                total_flat_adjustment += val * chars.surface_carrez
            else:
                adjustments.append({"name": "État général", "value": val, "type": "pct", "detail": label})
                total_pct_adjustment += val

    # Building type
    if bldg.building_type == "pierre_taille":
        adj = config.haussmann_bonus
        adjustments.append({"name": "Immeuble haussmannien", "value": adj, "type": "pct", "detail": "Pierre de taille : surcote"})
        total_pct_adjustment += adj

    if bldg.concierge:
        adj = config.concierge_bonus
        adjustments.append({"name": "Gardien", "value": adj, "type": "pct", "detail": "Gardien/concierge : surcote"})
        total_pct_adjustment += adj

    if bldg.total_lots < 10:
        adj = config.small_building_bonus
        adjustments.append({"name": "Petit immeuble", "value": adj, "type": "pct", "detail": f"< 10 lots ({bldg.total_lots}) : surcote"})
        total_pct_adjustment += adj

    # Parking
    if chars.parking != "aucun":
        zone = get_arrondissement_zone(loc.postal_code)
        parking_val = {"central": config.parking_central, "intermediate": config.parking_intermediate, "peripheral": config.parking_peripheral}
        p_adj = parking_val.get(zone, config.parking_peripheral)
        adjustments.append({"name": "Parking", "value": p_adj, "type": "flat", "detail": f"Place de stationnement ({zone})"})
        total_flat_adjustment += p_adj

    # Sold occupied
    if legal.current_rent > 0 and legal.remaining_lease_months > 0:
        adj = config.sold_occupied_discount
        adjustments.append({"name": "Vendu occupé", "value": adj, "type": "pct", "detail": f"Bail en cours ({legal.remaining_lease_months} mois restants)"})
        total_pct_adjustment += adj

    # 3. Calculate final price
    adjusted_price_sqm = base_price_sqm * (1 + total_pct_adjustment / 100)
    total_price_median = adjusted_price_sqm * chars.surface_carrez + total_flat_adjustment
    
    # Spread for range
    spread = 0.08 if confidence > 60 else 0.12
    total_price_low = total_price_median * (1 - spread)
    total_price_high = total_price_median * (1 + spread)

    # Location scores (simplified)
    location_scores = {
        "global": 72,
        "transports": 80,
        "commerces": 75,
        "education": 70,
        "sante": 68,
        "espaces_verts": 60,
        "calme": 65,
        "dynamisme": 78
    }

    # Risks
    risks = []
    if cond.dpe in ["F", "G"]:
        risks.append({
            "type": "Passoire énergétique",
            "level": "critical",
            "detail": f"DPE {cond.dpe} — Interdiction de location progressive. Coût rénovation estimé : {int(chars.surface_carrez * 500)}–{int(chars.surface_carrez * 1200)}€"
        })
    if cond.asbestos:
        risks.append({"type": "Amiante", "level": "warning", "detail": "Présence d'amiante détectée dans les diagnostics"})
    if cond.lead:
        risks.append({"type": "Plomb", "level": "warning", "detail": "Présence de plomb détectée"})
    if bldg.ongoing_procedures not in ["aucune", ""]:
        risks.append({"type": "Copropriété", "level": "warning", "detail": f"Procédure en cours : {bldg.ongoing_procedures}"})

    # Try to get georisks
    try:
        async with httpx.AsyncClient(timeout=8) as client_http:
            resp = await client_http.get(
                "https://georisques.gouv.fr/api/v1/gaspar/risques",
                params={"latlon": f"{loc.longitude},{loc.latitude}", "rayon": 500, "page": 1, "page_size": 10}
            )
            if resp.status_code == 200:
                geo_data = resp.json()
                for r in geo_data.get("data", []):
                    risks.append({
                        "type": r.get("libelle_risque_long", "Risque naturel"),
                        "level": "info",
                        "detail": f"Source : Géorisques",
                        "source": "Géorisques"
                    })
    except Exception:
        pass

    result = ValuationResult(
        request=req,
        price_low=round(total_price_low),
        price_median=round(total_price_median),
        price_high=round(total_price_high),
        price_per_sqm_low=round(total_price_low / max(chars.surface_carrez, 1)),
        price_per_sqm_median=round(adjusted_price_sqm),
        price_per_sqm_high=round(total_price_high / max(chars.surface_carrez, 1)),
        confidence_score=confidence,
        adjustments=adjustments,
        comparables=comparables[:20],
        location_scores=location_scores,
        risks=risks,
        market_data={
            "base_price_sqm": round(base_price_sqm),
            "total_comparables": len(comparables),
            "adjustment_pct": round(total_pct_adjustment, 1),
            "adjustment_flat": round(total_flat_adjustment)
        }
    )
    return result.model_dump()

# ─── Save / History / Share ───

@api_router.post("/valuation/save")
async def save_valuation(data: dict):
    data["saved_at"] = datetime.now(timezone.utc).isoformat()
    await db.valuations.insert_one(data)
    return {"status": "saved", "id": data.get("id"), "share_id": data.get("share_id")}

@api_router.get("/valuations")
async def list_valuations():
    docs = await db.valuations.find({}, {"_id": 0}).sort("saved_at", -1).to_list(100)
    return docs

@api_router.get("/valuation/{val_id}")
async def get_valuation(val_id: str):
    doc = await db.valuations.find_one({"id": val_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Valuation not found")
    return doc

@api_router.delete("/valuation/{val_id}")
async def delete_valuation(val_id: str):
    result = await db.valuations.delete_one({"id": val_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Valuation not found")
    return {"status": "deleted"}

@api_router.get("/share/{share_id}")
async def get_shared_valuation(share_id: str):
    doc = await db.valuations.find_one({"share_id": share_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Shared valuation not found")
    return doc

# ─── Algorithm Config ───

@api_router.get("/algorithm/config")
async def get_config():
    config = await get_algorithm_config()
    return config.model_dump()

@api_router.put("/algorithm/config")
async def update_config(data: dict):
    data["active"] = True
    await db.algorithm_config.update_one({"active": True}, {"$set": data}, upsert=True)
    return {"status": "updated"}

# ─── Purchase Simulation ───

@api_router.post("/simulation/calculate")
async def calculate_simulation(req: SimulationRequest):
    price = req.property_price
    notary_fees = price * req.notary_rate / 100
    broker_fee = req.broker_fee if req.broker_fee > 0 else price * req.broker_pct / 100
    
    loan_amount = req.loan_amount if req.loan_amount > 0 else (price + notary_fees + broker_fee - req.down_payment + req.renovation_budget)
    
    monthly_rate = req.interest_rate / 100 / 12
    n_months = req.loan_duration_years * 12
    
    if monthly_rate > 0:
        monthly_payment = loan_amount * monthly_rate / (1 - (1 + monthly_rate) ** (-n_months))
    else:
        monthly_payment = loan_amount / n_months
    
    monthly_insurance = loan_amount * req.insurance_rate / 100 / 12
    total_monthly = monthly_payment + monthly_insurance
    
    total_interest = (monthly_payment * n_months) - loan_amount
    total_insurance = monthly_insurance * n_months
    total_cost = price + notary_fees + broker_fee + req.renovation_budget + total_interest + total_insurance
    
    return {
        "property_price": round(price),
        "notary_fees": round(notary_fees),
        "broker_fee": round(broker_fee),
        "renovation_budget": round(req.renovation_budget),
        "loan_amount": round(loan_amount),
        "monthly_payment": round(monthly_payment),
        "monthly_insurance": round(monthly_insurance),
        "total_monthly": round(total_monthly),
        "total_interest": round(total_interest),
        "total_insurance": round(total_insurance),
        "total_cost": round(total_cost),
        "down_payment": round(req.down_payment),
        "cost_breakdown": [
            {"name": "Prix du bien", "value": round(price)},
            {"name": "Frais de notaire", "value": round(notary_fees)},
            {"name": "Frais de courtier", "value": round(broker_fee)},
            {"name": "Budget travaux", "value": round(req.renovation_budget)},
            {"name": "Intérêts totaux", "value": round(total_interest)},
            {"name": "Assurance emprunteur", "value": round(total_insurance)}
        ]
    }

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
