from fastapi import FastAPI, APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import httpx
import math
import requests
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
    floor_rdc: float = -10.0
    floor_1st: float = -5.0
    floor_2_3_no_elevator: float = 0.0
    floor_4_5_no_elevator: float = -4.0
    floor_6_plus_no_elevator: float = -12.0
    floor_last_with_elevator: float = 5.0
    floor_per_level_elevator: float = 0.8
    balcony_pct: float = 2.0
    terrace_pct: float = 5.0
    garden_pct: float = 8.0
    south_traversant: float = 2.0
    north_mono: float = -3.0
    vis_a_vis_close: float = -5.0
    view_monument: float = 8.0
    view_rooftops: float = 3.0
    view_garden: float = 2.0
    view_wall: float = -5.0
    dpe_ab: float = 3.0
    dpe_cd: float = 0.0
    dpe_e: float = -4.0
    dpe_f: float = -10.0
    dpe_g: float = -18.0
    parking_central: float = 40000.0
    parking_intermediate: float = 27000.0
    parking_peripheral: float = 18000.0
    ceiling_low: float = -5.0
    ceiling_standard: float = 0.0
    ceiling_high: float = 3.0
    state_to_renovate: float = -1200.0
    state_refresh: float = -400.0
    state_good: float = 0.0
    state_new: float = 5.0
    state_luxury: float = 8.0
    haussmann_bonus: float = 4.0
    concierge_bonus: float = 1.5
    small_building_bonus: float = 2.0
    sold_occupied_discount: float = -15.0
    max_cumulative_pct: float = 18.0

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
        params = {"q": q + " Paris", "limit": 8}
        resp = await client_http.get(
            "https://api-adresse.data.gouv.fr/search/",
            params=params
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
    # Convert radius to approx bbox degrees (1 deg ≈ 111km)
    delta = radius / 111000.0
    bbox = f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}"
    async with httpx.AsyncClient(timeout=15) as client_http:
        resp = await client_http.get(
            "https://apidf-preprod.cerema.fr/dvf_opendata/geomutations/",
            params={
                "in_bbox": bbox,
                "page_size": 50,
                "anneemut_min": 2020,
            }
        )
        results = []
        if resp.status_code == 200:
            data = resp.json()
            for f in data.get("features", []):
                p = f.get("properties", {})
                geom = f.get("geometry", {})
                coords = [0, 0]
                # Extract centroid from polygon
                if geom.get("type") == "MultiPolygon" and geom.get("coordinates"):
                    ring = geom["coordinates"][0][0]
                    coords = [sum(c[0] for c in ring)/len(ring), sum(c[1] for c in ring)/len(ring)]
                elif geom.get("type") == "Polygon" and geom.get("coordinates"):
                    ring = geom["coordinates"][0]
                    coords = [sum(c[0] for c in ring)/len(ring), sum(c[1] for c in ring)/len(ring)]
                
                price = p.get("valeurfonc")
                surface = p.get("sbati")
                if price and surface and float(surface) > 9:
                    price_f = float(price)
                    surface_f = float(surface)
                    if price_f > 0:
                        results.append({
                            "date": str(p.get("datemut", p.get("anneemut", ""))),
                            "price": price_f,
                            "surface": surface_f,
                            "rooms": p.get("nbpiece", 0) or 0,
                            "address": p.get("l_adresse", "") or f"Parcelle {p.get('l_idpar', '')}",
                            "postal_code": str(p.get("l_codinsee", ""))[:5],
                            "latitude": coords[1],
                            "longitude": coords[0],
                            "price_per_sqm": round(price_f / surface_f),
                            "type": p.get("libtypbien", ""),
                            "year": p.get("anneemut", ""),
                        })
        return results

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

# Average price/m² by arrondissement (source: DVF 2023-2024 medians, updated periodically)
ARRONDISSEMENT_AVG_PRICES = {
    "75001": 12800, "75002": 11900, "75003": 12100, "75004": 13200,
    "75005": 12500, "75006": 14800, "75007": 14200, "75008": 12600,
    "75009": 11200, "75010": 10400, "75011": 10600, "75012": 9800,
    "75013": 9500, "75014": 10200, "75015": 10000, "75016": 11500,
    "75017": 10800, "75018": 9600, "75019": 8500, "75020": 8800,
}

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

    # 1. Fetch DVF comparables via Cerema API (with retry)
    comparables = []
    base_price_sqm = 10500.0  # Paris average fallback
    try:
        delta = 500 / 111000.0
        bbox = f"{loc.longitude - delta},{loc.latitude - delta},{loc.longitude + delta},{loc.latitude + delta}"
        import asyncio
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=15) as client_http:
                    resp = await client_http.get(
                        "https://apidf-preprod.cerema.fr/dvf_opendata/geomutations/",
                        params={"in_bbox": bbox, "page_size": 50, "anneemut_min": 2020}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for f in data.get("features", []):
                            p = f.get("properties", {})
                            geom = f.get("geometry", {})
                            coords = [loc.longitude, loc.latitude]
                            if geom.get("type") == "Polygon" and geom.get("coordinates"):
                                ring = geom["coordinates"][0]
                                coords = [sum(c[0] for c in ring)/len(ring), sum(c[1] for c in ring)/len(ring)]
                            elif geom.get("type") == "MultiPolygon" and geom.get("coordinates"):
                                ring = geom["coordinates"][0][0]
                                coords = [sum(c[0] for c in ring)/len(ring), sum(c[1] for c in ring)/len(ring)]
                            price = p.get("valeurfonc")
                            surface = p.get("sbati")
                            if price and surface:
                                price_f = float(price)
                                surface_f = float(surface)
                                if price_f > 10000 and surface_f > 9:
                                    comparables.append({
                                        "date": str(p.get("datemut", p.get("anneemut", ""))),
                                        "price": price_f,
                                        "surface": surface_f,
                                        "rooms": p.get("nbpiece", 0) or 0,
                                        "address": p.get("l_adresse", "") or f"Parcelle {p.get('l_idpar', '')}",
                                        "postal_code": str(p.get("l_codinsee", ""))[:5],
                                        "latitude": coords[1],
                                        "longitude": coords[0],
                                        "price_per_sqm": round(price_f / surface_f),
                                    })
                        break  # success
                    elif resp.status_code == 503:
                        await asyncio.sleep(1)
                        continue
                    else:
                        break
            except Exception:
                await asyncio.sleep(1)
    except Exception as e:
        logger.warning(f"DVF API error: {e}")

    # Calculate trimmed median from comparables (remove top/bottom 10% to reduce outlier impact)
    if comparables:
        prices = sorted([c["price_per_sqm"] for c in comparables])
        n = len(prices)
        # Trim 10% from each end
        trim = max(1, n // 10)
        trimmed = prices[trim:n-trim] if n > 4 else prices
        tn = len(trimmed)
        base_price_sqm = trimmed[tn // 2] if tn % 2 == 1 else (trimmed[tn // 2 - 1] + trimmed[tn // 2]) / 2
    
    confidence = min(95, 30 + len(comparables) * 3)

    # 2. Apply adjustments
    adjustments = []
    total_pct_adjustment = 0.0
    total_flat_adjustment = 0.0
    arr_avg = ARRONDISSEMENT_AVG_PRICES.get(loc.postal_code, 10500)
    zone = get_arrondissement_zone(loc.postal_code)

    # Floor
    floor_adj, floor_label = compute_floor_adjustment(loc.floor, bldg.elevator, config)
    if floor_adj != 0:
        if loc.floor == 0:
            hyp = f"Le rez-de-chaussée subit une décote de {abs(floor_adj)}% car il est exposé au bruit de la rue, au manque de luminosité et aux problèmes de sécurité. À Paris, les RDC se vendent en moyenne 10 à 15% moins cher que les étages intermédiaires."
        elif loc.floor >= 6 and not bldg.elevator:
            hyp = f"Un {loc.floor}e étage sans ascenseur entraîne une forte décote ({abs(floor_adj)}%) car l'accessibilité réduit considérablement le bassin d'acheteurs potentiels (familles, personnes âgées). Chaque étage supplémentaire sans ascenseur au-delà du 4e amplifie la décote."
        elif loc.floor >= 6 and bldg.elevator:
            hyp = f"Le dernier étage avec ascenseur bénéficie d'une surcote de +{floor_adj}% : vue dégagée sur les toits, calme supérieur, moins de nuisances sonores des voisins du dessus. C'est un des critères les plus valorisés à Paris."
        elif bldg.elevator and floor_adj > 0:
            hyp = f"L'étage {loc.floor} avec ascenseur bénéficie d'une surcote de +{floor_adj:.1f}% par rapport aux étages bas. Plus on monte avec ascenseur, plus la luminosité, le calme et la vue s'améliorent. Le bonus est de +{config.floor_per_level_elevator}% par étage au-delà du 3e."
        else:
            hyp = f"L'étage {loc.floor} est considéré comme un étage de référence dans le modèle. Pas de surcote ni décote significative."
        adjustments.append({"name": "Étage", "value": floor_adj, "type": "pct", "detail": floor_label, "hypothesis": hyp})
        total_pct_adjustment += floor_adj

    # Exposure
    if chars.exposure in ["sud", "multi"]:
        adj = config.south_traversant
        hyp = f"Une exposition {'sud' if chars.exposure == 'sud' else 'multi-orientée'} apporte +{adj}% car elle maximise l'ensoleillement naturel (4 à 6h de soleil direct par jour en moyenne). Les études DVF montrent que les biens plein sud ou traversants se vendent systématiquement plus cher. L'impact sur les charges de chauffage est aussi positif (économie estimée de 10 à 20% sur la facture énergétique)."
        adjustments.append({"name": "Exposition", "value": adj, "type": "pct", "detail": f"Exposition {chars.exposure} : surcote", "hypothesis": hyp})
        total_pct_adjustment += adj
    elif chars.exposure == "nord":
        adj = config.north_mono
        hyp = f"Une exposition nord mono-orientée entraîne une décote de {abs(adj)}% car le bien reçoit très peu de lumière directe. Les acheteurs parisiens sont particulièrement sensibles à la luminosité, surtout dans les rues étroites. Cela se traduit aussi par des charges de chauffage plus élevées."
        adjustments.append({"name": "Exposition", "value": adj, "type": "pct", "detail": "Exposition nord : décote", "hypothesis": hyp})
        total_pct_adjustment += adj

    # View
    view_hypotheses = {
        "monument": f"La vue sur monument (Tour Eiffel, Sacré-Cœur, Seine, etc.) est le critère de surcote le plus puissant à Paris. Elle apporte +{config.view_monument}% car elle est irremplaçable et très recherchée par les acheteurs français et internationaux. Les biens avec vue iconique se vendent souvent au-dessus de la fourchette haute.",
        "degagee": f"Une vue dégagée sur les toits de Paris apporte +{config.view_rooftops}%. L'absence de vis-à-vis, la sensation d'espace et la lumière supplémentaire sont des critères majeurs. Les acheteurs sont prêts à payer une prime significative pour cette qualité de vie.",
        "jardin": f"La vue sur jardin apporte +{config.view_garden}% grâce au calme, à la verdure et à l'absence de vis-à-vis direct. Dans Paris intra-muros où les espaces verts privatifs sont rares, c'est un atout différenciant.",
        "vis_a_vis_proche": f"Un vis-à-vis à moins de 10 mètres entraîne une décote de {abs(config.view_wall)}%. La perte d'intimité, le manque de lumière et la sensation d'enfermement réduisent significativement l'attractivité du bien. C'est l'un des défauts les plus pénalisants à Paris.",
        "cour": "La vue sur cour intérieure apporte une légère surcote (+1%). C'est calme et protégé du bruit de la rue, mais l'absence de vue dégagée limite la valorisation.",
        "parc": f"La vue sur parc apporte +{config.view_garden}%. La proximité visuelle d'un espace vert est un avantage rare à Paris. Le calme, la verdure permanente et l'absence de construction future en face valorisent durablement le bien.",
    }
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
        hyp = view_hypotheses.get(chars.view, "")
        adjustments.append({"name": "Vue", "value": adj, "type": "pct", "detail": label, "hypothesis": hyp})
        total_pct_adjustment += adj

    # Exterior
    if chars.exterior_type == "balcon" and chars.exterior_surface > 0:
        adj = config.balcony_pct
        hyp = f"Un balcon de {chars.exterior_surface}m² apporte +{adj}% au prix du bien. À Paris, où l'espace extérieur est rare, les premiers mètres carrés de balcon sont valorisés à environ 50-80% du prix/m² intérieur. Au-delà de 8-10m², la valorisation marginale diminue (~30% du prix/m²). Post-Covid, la demande pour les extérieurs a bondi de +15 à 20% selon les notaires."
        adjustments.append({"name": "Balcon", "value": adj, "type": "pct", "detail": f"Balcon {chars.exterior_surface}m²", "hypothesis": hyp})
        total_pct_adjustment += adj
    elif chars.exterior_type == "terrasse" and chars.exterior_surface > 0:
        adj = config.terrace_pct
        hyp = f"Une terrasse de {chars.exterior_surface}m² apporte +{adj}% — c'est un atout majeur à Paris. Les terrasses sont beaucoup plus rares que les balcons et permettent un véritable usage (repas, détente). Leur valorisation peut atteindre 50% du prix/m² intérieur pour les premières surfaces. En dernier étage, une terrasse peut déclencher une surcote encore supérieure."
        adjustments.append({"name": "Terrasse", "value": adj, "type": "pct", "detail": f"Terrasse {chars.exterior_surface}m²", "hypothesis": hyp})
        total_pct_adjustment += adj
    elif chars.exterior_type == "jardin" and chars.exterior_surface > 0:
        adj = config.garden_pct
        hyp = f"Un jardin privatif de {chars.exterior_surface}m² à Paris est exceptionnel et apporte +{adj}%. C'est l'un des biens les plus recherchés du marché parisien. La rareté de l'offre (< 2% des biens) crée une prime significative, surtout dans les arrondissements centraux."
        adjustments.append({"name": "Jardin privatif", "value": adj, "type": "pct", "detail": f"Jardin {chars.exterior_surface}m²", "hypothesis": hyp})
        total_pct_adjustment += adj

    # DPE
    dpe_map = {"A": config.dpe_ab, "B": config.dpe_ab, "C": config.dpe_cd, "D": config.dpe_cd,
               "E": config.dpe_e, "F": config.dpe_f, "G": config.dpe_g}
    dpe_adj = dpe_map.get(cond.dpe, 0)
    if dpe_adj != 0:
        if cond.dpe in ["A", "B"]:
            hyp = f"Le DPE classe {cond.dpe} apporte une surcote de +{dpe_adj}%. Les biens très performants énergétiquement sont de plus en plus recherchés : charges réduites, confort thermique supérieur, et aucune contrainte réglementaire à prévoir. La loi Climat valorise ces biens vertueux."
        elif cond.dpe == "E":
            hyp = f"Le DPE classe E entraîne une décote de {abs(dpe_adj)}%. Bien que non encore interdit à la location, ce DPE signale des travaux de rénovation énergétique à prévoir à moyen terme. Les banques deviennent plus prudentes sur le financement de ces biens."
        elif cond.dpe == "F":
            hyp = f"Le DPE classe F entraîne une forte décote de {abs(dpe_adj)}%. Depuis la loi Climat et Résilience, les logements classés F seront interdits à la location à partir de 2028. Un acquéreur devra budgéter des travaux de rénovation énergétique (estimation : {int(chars.surface_carrez * 500)} à {int(chars.surface_carrez * 1000)}€). Les notaires constatent une décote moyenne de 8 à 15% sur ces biens."
        elif cond.dpe == "G":
            hyp = f"Le DPE classe G entraîne une décote majeure de {abs(dpe_adj)}%. Ces biens sont déjà interdits à la location depuis janvier 2025. L'acquéreur devra obligatoirement réaliser une rénovation énergétique lourde (estimation : {int(chars.surface_carrez * 800)} à {int(chars.surface_carrez * 1500)}€). Le nombre de biens G sur le marché a explosé, créant une pression à la baisse supplémentaire."
        else:
            hyp = f"Le DPE classe {cond.dpe} est la référence du marché. Pas de surcote ni décote significative."
        adjustments.append({"name": "DPE", "value": dpe_adj, "type": "pct", "detail": f"DPE classe {cond.dpe}", "hypothesis": hyp})
        total_pct_adjustment += dpe_adj

    # Ceiling height
    ceiling_map = {"<2.50": config.ceiling_low, "2.50-2.80": config.ceiling_standard,
                   "2.80-3.20": config.ceiling_high, ">3.20": config.ceiling_high}
    ceil_adj = ceiling_map.get(chars.ceiling_height, 0)
    if ceil_adj != 0:
        if ceil_adj < 0:
            hyp = f"Une hauteur sous plafond inférieure à 2,50m entraîne une décote de {abs(ceil_adj)}%. Cela crée une sensation d'écrasement, réduit la luminosité et peut poser des problèmes d'aménagement (meubles hauts, mezzanine impossible). C'est souvent le cas des chambres de service ou immeubles post-guerre."
        else:
            hyp = f"Une hauteur sous plafond de {chars.ceiling_height}m apporte +{ceil_adj}%. Les grands volumes sont très valorisés à Paris : sensation d'espace, luminosité accrue, possibilité de mezzanine. C'est caractéristique des immeubles haussmanniens nobles et très recherché."
        adjustments.append({"name": "Hauteur sous plafond", "value": ceil_adj, "type": "pct", "detail": f"HSP {chars.ceiling_height}m", "hypothesis": hyp})
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
                cost_total = abs(val) * chars.surface_carrez
                hyp = f"Le bien nécessite {'une rénovation complète' if cond.general_state == 'a_renover' else 'un rafraîchissement'} estimé à {abs(val)}€/m², soit environ {int(cost_total):,}€ au total. Cette décote reflète le coût réel des travaux que l'acquéreur devra engager (électricité, plomberie, sols, cuisine, salle de bain). Le budget travaux doit être intégré dans le plan de financement."
                adjustments.append({"name": "État général", "value": val, "type": "flat_per_sqm", "detail": label, "hypothesis": hyp})
                total_flat_adjustment += val * chars.surface_carrez
            else:
                if cond.general_state == "refait_neuf":
                    hyp = f"Un bien refait à neuf bénéficie d'une surcote de +{val}%. L'acquéreur n'aura aucun travaux à prévoir et peut emménager immédiatement. Les finitions récentes (cuisine, salle de bain, électricité) réduisent aussi les frais d'entretien sur 10-15 ans."
                elif cond.general_state == "luxe":
                    hyp = f"Un standing luxe (matériaux haut de gamme, domotique, cuisine sur mesure) apporte +{val}%. Ce niveau de finition cible une clientèle premium prête à payer un surcoût significatif pour un bien clé-en-main exceptionnel."
                else:
                    hyp = "Bon état général, considéré comme la référence du marché."
                adjustments.append({"name": "État général", "value": val, "type": "pct", "detail": label, "hypothesis": hyp})
                total_pct_adjustment += val

    # Building type
    if bldg.building_type == "pierre_taille":
        adj = config.haussmann_bonus
        hyp = f"Un immeuble haussmannien en pierre de taille apporte +{adj}% vs un immeuble béton des années 60-70. La qualité architecturale (façade sculptée, moulures, parquet, cheminées), la solidité de construction et le prestige de ces immeubles créent une prime durable. Les immeubles haussmanniens représentent environ 60% du parc du centre de Paris et restent les plus recherchés."
        adjustments.append({"name": "Immeuble haussmannien", "value": adj, "type": "pct", "detail": "Pierre de taille : surcote", "hypothesis": hyp})
        total_pct_adjustment += adj

    if bldg.concierge:
        adj = config.concierge_bonus
        hyp = f"La présence d'un gardien/concierge apporte +{adj}%. Il assure la réception des colis, la propreté des parties communes, la surveillance, et le lien social dans l'immeuble. C'est un service de plus en plus rare et apprécié, surtout dans les copropriétés de standing."
        adjustments.append({"name": "Gardien", "value": adj, "type": "pct", "detail": "Gardien/concierge : surcote", "hypothesis": hyp})
        total_pct_adjustment += adj

    if bldg.total_lots < 10:
        adj = config.small_building_bonus
        hyp = f"Un petit immeuble de {bldg.total_lots} lots apporte +{adj}%. Les charges de copropriété sont généralement plus faibles, les décisions en AG plus rapides, et l'ambiance plus conviviale. Les gros ensembles (>50 lots) subissent l'effet inverse (lourdeur de gestion, conflits plus fréquents)."
        adjustments.append({"name": "Petit immeuble", "value": adj, "type": "pct", "detail": f"< 10 lots ({bldg.total_lots}) : surcote", "hypothesis": hyp})
        total_pct_adjustment += adj

    # Parking
    if chars.parking != "aucun":
        parking_val = {"central": config.parking_central, "intermediate": config.parking_intermediate, "peripheral": config.parking_peripheral}
        p_adj = parking_val.get(zone, config.parking_peripheral)
        hyp = f"Une place de stationnement en zone {zone} à Paris vaut environ {int(p_adj):,}€. Dans les arrondissements centraux, la rareté des places pousse les prix jusqu'à 50 000€. Un parking sécurise aussi le financement bancaire et facilite la revente. Le type '{chars.parking}' est intégré comme un montant forfaitaire ajouté au prix."
        adjustments.append({"name": "Parking", "value": p_adj, "type": "flat", "detail": f"Place de stationnement ({zone})", "hypothesis": hyp})
        total_flat_adjustment += p_adj

    # Sold occupied
    if legal.current_rent > 0 and legal.remaining_lease_months > 0:
        adj = config.sold_occupied_discount
        hyp = f"Le bien est vendu occupé avec un bail de {legal.remaining_lease_months} mois restants et un loyer de {int(legal.current_rent)}€/mois. La décote de {abs(adj)}% reflète l'impossibilité d'occupation immédiate, le risque locatif, et le coût d'opportunité. Plus le bail est long, plus la décote est importante. Un viager ou un bail commercial peut entraîner des décotes de 20 à 40%."
        adjustments.append({"name": "Vendu occupé", "value": adj, "type": "pct", "detail": f"Bail en cours ({legal.remaining_lease_months} mois restants)", "hypothesis": hyp})
        total_pct_adjustment += adj

    # 3. Calculate final price with cumulative cap
    # Cap cumulative % adjustments to avoid over-valuation
    max_cap = config.max_cumulative_pct
    if total_pct_adjustment > max_cap:
        adjustments.append({"name": "Plafonnement", "value": round(max_cap - total_pct_adjustment, 1), "type": "pct", "detail": f"Ajustements cumulés plafonnés à +{max_cap}% (était +{round(total_pct_adjustment,1)}%)", "hypothesis": f"Les surcotes cumulées dépassaient +{round(total_pct_adjustment,1)}%. Un plafonnement à +{max_cap}% est appliqué pour rester réaliste. En pratique, les acheteurs ne paient jamais la somme arithmétique de tous les critères positifs — le marché impose une convergence."})
        total_pct_adjustment = max_cap
    elif total_pct_adjustment < -max_cap:
        adjustments.append({"name": "Plafonnement", "value": round(-max_cap - total_pct_adjustment, 1), "type": "pct", "detail": f"Ajustements cumulés plafonnés à -{max_cap}%", "hypothesis": f"Les décotes cumulées dépassaient {round(total_pct_adjustment,1)}%. Un plancher à -{max_cap}% est appliqué."})
        total_pct_adjustment = -max_cap

    adjusted_price_sqm = base_price_sqm * (1 + total_pct_adjustment / 100)
    total_price_median = adjusted_price_sqm * chars.surface_carrez + total_flat_adjustment
    
    # Spread for range
    spread = 0.08 if confidence > 60 else 0.12
    total_price_low = total_price_median * (1 - spread)
    total_price_high = total_price_median * (1 + spread)

    # Market position: compare to arrondissement average
    final_sqm = adjusted_price_sqm
    diff_vs_arr_pct = ((final_sqm - arr_avg) / arr_avg * 100) if arr_avg > 0 else 0
    if diff_vs_arr_pct > 15:
        market_position = {"label": "++", "description": "Nettement au-dessus du marché", "color": "green"}
    elif diff_vs_arr_pct > 5:
        market_position = {"label": "+", "description": "Au-dessus du marché", "color": "green"}
    elif diff_vs_arr_pct > -5:
        market_position = {"label": "=", "description": "Dans la moyenne du marché", "color": "neutral"}
    elif diff_vs_arr_pct > -15:
        market_position = {"label": "-", "description": "En-dessous du marché", "color": "red"}
    else:
        market_position = {"label": "--", "description": "Nettement en-dessous du marché", "color": "red"}
    market_position["diff_pct"] = round(diff_vs_arr_pct, 1)
    market_position["arr_avg"] = arr_avg
    market_position["estimated_sqm"] = round(final_sqm)

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
            "arrondissement_avg_sqm": arr_avg,
            "arrondissement": loc.postal_code,
            "zone": zone,
            "total_comparables": len(comparables),
            "adjustment_pct": round(total_pct_adjustment, 1),
            "adjustment_flat": round(total_flat_adjustment),
            "base_source": "DVF Cerema (transactions réelles)" if comparables else "Moyenne parisienne (fallback)",
            "comparables_period": "2020–2025",
            "market_position": market_position,
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

# ─── Object Storage for Documents ───

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "valorisateur-paris"
storage_key = None

def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.warning(f"Storage init failed (non-blocking): {e}")

ALLOWED_DOC_TYPES = {
    "pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain", "csv": "text/csv"
}

DOC_CATEGORIES = {
    "pv_ag": "PV d'Assemblée Générale",
    "releve_charges": "Relevé de charges",
    "dpe": "Diagnostic de Performance Énergétique",
    "diagnostic": "Diagnostic technique",
    "reglement_copro": "Règlement de copropriété",
    "plan": "Plan du bien",
    "photo": "Photo",
    "compromis": "Compromis de vente",
    "autre": "Autre document",
}

@api_router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    valuation_id: str = Query(""),
    category: str = Query("autre"),
):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    if ext not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Type de fichier non supporté: .{ext}")
    
    file_id = str(uuid.uuid4())
    storage_path = f"{APP_NAME}/docs/{valuation_id or 'general'}/{file_id}.{ext}"
    data = await file.read()
    
    if len(data) > 20 * 1024 * 1024:  # 20MB max
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 20Mo)")
    
    result = put_object(storage_path, data, file.content_type or ALLOWED_DOC_TYPES.get(ext, "application/octet-stream"))
    
    doc_record = {
        "id": file_id,
        "valuation_id": valuation_id,
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": result.get("size", len(data)),
        "category": category,
        "category_label": DOC_CATEGORIES.get(category, "Autre"),
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.documents.insert_one(doc_record)
    doc_record.pop("_id", None)
    return doc_record

@api_router.get("/documents/{valuation_id}")
async def list_documents(valuation_id: str):
    docs = await db.documents.find(
        {"valuation_id": valuation_id, "is_deleted": False}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return docs

@api_router.get("/documents/download/{file_id}")
async def download_document(file_id: str):
    record = await db.documents.find_one({"id": file_id, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")
    data, content_type = get_object(record["storage_path"])
    return Response(content=data, media_type=record.get("content_type", content_type),
                    headers={"Content-Disposition": f'inline; filename="{record.get("original_filename", "document")}"'})

@api_router.delete("/documents/{file_id}")
async def delete_document(file_id: str):
    result = await db.documents.update_one({"id": file_id}, {"$set": {"is_deleted": True}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted"}

# ─── Market Listings (Offres en cours) ───

@api_router.get("/market/listings")
async def get_market_listings(
    lat: float = Query(...),
    lon: float = Query(...),
    radius: int = Query(default=800),
    min_surface: float = Query(default=0),
    max_surface: float = Query(default=999),
):
    """Fetch current market listings from public API sources"""
    listings = []
    # Try DVF+ for recent (last 6 months) transactions as proxy for market
    try:
        delta = radius / 111000.0
        bbox = f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}"
        async with httpx.AsyncClient(timeout=15) as client_http:
            resp = await client_http.get(
                "https://apidf-preprod.cerema.fr/dvf_opendata/geomutations/",
                params={"in_bbox": bbox, "page_size": 30, "anneemut_min": 2023}
            )
            if resp.status_code == 200:
                data = resp.json()
                for f in data.get("features", []):
                    p = f.get("properties", {})
                    geom = f.get("geometry", {})
                    coords = [lon, lat]
                    if geom.get("type") in ["Polygon", "MultiPolygon"] and geom.get("coordinates"):
                        ring = geom["coordinates"][0][0] if geom["type"] == "MultiPolygon" else geom["coordinates"][0]
                        coords = [sum(c[0] for c in ring)/len(ring), sum(c[1] for c in ring)/len(ring)]
                    price = p.get("valeurfonc")
                    surface = p.get("sbati")
                    if price and surface:
                        pf, sf = float(price), float(surface)
                        if pf > 10000 and sf > 9:
                            listings.append({
                                "source": "DVF (transaction récente)",
                                "type": "transaction",
                                "date": str(p.get("datemut", "")),
                                "price": pf,
                                "surface": sf,
                                "price_per_sqm": round(pf / sf),
                                "rooms": p.get("nbpiece", 0) or 0,
                                "address": p.get("l_adresse", "") or f"Parcelle {p.get('l_idpar', '')}",
                                "latitude": coords[1],
                                "longitude": coords[0],
                                "status": "vendu",
                            })
    except Exception as e:
        logger.warning(f"Market listings fetch error: {e}")
    
    # Sort by date descending
    listings.sort(key=lambda x: x.get("date", ""), reverse=True)
    return listings

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
