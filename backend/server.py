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
from services import (
    scrape_bienici_listings, scrape_seloger_listing_url, lookup_castorus_url,
    scrape_castorus_zone_stats,
    calculate_spread, calculate_tension_index, calculate_market_coefficient,
    estimate_transaction_price_from_asking,
)

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
    city: str = ""
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
    listing_url: str = ""
    asking_price: float = 0.0
    castorus_manual: Optional[Dict[str, Any]] = None

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
        # Don't force "Paris" — allow petite couronne. Use Île-de-France region filter.
        query = q
        # If no city/postal hint in query, bias toward Paris region
        has_location_hint = any(kw in q.lower() for kw in ["paris", "neuilly", "boulogne", "clichy",
            "levallois", "issy", "montrouge", "puteaux", "courbevoie", "nanterre", "colombes",
            "montreuil", "saint-denis", "pantin", "vincennes", "saint-mandé", "ivry", "créteil",
            "92", "93", "94", "75"])
        if not has_location_hint:
            query = q + " Île-de-France"
        params = {"q": query, "limit": 8}
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
                postcode = props.get("postcode", "")
                # Filter: only Paris (75) + petite couronne (92, 93, 94)
                if postcode and not postcode.startswith(("75", "92", "93", "94")):
                    continue
                results.append({
                    "label": props.get("label", ""),
                    "street_number": props.get("housenumber", ""),
                    "street_name": props.get("street", ""),
                    "postal_code": postcode,
                    "city": props.get("city", ""),
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
                        # Build readable address
                        raw_addr = p.get("l_adresse", "") or ""
                        if not raw_addr or "PARCELLE" in raw_addr.upper():
                            num_v = p.get("l_numvoie", "") or ""
                            type_v = p.get("l_typvoie", "") or ""
                            nom_v = p.get("l_nomvoie", "") or ""
                            if nom_v:
                                raw_addr = f"{num_v} {type_v} {nom_v}".strip()
                            else:
                                raw_addr = f"Parcelle {p.get('l_idpar', '')}"
                        results.append({
                            "date": str(p.get("datemut", p.get("anneemut", ""))),
                            "price": price_f,
                            "surface": surface_f,
                            "rooms": p.get("nbpiece", 0) or 0,
                            "address": raw_addr,
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

# Average price/m² by zone (source: DVF 2023-2024 medians)
# Paris intramuros + Petite Couronne (92, 93, 94)
ZONE_AVG_PRICES = {
    # Paris intramuros
    "75001": 12800, "75002": 11900, "75003": 12100, "75004": 13200,
    "75005": 12500, "75006": 14800, "75007": 14200, "75008": 12600,
    "75009": 11200, "75010": 10400, "75011": 10600, "75012": 9800,
    "75013": 9500, "75014": 10200, "75015": 10000, "75016": 11500,
    "75017": 10800, "75018": 9600, "75019": 8500, "75020": 8800,
    # Hauts-de-Seine (92)
    "92200": 9500, "92100": 8200, "92300": 8500, "92130": 7500,
    "92120": 7200, "92170": 7400, "92240": 6800, "92800": 6800,
    "92400": 6500, "92000": 5500, "92500": 6200, "92600": 6500,
    "92110": 6200, "92700": 5500, "92320": 6200, "92140": 6800,
    "92150": 7000, "92210": 7500, "92310": 6500, "92330": 6800,
    "92350": 5800, "92160": 6200, "92340": 6000, "92260": 5800,
    "92190": 6500, "92360": 5500,
    # Seine-Saint-Denis (93)
    "93100": 6200, "93200": 4800, "93400": 5800, "93300": 4200,
    "93500": 5500, "93170": 5500, "93310": 5000, "93260": 5200,
    "93110": 4800, "93250": 4200, "93150": 4500, "93140": 4600,
    "93000": 4600, "93700": 4800,
    # Val-de-Marne (94)
    "94300": 8200, "94160": 8800, "94220": 7500, "94200": 5800,
    "94270": 6500, "94250": 5800, "94240": 6000, "94120": 5500,
    "94130": 6500, "94100": 6200, "94000": 4500, "94400": 5200,
    "94800": 5500, "94700": 5800, "94340": 5200, "94170": 5500,
}
ARRONDISSEMENT_AVG_PRICES = ZONE_AVG_PRICES

_COMMUNE_NAMES = {
    "92200": "Neuilly-sur-Seine", "92100": "Boulogne-Billancourt", "92300": "Levallois-Perret",
    "92130": "Issy-les-Moulineaux", "92120": "Montrouge", "92170": "Vanves", "92240": "Malakoff",
    "92800": "Puteaux", "92400": "Courbevoie", "92000": "Nanterre", "92500": "Rueil-Malmaison",
    "92600": "Asnières-sur-Seine", "92110": "Clichy", "92700": "Colombes", "92320": "Châtillon",
    "92140": "Clamart", "92150": "Suresnes", "92210": "Saint-Cloud", "92310": "Sèvres",
    "92330": "Sceaux", "92350": "Le Plessis-Robinson", "92160": "Antony", "92340": "Bourg-la-Reine",
    "92260": "Fontenay-aux-Roses", "92190": "Meudon", "92360": "Meudon-la-Forêt",
    "93100": "Montreuil", "93200": "Saint-Denis", "93400": "Saint-Ouen-sur-Seine",
    "93300": "Aubervilliers", "93500": "Pantin", "93170": "Bagnolet", "93310": "Le Pré-Saint-Gervais",
    "93260": "Les Lilas", "93110": "Rosny-sous-Bois", "93250": "Villemomble",
    "93150": "Le Blanc-Mesnil", "93140": "Bondy", "93000": "Bobigny", "93700": "Drancy",
    "94300": "Vincennes", "94160": "Saint-Mandé", "94220": "Charenton-le-Pont",
    "94200": "Ivry-sur-Seine", "94270": "Le Kremlin-Bicêtre", "94250": "Gentilly",
    "94240": "L'Haÿ-les-Roses", "94120": "Fontenay-sous-Bois", "94130": "Nogent-sur-Marne",
    "94100": "Saint-Maur-des-Fossés", "94000": "Créteil", "94400": "Vitry-sur-Seine",
    "94800": "Villejuif", "94700": "Maisons-Alfort", "94340": "Joinville-le-Pont",
    "94170": "Le Perreux-sur-Marne",
}

def _is_paris_intramuros(postal_code: str) -> bool:
    return postal_code.startswith("75") and len(postal_code) == 5

def _zone_display_label(postal_code: str) -> str:
    if _is_paris_intramuros(postal_code):
        return f"{postal_code[-2:]}e arrondissement"
    return _COMMUNE_NAMES.get(postal_code, postal_code)

def get_arrondissement_zone(postal_code: str) -> str:
    central = ["75001", "75002", "75003", "75004", "75005", "75006", "75007"]
    intermediate = ["75008", "75009", "75010", "75011", "75012", "75014", "75015", "75016", "75017"]
    premium_suburbs = ["92200", "92300", "94160", "92210"]
    mid_suburbs = ["92100", "92130", "92120", "92170", "92150", "94300", "94220", "93260", "93310"]
    if postal_code in central:
        return "central"
    elif postal_code in intermediate or postal_code in premium_suburbs:
        return "intermediate"
    elif postal_code in mid_suburbs:
        return "intermediate"
    elif postal_code.startswith(("92", "93", "94")):
        return "peripheral"
    return "peripheral"

# ─── Spatial Resolution Helpers ───

import re as re_mod

# Premium zones with higher price/m² ceiling
PREMIUM_ARRONDISSEMENTS = {"75006", "75007", "75008", "92200", "94160"}

def haversine_meters(lat1, lon1, lat2, lon2):
    """Distance in meters between two GPS points"""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ── Street Name Extraction & Classification ──

def _normalize_street(raw):
    """Normalize a street name for matching."""
    s = str(raw).upper().strip()
    s = s.strip("[]'\"")
    s = re_mod.sub(r'^\d+[\s,]*', '', s).strip()
    s = re_mod.sub(r'\s+\d+$', '', s).strip()
    return s

def _extract_street_from_user_address(addr):
    """Extract street name from '22 Avenue de Lamballe 75016 Paris' or '5 Rue du Bois 92200 Neuilly'."""
    s = str(addr).upper().strip()
    # Remove postal code + city suffix for Paris and petite couronne
    s = re_mod.sub(r'\b(75|92|93|94)\d{3}\b.*', '', s).strip()
    s = re_mod.sub(r'^\d+[\s,]*', '', s).strip()
    return s

def _street_names_match(street1, street2):
    """Check if two normalized street names refer to the same street."""
    if not street1 or not street2:
        return False
    s1 = _normalize_street(street1)
    s2 = _normalize_street(street2)
    if not s1 or not s2:
        return False
    if s1 == s2:
        return True
    if s1 in s2 or s2 in s1:
        return True
    def _core(s):
        for pfx in ["RUE DE LA ", "RUE DU ", "RUE DE L'", "RUE DES ", "RUE DE ",
                     "RUE D'", "RUE ", "AVENUE DE LA ", "AVENUE DU ", "AVENUE DE L'",
                     "AVENUE DES ", "AVENUE DE ", "AVENUE D'", "AVENUE ",
                     "BOULEVARD DE LA ", "BOULEVARD DU ", "BOULEVARD DES ", "BOULEVARD DE ", "BOULEVARD ",
                     "IMPASSE DE LA ", "IMPASSE DU ", "IMPASSE ", "VILLA ", "PASSAGE ", "PLACE DE LA ",
                     "PLACE DU ", "PLACE DES ", "PLACE DE ", "PLACE "]:
            if s.startswith(pfx):
                return s[len(pfx):]
        return s
    return _core(s1) == _core(s2)

def _classify_street_type(street_name):
    """
    Type A — Boulevard / Avenue (larges, commerçants, bruyants)
    Type B — Rue résidentielle moyenne
    Type C — Petite rue calme / impasse / villa / passage
    """
    s = _normalize_street(street_name)
    if not s:
        return "B"
    for pfx in ["AVENUE", "BOULEVARD", "COURS", "PLACE", "ESPLANADE", "QUAI"]:
        if s.startswith(pfx):
            return "A"
    for pfx in ["IMPASSE", "VILLA", "PASSAGE", "ALLEE", "ALLÉE", "CITE", "CITÉ",
                "SQUARE", "VOIE", "SENTIER", "COUR ", "HAMEAU", "CHEMIN"]:
        if s.startswith(pfx):
            return "C"
    return "B"

# ── Weighting Functions ──

def _distance_weight(d_meters):
    """Weight by proximity: 0m→1.0, 100m→0.67, 200m→0.50, 500m→0.29"""
    return 1.0 / (1.0 + d_meters / 200.0)

def _freshness_weight_months(date_str):
    """
    RÈGLE ABSOLUE: max 24 mois.
    0-6 mois=1.0, 6-12 mois=0.8, 12-18 mois=0.6, 18-24 mois=0.4. Au-delà=exclusion.
    """
    try:
        parts = str(date_str).split("-")
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 6
        ref_year, ref_month = 2026, 2
        age_months = (ref_year - year) * 12 + (ref_month - month)
    except (ValueError, TypeError, IndexError):
        return 0
    if age_months > 24:
        return 0
    if age_months <= 6:
        return 1.0
    if age_months <= 12:
        return 0.8
    if age_months <= 18:
        return 0.6
    return 0.4

def _surface_similarity_weight(comp_surface, target_surface):
    """
    SEGMENTATION: Coefficient de similarité surface (prompt consolidé).
    ±20% = 1.0, ±20-30% = 0.7, ±30-50% = 0.4, au-delà = exclusion (0).
    """
    if target_surface <= 0 or comp_surface <= 0:
        return 0
    ratio = abs(comp_surface - target_surface) / target_surface
    if ratio <= 0.2:
        return 1.0
    if ratio <= 0.3:
        return 0.7
    if ratio <= 0.5:
        return 0.4
    return 0

def _compute_relevance_score(distance_m, freshness_w, similarity_w, circle_bonus=0):
    """Score 0-100 combining distance, freshness, similarity + circle bonus."""
    dist_score = max(0, 100 - distance_m / 5)
    fresh_score = freshness_w * 100
    sim_score = similarity_w * 100
    base = dist_score * 0.35 + fresh_score * 0.3 + sim_score * 0.2 + circle_bonus
    return min(100, round(base))

def weighted_median_price(comparables):
    """Distance+freshness+similarity weighted median of price/m²"""
    if not comparables:
        return 0
    pairs = sorted([(c["price_per_sqm"], c.get("_weight", 1.0)) for c in comparables])
    total = sum(w for _, w in pairs)
    if total == 0:
        return pairs[len(pairs)//2][0]
    cumul = 0
    for val, w in pairs:
        cumul += w
        if cumul >= total / 2:
            return val
    return pairs[-1][0]

def _parse_dvf_feature_raw(f, ref_lat, ref_lon, max_radius):
    """Parse a single DVF GeoJSON feature into raw dict with street data."""
    p = f.get("properties", {})
    geom = f.get("geometry", {})
    coords = None
    if geom.get("type") == "Polygon" and geom.get("coordinates"):
        ring = geom["coordinates"][0]
        coords = [sum(c[0] for c in ring)/len(ring), sum(c[1] for c in ring)/len(ring)]
    elif geom.get("type") == "MultiPolygon" and geom.get("coordinates"):
        ring = geom["coordinates"][0][0]
        coords = [sum(c[0] for c in ring)/len(ring), sum(c[1] for c in ring)/len(ring)]
    if not coords:
        return None
    price = p.get("valeurfonc")
    surface = p.get("sbati")
    if not price or not surface:
        return None
    pf, sf = float(price), float(surface)
    if pf <= 10000 or sf <= 0:
        return None
    clat, clon = coords[1], coords[0]
    d = haversine_meters(ref_lat, ref_lon, clat, clon)
    if d > max_radius:
        return None
    date_str = str(p.get("datemut", p.get("anneemut", "")))
    raw_address = p.get("l_adresse", "") or ""
    # Try to build a readable address from available fields
    if raw_address and "PARCELLE" not in raw_address.upper() and raw_address.strip():
        display_address = raw_address
    else:
        # Use l_adresse fields if available, fallback to parcel ID
        num_voie = p.get("l_numvoie", "") or ""
        type_voie = p.get("l_typvoie", "") or ""
        nom_voie = p.get("l_nomvoie", "") or ""
        if nom_voie:
            display_address = f"{num_voie} {type_voie} {nom_voie}".strip()
        else:
            parcel_ids = p.get("l_idpar", "")
            display_address = f"Parcelle {parcel_ids}" if parcel_ids else "Adresse non renseignée"
    street = _normalize_street(display_address)
    return {
        "date": date_str, "price": pf, "surface": sf,
        "rooms": p.get("nbpiece", 0) or 0,
        "address": display_address,
        "postal_code": str(p.get("l_codinsee", ""))[:5],
        "latitude": clat, "longitude": clon,
        "price_per_sqm": round(pf / sf), "distance_m": round(d),
        "_parcel_id": p.get("l_idpar", ""),
        "_street_name": street, "_street_type": _classify_street_type(street),
    }

# ── Concentric Circle Logic ──

def _assign_circle(comp, target_street, target_street_type):
    """
    C1 — Même rue (poids x3)
    C2 — Même type de rue dans 200m (poids x1.5)
    C3 — Rayon élargi (poids x1 si même type, x0.3 si type très différent)

    Note: L'API DVF Cerema retourne souvent des parcelles cadastrales au lieu
    de noms de rue. Quand l'adresse est une parcelle, utiliser la distance
    comme heuristique: < 50m ≈ même rue, < 150m ≈ rue voisine.
    """
    comp_street = comp.get("_street_name", "")
    comp_type = comp.get("_street_type", "B")
    distance = comp.get("distance_m", 999)
    is_parcel = "PARCELLE" in comp_street.upper() or not comp_street

    # Si on a un vrai nom de rue, matching exact
    if not is_parcel and target_street:
        if _street_names_match(comp_street, target_street):
            return 1, 3.0
        if distance <= 200 and comp_type == target_street_type:
            return 2, 1.5
        if comp_type == target_street_type:
            return 3, 1.0
        type_diff = abs(ord(comp_type) - ord(target_street_type))
        if type_diff >= 2:
            return 3, 0.3
        return 3, 0.6

    # Heuristique distance pour parcelles sans nom de rue
    if distance <= 50:
        return 1, 2.5  # Très proche = probable même rue
    if distance <= 150:
        return 2, 1.5  # Rue voisine
    return 3, 1.0

def _filter_and_score_comparables(raw_comps, target_surface, postal_code,
                                   target_street="", target_street_type="B",
                                   excluded_ids=None):
    """NETTOYAGE + CERCLES CONCENTRIQUES + SCORING. Returns (included, excluded, circle_stats)."""
    excluded_ids = set(excluded_ids or [])
    is_premium = postal_code in PREMIUM_ARRONDISSEMENTS
    price_max = 25000 if is_premium else 20000
    included, excluded = [], []
    seen_parcels = {}
    for c in raw_comps:
        comp_id = f"{c['address']}_{c['date']}_{c['price']}"
        reasons = []
        if comp_id in excluded_ids:
            reasons.append("Exclu manuellement")
            excluded.append({**c, "exclusion_reasons": reasons, "included": False, "circle": 0})
            continue
        fw = _freshness_weight_months(c["date"])
        if fw == 0:
            reasons.append("Transaction > 24 mois")
        psqm = c["price_per_sqm"]
        if psqm < 5000:
            reasons.append(f"Prix/m² trop bas ({psqm}€) — probable cave/parking/viager")
        if psqm > price_max:
            reasons.append(f"Prix/m² trop élevé ({psqm}€ > {price_max}€)")
        if c["surface"] < 20:
            reasons.append(f"Surface trop petite ({c['surface']}m²) — chambre de service")
        sim_w = _surface_similarity_weight(c["surface"], target_surface)
        if sim_w == 0:
            reasons.append(f"Surface trop éloignée ({c['surface']}m² vs {target_surface}m² cible)")
        pid = c.get("_parcel_id", "")
        if pid:
            key = f"{pid}_{c['date'][:10]}_{int(c['price'])}"
            if key in seen_parcels:
                reasons.append("Doublon — même parcelle/date/prix (probable lot en bloc)")
            else:
                seen_parcels[key] = True
        if reasons:
            excluded.append({**c, "exclusion_reasons": reasons, "included": False, "circle": 0})
        else:
            circle, circle_mult = _assign_circle(c, target_street, target_street_type)
            dw = _distance_weight(c["distance_m"])
            combined_w = round(dw * fw * sim_w * circle_mult, 4)
            circle_bonus = 15 if circle == 1 else (5 if circle == 2 else 0)
            relevance = _compute_relevance_score(c["distance_m"], fw, sim_w, circle_bonus)
            included.append({
                **c, "_weight": combined_w, "_freshness_w": round(fw, 3),
                "_similarity_w": round(sim_w, 2), "_circle_mult": circle_mult,
                "circle": circle, "relevance_score": relevance,
                "included": True, "exclusion_reasons": [],
            })
    if len(included) >= 5:
        prices = [c["price_per_sqm"] for c in included]
        mean_p = sum(prices) / len(prices)
        std_p = (sum((p - mean_p)**2 for p in prices) / len(prices)) ** 0.5
        # Also use IQR for more robust filtering
        sorted_prices = sorted(prices)
        q1_idx = len(sorted_prices) // 4
        q3_idx = 3 * len(sorted_prices) // 4
        q1 = sorted_prices[q1_idx]
        q3 = sorted_prices[q3_idx]
        iqr = q3 - q1
        iqr_lower = q1 - 1.5 * iqr
        iqr_upper = q3 + 1.5 * iqr
        # Use the tighter of the two methods
        if std_p > 0:
            std_lower, std_upper = mean_p - 1.5 * std_p, mean_p + 1.5 * std_p
            lower = max(iqr_lower, std_lower)
            upper = min(iqr_upper, std_upper)
        else:
            lower, upper = iqr_lower, iqr_upper
        new_included = []
        for c in included:
            if c["price_per_sqm"] < lower or c["price_per_sqm"] > upper:
                c["exclusion_reasons"] = [f"Outlier ({c['price_per_sqm']}€/m² hors [{int(lower)}-{int(upper)}])"]
                c["included"] = False
                c["circle"] = 0
                excluded.append(c)
            else:
                new_included.append(c)
        included = new_included
    included.sort(key=lambda x: (x.get("circle", 3), -x.get("relevance_score", 0)))
    excluded.sort(key=lambda x: x.get("distance_m", 999))
    c1 = len([c for c in included if c.get("circle") == 1])
    c2 = len([c for c in included if c.get("circle") == 2])
    c3 = len([c for c in included if c.get("circle") == 3])
    reliability = "HAUTE" if c1 >= 8 else ("MOYENNE" if c1 + c2 >= 5 else "BASSE")
    circle_stats = {"circle_1_count": c1, "circle_2_count": c2, "circle_3_count": c3,
                    "reliability": reliability, "target_street": target_street, "target_street_type": target_street_type}
    return included, excluded, circle_stats

def _compute_street_coefficient(included, target_street):
    """Coefficient de rue = médiane même rue / médiane zone."""
    if not included or not target_street:
        return 1.0, "Neutre (données insuffisantes)"
    same = [c for c in included if _street_names_match(c.get("_street_name", ""), target_street)]
    if len(same) < 3:
        return 1.0, f"Neutre — {len(same)} transaction(s) sur la rue"
    sm = weighted_median_price(same)
    am = weighted_median_price(included)
    if am == 0:
        return 1.0, "Neutre"
    coeff = round(sm / am, 3)
    return coeff, f"Coeff. rue : {coeff:.2f} (rue {sm}€/m² vs zone {am}€/m²)"


async def _fetch_dvf_raw(lat, lon, radius):
    """Fetch raw DVF data from Cerema API for a given radius."""
    import asyncio
    raw = []
    delta = radius / 111000.0
    bbox = f"{lon-delta},{lat-delta},{lon+delta},{lat+delta}"
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=15) as cl:
                resp = await cl.get(
                    "https://apidf-preprod.cerema.fr/dvf_opendata/geomutations/",
                    params={"in_bbox": bbox, "page_size": 100, "anneemut_min": 2024}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for feat in data.get("features", []):
                        c = _parse_dvf_feature_raw(feat, lat, lon, radius)
                        if c:
                            raw.append(c)
                    return raw
                elif resp.status_code == 503:
                    await asyncio.sleep(1)
                    continue
                else:
                    return raw
        except Exception:
            await asyncio.sleep(1)
    return raw


async def fetch_dvf_progressive(lat, lon, target_surface=70, postal_code="75001",
                                 target_street="", min_comps=8, excluded_ids=None):
    """
    HIÉRARCHIE DES CERCLES CONCENTRIQUES:
      C1 — Même rue (poids x3)
      C2 — Même type de rue dans 200m (poids x1.5)
      C3 — Rayon élargi 300-500m (poids x1)
    Returns (included, excluded, radius, circle_stats, street_coeff, street_coeff_detail).
    """
    target_street_type = _classify_street_type(target_street)
    radii = [200, 300, 500]
    included, excluded, circle_stats = [], [], {}

    for radius in radii:
        raw = await _fetch_dvf_raw(lat, lon, radius)
        included, excluded, circle_stats = _filter_and_score_comparables(
            raw, target_surface, postal_code,
            target_street=target_street, target_street_type=target_street_type,
            excluded_ids=excluded_ids,
        )
        if len(included) >= min_comps:
            sc, scd = _compute_street_coefficient(included, target_street)
            return included, excluded, radius, circle_stats, sc, scd

    sc, scd = _compute_street_coefficient(included, target_street)
    return included, excluded, radii[-1], circle_stats, sc, scd

def compute_micro_score(comparables, arr_avg, postal_code=""):
    """Compute micro-location score from local DVF data"""
    zone_label = "la zone" if not postal_code else _zone_display_label(postal_code)
    if not comparables:
        return {"score": 50, "detail": "Données DVF insuffisantes pour scorer", "local_premium_pct": 0, "density_300m": 0, "price_homogeneity": 50, "local_median_sqm": 0}
    local_median = weighted_median_price(comparables)
    premium_pct = ((local_median - arr_avg) / arr_avg * 100) if arr_avg > 0 else 0
    close = [c for c in comparables if c.get("distance_m", 999) <= 300]
    density = len(close)
    prices = [c["price_per_sqm"] for c in comparables]
    mean_p = sum(prices) / len(prices)
    std_p = (sum((p - mean_p)**2 for p in prices) / len(prices)) ** 0.5
    cv = std_p / mean_p if mean_p > 0 else 1
    homogeneity = max(0, min(100, int(100 * (1 - cv))))
    score = int(50 + premium_pct * 1.5)
    score = max(10, min(100, score))
    parts = []
    if premium_pct > 5:
        parts.append(f"Micro-localisation premium (+{premium_pct:.0f}% vs moyenne {zone_label})")
    elif premium_pct < -5:
        parts.append(f"Micro-localisation en retrait ({premium_pct:.0f}% vs moyenne {zone_label})")
    else:
        parts.append(f"Micro-localisation dans la moyenne ({zone_label})")
    parts.append(f"{density} transaction(s) à moins de 300m")
    return {
        "score": score,
        "detail": ". ".join(parts),
        "local_premium_pct": round(premium_pct, 1),
        "density_300m": density,
        "price_homogeneity": homogeneity,
        "local_median_sqm": round(local_median),
    }

async def geocode_address(address_text):
    """Geocode an address using api-adresse.data.gouv.fr"""
    try:
        async with httpx.AsyncClient(timeout=10) as cl:
            resp = await cl.get("https://api-adresse.data.gouv.fr/search/", params={"q": address_text, "limit": 1})
            if resp.status_code == 200:
                feats = resp.json().get("features", [])
                if feats:
                    coords = feats[0]["geometry"]["coordinates"]
                    props = feats[0]["properties"]
                    return {"latitude": coords[1], "longitude": coords[0], "postal_code": props.get("postcode", ""), "label": props.get("label", ""), "street": props.get("street", props.get("name", ""))}
    except Exception as e:
        logger.warning(f"Geocode error: {e}")
    return None

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

    # 1. Fetch DVF comparables via progressive radius search (200m → 300m → 500m)
    # HIÉRARCHIE: Cercle 1 (même rue x3) → Cercle 2 (même type 200m x1.5) → Cercle 3
    comparables = []
    excluded_comparables = []
    search_radius = 200
    circle_stats = {}
    street_coeff = 1.0
    street_coeff_detail = ""
    target_street = _extract_street_from_user_address(loc.address or "")
    try:
        comparables, excluded_comparables, search_radius, circle_stats, street_coeff, street_coeff_detail = await fetch_dvf_progressive(
            loc.latitude, loc.longitude,
            target_surface=chars.surface_carrez,
            postal_code=loc.postal_code,
            target_street=target_street,
            min_comps=8,
        )
    except Exception as e:
        logger.warning(f"DVF progressive search error: {e}")

    # RÈGLE ABSOLUE: prix de base = médiane pondérée DVF locale
    # Appliquer le coefficient de rue si les comparables viennent d'autres rues
    if comparables:
        raw_median = weighted_median_price(comparables)
        # Si le coefficient de rue est significatif et qu'on a assez de data, corriger
        if street_coeff != 1.0 and abs(street_coeff - 1.0) > 0.05:
            base_price_sqm = round(raw_median * street_coeff)
        else:
            base_price_sqm = raw_median
    else:
        base_price_sqm = ARRONDISSEMENT_AVG_PRICES.get(loc.postal_code, 10500)

    reliability = circle_stats.get("reliability", "BASSE")
    confidence = min(95, 25 + len(comparables) * 2 + (15 if search_radius <= 300 else 5)
                     + (10 if reliability == "HAUTE" else (5 if reliability == "MOYENNE" else 0)))

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
            hyp = f"Le rez-de-chaussée subit une décote de {abs(floor_adj)}% car il est exposé au bruit de la rue, au manque de luminosité et aux problèmes de sécurité. Les RDC se vendent en moyenne 10 à 15% moins cher que les étages intermédiaires."
        elif loc.floor >= 6 and not bldg.elevator:
            hyp = f"Un {loc.floor}e étage sans ascenseur entraîne une forte décote ({abs(floor_adj)}%) car l'accessibilité réduit considérablement le bassin d'acheteurs potentiels (familles, personnes âgées). Chaque étage supplémentaire sans ascenseur au-delà du 4e amplifie la décote."
        elif loc.floor >= 6 and bldg.elevator:
            hyp = f"Le dernier étage avec ascenseur bénéficie d'une surcote de +{floor_adj}% : vue dégagée, calme supérieur, moins de nuisances sonores des voisins du dessus. C'est un des critères les plus valorisés en région parisienne."
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
        hyp = f"Une exposition nord mono-orientée entraîne une décote de {abs(adj)}% car le bien reçoit très peu de lumière directe. Les acheteurs sont particulièrement sensibles à la luminosité, surtout dans les rues étroites. Cela se traduit aussi par des charges de chauffage plus élevées."
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
        hyp = f"Un jardin privatif de {chars.exterior_surface}m² est exceptionnel et apporte +{adj}%. C'est l'un des biens les plus recherchés du marché. La rareté de l'offre (< 2% des biens) crée une prime significative, surtout dans les zones centrales."
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
        hyp = f"Une place de stationnement en zone {zone} vaut environ {int(p_adj):,}€. Dans les zones centrales, la rareté des places pousse les prix jusqu'à 50 000€. Un parking sécurise aussi le financement bancaire et facilite la revente. Le type '{chars.parking}' est intégré comme un montant forfaitaire ajouté au prix."
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

    # Market position: compare to LOCAL DVF median (not arrondissement average!)
    # RÈGLE: La moyenne d'arrondissement n'est PAS une référence valide.
    # Le 16e va de 8000€/m² (Auteuil Sud) à 15000€/m² (Trocadéro).
    final_sqm = adjusted_price_sqm
    local_ref = base_price_sqm if comparables else arr_avg
    local_ref_label = f"médiane DVF locale ({search_radius}m)" if comparables else f"moyenne {zone_label} (fallback)"
    diff_vs_local_pct = ((final_sqm - local_ref) / local_ref * 100) if local_ref > 0 else 0
    if diff_vs_local_pct > 15:
        market_position = {"label": "++", "description": "Nettement au-dessus du marché local", "color": "green"}
    elif diff_vs_local_pct > 5:
        market_position = {"label": "+", "description": "Au-dessus du marché local", "color": "green"}
    elif diff_vs_local_pct > -5:
        market_position = {"label": "=", "description": "Dans la moyenne du marché local", "color": "neutral"}
    elif diff_vs_local_pct > -15:
        market_position = {"label": "-", "description": "En-dessous du marché local", "color": "red"}
    else:
        market_position = {"label": "--", "description": "Nettement en-dessous du marché local", "color": "red"}
    market_position["diff_pct"] = round(diff_vs_local_pct, 1)
    market_position["local_ref_sqm"] = round(local_ref)
    market_position["local_ref_label"] = local_ref_label
    market_position["arr_avg"] = arr_avg
    market_position["arr_avg_note"] = f"Moyenne {zone_label} : {arr_avg}€/m² (indicatif uniquement — écarts intra-zone > 50%)"
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

    # Micro-location score
    micro_score = compute_micro_score(comparables, arr_avg, postal_code=loc.postal_code)

    zone_label = _zone_display_label(loc.postal_code)
    is_paris = _is_paris_intramuros(loc.postal_code)

    # ═══ COUCHE 2: Marché actif (annonces en cours) ═══
    active_market = {}
    try:
        surface_target = chars.surface_carrez or 50

        # Scrape active listings from BienIci
        active_listings = await scrape_bienici_listings(
            loc.postal_code,
            surface_min=max(15, int(surface_target * 0.5)),
            surface_max=int(surface_target * 2),
            rooms_min=max(1, chars.rooms - 1),
            rooms_max=chars.rooms + 2,
        )

        # Also get Castorus zone stats for market tension
        castorus_zone = await scrape_castorus_zone_stats(loc.postal_code)

        # Calculate spread (annonces vs DVF)
        spread_data = calculate_spread(comparables, active_listings, surface_target,
                                        postal_code=loc.postal_code)

        # Castorus lookup if listing URL provided
        castorus_data = None
        if req.listing_url:
            castorus_data = await lookup_castorus_url(req.listing_url)

        # Use manual Castorus data if provided (fallback)
        if not castorus_data and req.castorus_manual:
            castorus_data = req.castorus_manual

        # Enrich castorus_data with zone-level stats if individual data missing
        if not castorus_data and castorus_zone:
            castorus_data = {
                "source": "castorus_zone_aggregate",
                "days_on_market": castorus_zone.get("avg_dom"),
                "zone_pct_drops": castorus_zone.get("pct_with_drops"),
            }

        # Calculate tension index
        tension_data = calculate_tension_index(active_listings, comparables, castorus_data,
                                                zone=zone)

        # Calculate market coefficient (Couche 2)
        market_coeff_data = calculate_market_coefficient(spread_data, tension_data, castorus_data)
        market_coefficient = market_coeff_data["coefficient"]

        # Apply Couche 2 to prices
        total_price_median = round(total_price_median * market_coefficient)
        total_price_low = round(total_price_low * market_coefficient)
        total_price_high = round(total_price_high * market_coefficient)
        adjusted_price_sqm = round(adjusted_price_sqm * market_coefficient)

        # If asking price provided, estimate transaction price
        transaction_estimate = None
        if req.asking_price > 0:
            transaction_estimate = estimate_transaction_price_from_asking(
                req.asking_price, spread_data["spread_pct"],
                tension_data["score"], castorus_data
            )

        # Build active market summary for response
        listing_summary = []
        for listing_item in active_listings[:15]:
            listing_summary.append({
                "price": listing_item.get("price"),
                "price_per_sqm": listing_item.get("price_per_sqm"),
                "surface": listing_item.get("surface"),
                "rooms": listing_item.get("rooms"),
                "neighborhood": listing_item.get("neighborhood", ""),
                "floor": listing_item.get("floor"),
            })

        active_market = {
            "listings_count": len(active_listings),
            "listings_sample": listing_summary,
            "spread": spread_data,
            "tension": tension_data,
            "market_coefficient": market_coeff_data,
            "castorus": castorus_data,
            "transaction_estimate": transaction_estimate,
            "listing_median_sqm": spread_data.get("listing_median_sqm", 0),
        }
        logger.info(f"Couche 2: {len(active_listings)} annonces, spread={spread_data['spread_pct']}%, tension={tension_data['score']}/100, coeff={market_coefficient}")
    except Exception as e:
        logger.error(f"Couche 2 error (non-blocking): {e}")
        active_market = {"error": str(e), "listings_count": 0}

    # Strip internal fields from comparables for response
    def _clean_comp(c):
        return {k: v for k, v in c.items() if not k.startswith("_")}

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
        comparables=[_clean_comp(c) for c in comparables[:25]],
        location_scores=location_scores,
        risks=risks,
        market_data={
            "base_price_sqm": round(base_price_sqm),
            "arrondissement_avg_sqm": arr_avg,
            "arrondissement": loc.postal_code,
            "zone": zone,
            "zone_label": zone_label,
            "is_paris": is_paris,
            "total_comparables": len(comparables),
            "total_excluded": len(excluded_comparables),
            "search_radius_m": search_radius,
            "adjustment_pct": round(total_pct_adjustment, 1),
            "adjustment_flat": round(total_flat_adjustment),
            "base_source": f"DVF Cerema — médiane pondérée ({search_radius}m, 24 mois max, filtré)" if comparables else f"Moyenne {zone_label} (fallback — aucune transaction DVF trouvée)",
            "comparables_period": "24 derniers mois",
            "market_position": market_position,
            "micro_score": micro_score,
            "reliability": reliability,
            "street_coefficient": street_coeff,
            "street_coefficient_detail": street_coeff_detail,
        }
    )
    resp = result.model_dump()
    # Add excluded comparables for transparency
    resp["excluded_comparables"] = [_clean_comp(c) for c in excluded_comparables[:20]]
    # Circle stats and street coefficient
    resp["circle_stats"] = circle_stats
    resp["street_coefficient"] = {"value": street_coeff, "detail": street_coeff_detail}
    # Cross-calibration warning
    resp["cross_calibration_warning"] = f"Vérifiez la cohérence de l'estimation avec les annonces en cours sur SeLoger/LeBonCoin autour de {loc.address or 'cette adresse'} (prix affichés = +5 à 10% vs prix de transaction réel). La moyenne de la zone ({arr_avg}€/m² pour {zone_label}) n'est PAS une référence valide — les écarts intra-zone peuvent dépasser 50%."
    # Couche 2 — Active market data
    resp["active_market"] = active_market
    return resp

# ─── Standalone Market Data Endpoint ───

class MarketDataRequest(BaseModel):
    postal_code: str
    surface: float = 60
    rooms: int = 3
    listing_url: str = ""
    asking_price: float = 0
    castorus_manual: Optional[Dict[str, Any]] = None

@api_router.post("/market/active")
async def get_active_market(req: MarketDataRequest):
    """Get active market data (listings, spread, tension) for a zone."""
    active_listings = await scrape_bienici_listings(
        req.postal_code,
        surface_min=max(15, int(req.surface * 0.5)),
        surface_max=int(req.surface * 2),
        rooms_min=max(1, req.rooms - 1),
        rooms_max=req.rooms + 2,
    )

    # Get DVF comparables for spread calculation (use cached data if possible)
    dvf_comps = []
    doc = await db.valuations.find_one(
        {"request.location.postal_code": req.postal_code},
        {"_id": 0, "comparables": 1},
        sort=[("created_at", -1)]
    )
    if doc:
        dvf_comps = doc.get("comparables", [])

    spread = calculate_spread(dvf_comps, active_listings, req.surface,
                              postal_code=req.postal_code)

    castorus_data = None
    if req.listing_url:
        castorus_data = await lookup_castorus_url(req.listing_url)
    if not castorus_data and req.castorus_manual:
        castorus_data = req.castorus_manual

    zone = get_arrondissement_zone(req.postal_code)
    tension = calculate_tension_index(active_listings, dvf_comps, castorus_data, zone=zone)
    market_coeff = calculate_market_coefficient(spread, tension, castorus_data)

    transaction_estimate = None
    if req.asking_price > 0:
        transaction_estimate = estimate_transaction_price_from_asking(
            req.asking_price, spread["spread_pct"], tension["score"], castorus_data
        )

    listings_sample = []
    for l in active_listings[:20]:
        listings_sample.append({
            "price": l.get("price"),
            "price_per_sqm": l.get("price_per_sqm"),
            "surface": l.get("surface"),
            "rooms": l.get("rooms"),
            "neighborhood": l.get("neighborhood", ""),
            "floor": l.get("floor"),
        })

    return {
        "postal_code": req.postal_code,
        "zone_label": _zone_display_label(req.postal_code),
        "listings_count": len(active_listings),
        "listings_sample": listings_sample,
        "spread": spread,
        "tension": tension,
        "market_coefficient": market_coeff,
        "castorus": castorus_data,
        "transaction_estimate": transaction_estimate,
    }

# ─── Recalculate with manual exclusions ───

class RecalculateRequest(BaseModel):
    valuation_id: str
    excluded_comparable_ids: List[str] = Field(default_factory=list)

@api_router.post("/valuation/recalculate")
async def recalculate_valuation(req: RecalculateRequest):
    """Recalculate an estimation after user manually excludes some comparables."""
    doc = await db.valuations.find_one({"id": req.valuation_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Estimation introuvable")

    orig_req = doc.get("request", {})
    loc = orig_req.get("location", {})
    chars = orig_req.get("characteristics", {})
    lat = loc.get("latitude", 48.8566)
    lon = loc.get("longitude", 2.3522)
    surface = chars.get("surface_carrez", 70)
    postal = loc.get("postal_code", "75001")

    target_street = _extract_street_from_user_address(loc.get("address", ""))

    # Re-fetch DVF with exclusions
    included, excluded, radius, cstats, sc, scd = await fetch_dvf_progressive(
        lat, lon, target_surface=surface, postal_code=postal,
        target_street=target_street,
        min_comps=5, excluded_ids=req.excluded_comparable_ids,
    )

    if not included:
        raise HTTPException(status_code=400, detail="Plus aucun comparable valide après exclusion")

    new_raw_median = weighted_median_price(included)
    if sc != 1.0 and abs(sc - 1.0) > 0.05:
        new_median = round(new_raw_median * sc)
    else:
        new_median = new_raw_median
    arr_avg = ARRONDISSEMENT_AVG_PRICES.get(postal, 10500)
    pct_adj = doc.get("market_data", {}).get("adjustment_pct", 0)
    flat_adj = doc.get("market_data", {}).get("adjustment_flat", 0)

    adjusted_sqm = new_median * (1 + pct_adj / 100)
    new_price_median = adjusted_sqm * surface + flat_adj
    spread = 0.08 if len(included) > 10 else 0.12

    def _clean(c):
        return {k: v for k, v in c.items() if not k.startswith("_")}

    return {
        "new_base_price_sqm": round(new_median),
        "new_price_per_sqm_median": round(adjusted_sqm),
        "new_price_median": round(new_price_median),
        "new_price_low": round(new_price_median * (1 - spread)),
        "new_price_high": round(new_price_median * (1 + spread)),
        "comparables_count": len(included),
        "excluded_count": len(excluded),
        "search_radius_m": radius,
        "circle_stats": cstats,
        "street_coefficient": {"value": sc, "detail": scd},
        "comparables": [_clean(c) for c in included[:25]],
        "excluded_comparables": [_clean(c) for c in excluded[:20]],
    }


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

# ─── Listing Sheet Analysis (AI-powered) ───

EXTRACTION_PROMPT = """Tu es un expert en immobilier dans la région parisienne (Paris + petite couronne). Analyse cette fiche d'agence immobilière et extrais TOUTES les informations disponibles dans un JSON structuré.

IMPORTANT: 
- Extrais EXACTEMENT ce qui est écrit, sans inventer de données
- Pour les champs manquants, mets null
- Le prix demandé doit être le prix HAI (honoraires inclus) si disponible
- Distingue bien prix du bien et prix du parking si séparé

Retourne UNIQUEMENT un JSON valide avec cette structure (pas de texte avant ou après):
{
  "extracted": {
    "address": "adresse complète ou null",
    "postal_code": "code postal (75xxx, 92xxx, 93xxx, 94xxx)",
    "arrondissement": "numéro d'arrondissement (Paris) ou nom de commune (banlieue)",
    "neighborhood": "quartier mentionné ou null",
    "asking_price": prix demandé en euros (nombre),
    "asking_price_detail": "détail (HAI, hors honoraires, etc.)",
    "price_per_sqm_asked": prix au m² demandé ou null,
    "parking_price": prix du parking si séparé ou 0,
    "surface_carrez": surface loi carrez en m² (nombre),
    "surface_habitable": surface habitable ou null,
    "rooms": nombre de pièces principales (nombre),
    "bedrooms": nombre de chambres (nombre),
    "bathrooms": nombre de salles de bain/eau (nombre),
    "property_type": "appartement/duplex/triplex/loft/etc",
    "floor": étage principal (nombre),
    "total_floors": nombre d'étages de l'immeuble ou null,
    "elevator": true/false/null,
    "exposure": "nord/sud/est/ouest/multi/null",
    "view": "description de la vue ou null",
    "exterior_type": "balcon/terrasse/jardin/loggia/aucun",
    "exterior_surface": surface extérieure en m² ou 0,
    "exterior_count": nombre de balcons/terrasses ou 0,
    "ceiling_height": hauteur sous plafond en mètres ou null,
    "parking": "type de parking ou aucun",
    "cave": true/false,
    "cave_count": nombre de caves ou 0,
    "general_state": "a_renover/rafraichissement/bon_etat/refait_neuf/luxe",
    "construction_year": année de construction ou null,
    "building_type": "pierre_taille/brique/beton/moderne/standing",
    "dpe": "A/B/C/D/E/F/G ou null",
    "dpe_value": valeur kWh/m²/an ou null,
    "ges": "A/B/C/D/E/F/G ou null",
    "annual_charges": charges annuelles en euros ou 0,
    "property_tax": taxe foncière annuelle ou 0,
    "total_lots": nombre de lots copro ou null,
    "concierge": true/false/null,
    "heating": "type de chauffage",
    "windows": "type de vitrage",
    "agency_name": "nom de l'agence",
    "agency_fees_detail": "détail des honoraires",
    "notable_features": ["liste des points forts mentionnés"],
    "notable_defects": ["liste des points faibles ou travaux à prévoir"]
  },
  "summary": "résumé en 2-3 phrases du bien"
}"""

ANALYSIS_PROMPT_TEMPLATE = """Tu es un expert en valorisation immobilière parisienne. Tu as extrait les caractéristiques suivantes d'une fiche d'agence:

{extracted_json}

Le prix demandé est de {asking_price}€ pour {surface}m² soit {price_sqm}€/m².

DONNÉES DE MARCHÉ LOCALES (transactions DVF réelles, 24 derniers mois uniquement, filtrées):
- Médiane pondérée locale (distance+fraîcheur+similarité) dans un rayon de {search_radius}m : {local_median}€/m²
- Comparables retenus : {num_comparables} (exclus : {num_excluded})
- Répartition cercles : C1 (même rue)={c1_count}, C2 (même type 200m)={c2_count}, C3 (élargi)={c3_count}
- Fiabilité : {reliability}
- Coefficient de rue : {street_coeff} — {street_coeff_detail}
- Moy. zone : {arr_avg}€/m² (PAS une référence — écarts intra-zone > 50%)
- Prime micro-localisation : {local_premium}% vs arrondissement

IMPORTANT: Base-toi EXCLUSIVEMENT sur la médiane locale DVF ({local_median}€/m²), corrigée par le coefficient de rue si applicable.

SEUILS DE VERDICT (OBLIGATOIRE):
- Écart < 5% → "prix_juste" — "PRIX MARCHÉ — bien positionné"
- 5-10% en-dessous → "prix_juste" — "LÉGÈREMENT SOUS LE MARCHÉ — marge de négociation limitée"
- 5-10% au-dessus → "surévalué" — "LÉGÈREMENT AU-DESSUS DU MARCHÉ — négociable"
- 10-15% → "surévalué" / "sous-évalué" — "vérifier les données"
- > 15% → "très_surévalué" / "sous-évalué" — "ALERTE : écart anormal, vérification croisée obligatoire — ne PAS conclure à une opportunité sans vérification, l'explication la plus probable est une erreur de comparables ou des informations manquantes"

Si fiabilité BASSE: ajouter un warning dans le verdict mentionnant que l'estimation est indicative.

ANALYSE DE PRIX — Réponds en JSON UNIQUEMENT:
{{
  "price_opinion": "sous-évalué" / "prix_juste" / "surévalué" / "très_surévalué",
  "price_opinion_icon": "--" / "-" / "=" / "+" / "++",
  "price_opinion_detail": "description courte du verdict (ex: PRIX MARCHÉ, LÉGÈREMENT AU-DESSUS, ALERTE...)",
  "estimated_fair_price_low": estimation basse (nombre),
  "estimated_fair_price_high": estimation haute (nombre),
  "estimated_fair_price_sqm": estimation prix/m² juste (nombre),
  "arguments_for": ["3-5 arguments qui justifient un prix élevé"],
  "arguments_against": ["3-5 arguments qui justifient un prix plus bas"],
  "negotiation_tips": ["2-3 conseils de négociation spécifiques à ce bien"],
  "undervaluation_warning": "string ou null — warning si sous-évaluation > 15%",
  "verdict": "paragraphe de 4-5 lignes avec ton verdict argumenté basé EXCLUSIVEMENT sur la médiane locale DVF et le coefficient de rue. Mentionne l'écart en %. Si écart > 15%, dis EXPLICITEMENT que cela suggère soit une erreur de comparables soit des informations manquantes."
}}"""

@api_router.post("/listing/analyze")
async def analyze_listing(file: UploadFile = File(...)):
    """Analyze a real estate agency listing sheet using AI"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
    import tempfile, json as json_mod

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    if ext not in ["pdf", "jpg", "jpeg", "png", "webp"]:
        raise HTTPException(status_code=400, detail="Format supporté : PDF, JPG, PNG")

    file_data = await file.read()
    if len(file_data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 20Mo)")

    # Save to temp file for Gemini
    mime_map = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime = mime_map.get(ext, "application/octet-stream")

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(file_data)
        tmp_path = tmp.name

    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="LLM key not configured")

        # Step 1: Extract data from the listing
        chat = LlmChat(
            api_key=api_key,
            session_id=f"listing-{uuid.uuid4()}",
            system_message="Tu es un expert immobilier région parisienne (Paris + petite couronne). Tu extrais des données structurées de fiches d'agences immobilières. Réponds UNIQUEMENT en JSON valide."
        ).with_model("gemini", "gemini-2.5-flash")

        file_attachment = FileContentWithMimeType(file_path=tmp_path, mime_type=mime)
        extraction_msg = UserMessage(text=EXTRACTION_PROMPT, file_contents=[file_attachment])
        extraction_response = await chat.send_message(extraction_msg)

        # Parse JSON from response
        raw = extraction_response.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        extracted = json_mod.loads(raw)
        ext_data = extracted.get("extracted", extracted)
        summary = extracted.get("summary", "")

        # Step 2: Price analysis — use LOCAL DVF data, not arrondissement average
        asking_price = ext_data.get("asking_price", 0) or 0
        surface = ext_data.get("surface_carrez", 0) or ext_data.get("surface_habitable", 0) or 50
        price_sqm = round(asking_price / max(surface, 1)) if asking_price else 0
        postal = ext_data.get("postal_code", "75001")
        arr_avg = ZONE_AVG_PRICES.get(postal, 8000)

        # Geocode the address to get lat/lon for DVF local search
        address_text = ext_data.get("address") or ""
        if not address_text and ext_data.get("neighborhood"):
            address_text = f"{ext_data['neighborhood']} {postal}"
        elif not address_text:
            address_text = f"{postal}"

        # Only append city context if no city/postal hint detected
        geo_query = address_text
        if not any(kw in address_text.lower() for kw in ["paris", "neuilly", "boulogne", "clichy",
            "levallois", "issy", "montrouge", "vincennes", "montreuil", "saint-"]):
            if _is_paris_intramuros(postal):
                geo_query = address_text + " Paris"
            else:
                geo_query = address_text  # BAN API handles postal codes well

        geo = await geocode_address(geo_query)
        local_median = arr_avg
        search_radius = 0
        local_comparables = []
        local_excluded = []
        local_circle_stats = {}
        local_street_coeff = 1.0
        local_street_coeff_detail = ""
        micro = {"local_premium_pct": 0}
        target_street_name = ""

        if geo:
            target_street_name = _extract_street_from_user_address(geo.get("street", "") or address_text)
            local_comparables, local_excluded, search_radius, local_circle_stats, local_street_coeff, local_street_coeff_detail = await fetch_dvf_progressive(
                geo["latitude"], geo["longitude"],
                target_surface=surface, postal_code=postal,
                target_street=target_street_name, min_comps=8,
            )
            if local_comparables:
                raw_median = weighted_median_price(local_comparables)
                if local_street_coeff != 1.0 and abs(local_street_coeff - 1.0) > 0.05:
                    local_median = round(raw_median * local_street_coeff)
                else:
                    local_median = raw_median
                micro = compute_micro_score(local_comparables, arr_avg, postal_code=postal)
                if geo.get("postal_code"):
                    postal = geo["postal_code"]
                    arr_avg = ARRONDISSEMENT_AVG_PRICES.get(postal, arr_avg)

        analysis_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            extracted_json=json_mod.dumps(ext_data, ensure_ascii=False, indent=2),
            asking_price=f"{asking_price:,.0f}",
            surface=surface,
            price_sqm=f"{price_sqm:,.0f}",
            arr_avg=f"{arr_avg:,.0f}",
            local_median=f"{local_median:,.0f}",
            search_radius=search_radius,
            num_comparables=len(local_comparables),
            num_excluded=len(local_excluded),
            c1_count=local_circle_stats.get("circle_1_count", 0),
            c2_count=local_circle_stats.get("circle_2_count", 0),
            c3_count=local_circle_stats.get("circle_3_count", 0),
            reliability=local_circle_stats.get("reliability", "BASSE"),
            street_coeff=f"{local_street_coeff:.2f}",
            street_coeff_detail=local_street_coeff_detail,
            local_premium=f"{micro.get('local_premium_pct', 0):+.1f}",
        )

        chat2 = LlmChat(
            api_key=api_key,
            session_id=f"analysis-{uuid.uuid4()}",
            system_message="Tu es un expert en valorisation immobilière. Réponds UNIQUEMENT en JSON valide. Sois direct, factuel et sans complaisance."
        ).with_model("gemini", "gemini-2.5-flash")

        analysis_response = await chat2.send_message(UserMessage(text=analysis_prompt))
        raw2 = analysis_response.strip()
        if raw2.startswith("```"):
            raw2 = raw2.split("\n", 1)[1] if "\n" in raw2 else raw2[3:]
            raw2 = raw2.rsplit("```", 1)[0]
        analysis = json_mod.loads(raw2)

        # Build result with DVF local data
        def _clean(c):
            return {k: v for k, v in c.items() if not k.startswith("_")}

        analysis_id = str(uuid.uuid4())
        result_data = {
            "status": "success",
            "analysis_id": analysis_id,
            "extracted": ext_data,
            "summary": summary,
            "analysis": analysis,
            "market_reference": {
                "arrondissement_avg_sqm": arr_avg,
                "local_dvf_median_sqm": round(local_median),
                "search_radius_m": search_radius,
                "num_comparables": len(local_comparables),
                "num_excluded": len(local_excluded),
                "postal_code": postal,
                "zone_label": _zone_display_label(postal),
                "is_paris": _is_paris_intramuros(postal),
                "asking_price_sqm": price_sqm,
                "micro_score": micro,
                "circle_stats": local_circle_stats,
                "street_coefficient": local_street_coeff,
                "street_coefficient_detail": local_street_coeff_detail,
            },
            "comparables": [_clean(c) for c in local_comparables[:15]],
            "excluded_comparables": [_clean(c) for c in local_excluded[:10]],
            "cross_calibration_warning": f"Vérifiez la cohérence avec les annonces en cours sur SeLoger/LeBonCoin autour de cette adresse (prix affichés = +5 à 10% vs prix de transaction réel).",
        }

        # Save to MongoDB for PDF export
        save_doc = {**result_data, "created_at": datetime.now(timezone.utc).isoformat()}
        await db.listing_analyses.insert_one(save_doc)
        save_doc.pop("_id", None)

        return result_data

    except json_mod.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nRaw: {raw[:500] if 'raw' in dir() else 'N/A'}")
        raise HTTPException(status_code=422, detail="L'IA n'a pas retourné un JSON valide. Réessayez.")
    except Exception as e:
        logger.error(f"Listing analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {str(e)}")
    finally:
        os.unlink(tmp_path)

# ─── PDF Report Generation ───

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

# Color palette
PDF_BLACK = HexColor("#18181B")
PDF_GRAY = HexColor("#71717A")
PDF_LIGHT = HexColor("#F4F4F5")
PDF_GREEN = HexColor("#008A00")
PDF_RED = HexColor("#E60000")
PDF_WHITE = white

def build_pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1", fontSize=22, leading=26, textColor=PDF_BLACK, spaceAfter=6))
    styles.add(ParagraphStyle(name="H2", fontSize=14, leading=18, textColor=PDF_BLACK, spaceAfter=4, spaceBefore=14))
    styles.add(ParagraphStyle(name="H3", fontSize=11, leading=14, textColor=PDF_BLACK, spaceAfter=3, spaceBefore=8))
    styles.add(ParagraphStyle(name="Body", fontSize=9, leading=13, textColor=PDF_GRAY))
    styles.add(ParagraphStyle(name="BodyBold", fontSize=9, leading=13, textColor=PDF_BLACK, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Small", fontSize=7.5, leading=10, textColor=PDF_GRAY))
    styles.add(ParagraphStyle(name="SmallBold", fontSize=7.5, leading=10, textColor=PDF_BLACK, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Price", fontSize=28, leading=32, textColor=PDF_BLACK, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Caption", fontSize=8, leading=10, textColor=PDF_GRAY, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Footer", fontSize=7, leading=9, textColor=PDF_GRAY, alignment=TA_CENTER))
    return styles

def fmt_price(n):
    if not n: return "—"
    return f"{int(n):,}".replace(",", " ") + " \u20ac"

def fmt_pct(n):
    if not n: return "0%"
    return f"{'+' if n > 0 else ''}{n:.1f}%"

def _header_footer(canvas, doc, address, date_str):
    canvas.saveState()
    w, h = A4
    # Header line
    canvas.setStrokeColor(HexColor("#E4E4E7"))
    canvas.setLineWidth(0.5)
    canvas.line(20*mm, h - 18*mm, w - 20*mm, h - 18*mm)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(PDF_BLACK)
    canvas.drawString(20*mm, h - 15*mm, "VALORISATEUR")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(PDF_GRAY)
    canvas.drawRightString(w - 20*mm, h - 15*mm, f"Rapport d'estimation — {date_str}")
    # Footer
    canvas.line(20*mm, 15*mm, w - 20*mm, 15*mm)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawString(20*mm, 10*mm, f"{address}")
    canvas.drawRightString(w - 20*mm, 10*mm, f"Page {doc.page}")
    canvas.restoreState()


@api_router.get("/report/pdf/{valuation_id}")
async def generate_pdf_report(valuation_id: str):
    doc_data = await db.valuations.find_one({"id": valuation_id}, {"_id": 0})
    if not doc_data:
        raise HTTPException(status_code=404, detail="Estimation introuvable")

    req = doc_data.get("request", {})
    loc = req.get("location", {})
    chars = req.get("characteristics", {})
    cond = req.get("condition", {})
    bldg = req.get("building", {})
    legal = req.get("legal", {})
    mkt = doc_data.get("market_data", {})
    pos = mkt.get("market_position", {})
    adjustments = doc_data.get("adjustments", [])
    comparables = doc_data.get("comparables", [])
    risks = doc_data.get("risks", [])

    address = loc.get("address", "Adresse inconnue")
    date_str = doc_data.get("created_at", "")[:10]

    styles = build_pdf_styles()
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=24*mm, bottomMargin=22*mm,
    )

    story = []

    # ──── PAGE 1: Cover ────
    story.append(Spacer(1, 30*mm))
    story.append(Paragraph("RAPPORT D'ESTIMATION", styles["H1"]))
    story.append(Paragraph("IMMOBILIÈRE", styles["H1"]))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=PDF_BLACK))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(address, styles["H2"]))
    story.append(Paragraph(f"{loc.get('postal_code', '')} {loc.get('city', '')}", styles["Body"]))
    story.append(Spacer(1, 10*mm))

    # Price summary table
    cover_data = [
        ["ESTIMATION", "FOURCHETTE", "PRIX/M²", "CONFIANCE"],
        [
            fmt_price(doc_data.get("price_median")),
            f"{fmt_price(doc_data.get('price_low'))} — {fmt_price(doc_data.get('price_high'))}",
            fmt_price(doc_data.get("price_per_sqm_median")),
            f"{doc_data.get('confidence_score', 0)}/100",
        ],
    ]
    cover_table = Table(cover_data, colWidths=[42*mm, 52*mm, 38*mm, 30*mm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PDF_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), PDF_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 1), (-1, 1), 10),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E4E4E7")),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 8*mm))

    # Property characteristics summary
    chars_items = [
        ("Surface Carrez", f"{chars.get('surface_carrez', '?')} m²"),
        ("Pièces / Chambres", f"{chars.get('rooms', '?')} / {chars.get('bedrooms', '?')}"),
        ("Étage", f"{loc.get('floor', '?')} {'(avec ascenseur)' if bldg.get('elevator') else '(sans ascenseur)'}"),
        ("Exposition", chars.get("exposure", "?").capitalize()),
        ("Vue", chars.get("view", "?").replace("_", " ").capitalize()),
        ("DPE / GES", f"{cond.get('dpe', '?')} / {cond.get('ges', '?')}"),
        ("État général", cond.get("general_state", "?").replace("_", " ").capitalize()),
        ("Immeuble", bldg.get("building_type", "?").replace("_", " ").capitalize()),
        ("Parking", chars.get("parking", "aucun").replace("_", " ").capitalize()),
    ]
    ext_type = chars.get('exterior_type', 'aucun')
    ext_surf = chars.get('exterior_surface', 0)
    ext_label = f"{ext_type} ({ext_surf} m²)" if ext_surf else ext_type
    chars_items.append(("Extérieur", ext_label))
    char_data = [["CARACTÉRISTIQUE", "VALEUR"]]
    for label, val in chars_items:
        char_data.append([label, val])
    char_table = Table(char_data, colWidths=[80*mm, 82*mm])
    char_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PDF_LIGHT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 1), (0, -1), PDF_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#E4E4E7")),
    ]))
    story.append(Paragraph("Caractéristiques du bien", styles["H2"]))
    story.append(char_table)

    # Market position
    if pos:
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("Position sur le marché", styles["H2"]))
        mp_text = f"Votre bien est estimé à {fmt_price(pos.get('estimated_sqm'))}/m², "
        mp_text += f"soit {fmt_pct(pos.get('diff_pct'))} par rapport à la moyenne de la zone ({fmt_price(pos.get('arr_avg'))}/m²). "
        mp_text += f"Position : <b>{pos.get('label', '=')}</b> — {pos.get('description', '')}"
        story.append(Paragraph(mp_text, styles["Body"]))

    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"Source des données : {mkt.get('base_source', 'DVF Cerema')} — Période : {mkt.get('comparables_period', '2020-2025')} — {mkt.get('total_comparables', 0)} transactions analysées", styles["Small"]))

    story.append(PageBreak())

    # ──── PAGE 2: Adjustments detail ────
    story.append(Paragraph("Décomposition du prix", styles["H1"]))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"Prix de base médian : {fmt_price(mkt.get('base_price_sqm'))}/m² (source : {mkt.get('base_source', 'DVF')})", styles["BodyBold"]))
    story.append(Spacer(1, 4*mm))

    if adjustments:
        adj_data = [["CRITÈRE", "IMPACT", "DÉTAIL"]]
        for adj in adjustments:
            atype = adj.get("type", "pct")
            val = adj.get("value", 0)
            if atype == "pct":
                impact_str = fmt_pct(val)
            elif atype == "flat":
                impact_str = fmt_price(val)
            elif atype == "flat_per_sqm":
                impact_str = f"{fmt_price(val)}/m²"
            else:
                impact_str = str(val)
            adj_data.append([adj.get("name", ""), impact_str, adj.get("detail", "")])

        # Summary row
        adj_data.append(["TOTAL AJUSTEMENTS", fmt_pct(mkt.get("adjustment_pct", 0)) + (f" + {fmt_price(mkt.get('adjustment_flat', 0))}" if mkt.get("adjustment_flat") else ""), ""])

        adj_table = Table(adj_data, colWidths=[45*mm, 35*mm, 82*mm])
        adj_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PDF_BLACK),
            ("TEXTCOLOR", (0, 0), (-1, 0), PDF_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#E4E4E7")),
            # Last row = total
            ("BACKGROUND", (0, -1), (-1, -1), PDF_LIGHT),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        story.append(adj_table)
    else:
        story.append(Paragraph("Aucun ajustement appliqué.", styles["Body"]))

    story.append(Spacer(1, 6*mm))

    # Hypotheses detail
    story.append(Paragraph("Hypothèses détaillées", styles["H2"]))
    story.append(Spacer(1, 2*mm))
    for adj in adjustments:
        hyp = adj.get("hypothesis", "")
        if hyp:
            story.append(Paragraph(f"<b>{adj.get('name', '')}</b> ({fmt_pct(adj.get('value', 0)) if adj.get('type') == 'pct' else fmt_price(adj.get('value', 0))})", styles["H3"]))
            story.append(Paragraph(hyp, styles["Body"]))
            story.append(Spacer(1, 2*mm))

    story.append(PageBreak())

    # ──── PAGE 3: Comparables ────
    story.append(Paragraph("Transactions comparables (DVF)", styles["H1"]))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"{len(comparables)} transactions réelles trouvées dans un rayon de 500m", styles["Body"]))
    story.append(Spacer(1, 4*mm))

    if comparables:
        comp_display = comparables[:20]
        comp_data = [["DATE", "ADRESSE", "SURFACE", "PRIX", "PRIX/M²"]]
        for c in comp_display:
            comp_data.append([
                str(c.get("date", ""))[:10],
                str(c.get("address", ""))[:35],
                f"{c.get('surface', 0):.0f} m²",
                fmt_price(c.get("price")),
                fmt_price(c.get("price_per_sqm")),
            ])
        comp_table = Table(comp_data, colWidths=[22*mm, 60*mm, 22*mm, 30*mm, 28*mm])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PDF_BLACK),
            ("TEXTCOLOR", (0, 0), (-1, 0), PDF_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 6.5),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#E4E4E7")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PDF_WHITE, PDF_LIGHT]),
        ]))
        story.append(comp_table)
    else:
        story.append(Paragraph("Aucune transaction comparable trouvée.", styles["Body"]))

    story.append(Spacer(1, 6*mm))

    # ──── Risks ────
    story.append(Paragraph("Analyse des risques", styles["H2"]))
    story.append(Spacer(1, 3*mm))

    if risks:
        for r in risks:
            level = r.get("level", "info")
            color_hex = "#E60000" if level == "critical" else "#F59E0B" if level == "warning" else "#71717A"
            story.append(Paragraph(f'<font color="{color_hex}">●</font> <b>{r.get("type", "")}</b> — {r.get("detail", "")}', styles["Body"]))
            story.append(Spacer(1, 1.5*mm))
    else:
        story.append(Paragraph("Aucun risque majeur identifié.", styles["Body"]))

    story.append(Spacer(1, 10*mm))

    # Legal information
    story.append(Paragraph("Informations légales", styles["H2"]))
    legal_items = [
        ("Type de propriété", legal.get("ownership_type", "pleine_propriete").replace("_", " ").capitalize()),
        ("Taxe foncière", fmt_price(legal.get("property_tax")) if legal.get("property_tax") else "Non renseignée"),
        ("Charges annuelles", fmt_price(bldg.get("annual_charges")) if bldg.get("annual_charges") else "Non renseignées"),
        ("Syndic", bldg.get("syndic_type", "?").capitalize()),
        ("Lots copropriété", str(bldg.get("total_lots", "?"))),
    ]
    for label, val in legal_items:
        story.append(Paragraph(f"<b>{label}</b> : {val}", styles["Body"]))

    story.append(PageBreak())

    # ──── PAGE 4: Disclaimer & methodology ────
    story.append(Paragraph("Méthodologie", styles["H1"]))
    story.append(Spacer(1, 4*mm))
    methodology_text = """Cette estimation repose sur une méthodologie transparente en 4 étapes :

<b>1. Collecte des données</b> — Les transactions immobilières réelles sont récupérées via l'API DVF du Cerema (Demandes de Valeurs Foncières), base officielle alimentée par la DGFiP. Seules les ventes depuis 2020 dans un rayon de 500m sont retenues.

<b>2. Calcul du prix de base</b> — La médiane tronquée (trimmed median) des prix au m² est calculée en excluant les 10% de valeurs extrêmes (hautes et basses) pour éliminer les transactions atypiques.

<b>3. Ajustements</b> — Des coefficients de pondération sont appliqués pour chaque critère (étage, exposition, DPE, vue, état, etc.). Ces coefficients sont basés sur les études notariales et les recommandations d'experts. Un plafonnement des ajustements cumulés est appliqué pour éviter toute surestimation.

<b>4. Fourchette de prix</b> — Le prix final est présenté avec une fourchette de ±8% (haute confiance) à ±12% (confiance modérée), selon le nombre de comparables disponibles."""

    story.append(Paragraph(methodology_text, styles["Body"]))
    story.append(Spacer(1, 8*mm))

    story.append(Paragraph("Avertissement", styles["H2"]))
    disclaimer = """Ce rapport est fourni à titre indicatif et ne constitue pas une expertise immobilière au sens de la Charte de l'Expertise en Évaluation Immobilière. Les données utilisées proviennent de sources publiques (DVF, Géorisques, ADEME) et peuvent comporter des inexactitudes. Cette estimation ne saurait engager la responsabilité de ses auteurs. Pour toute transaction immobilière, nous recommandons de consulter un expert agréé, un notaire ou un agent immobilier qualifié."""
    story.append(Paragraph(disclaimer, styles["Body"]))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(f"Rapport généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')} UTC", styles["Small"]))

    # Build PDF
    def on_page(canvas, doc):
        _header_footer(canvas, doc, address, date_str)

    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    buffer.seek(0)

    safe_address = address.replace(" ", "_").replace("/", "-")[:50]
    filename = f"Estimation_{safe_address}_{date_str}.pdf"

    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ─── Listing Analysis PDF Report ───

@api_router.get("/listing/report/pdf/{analysis_id}")
async def generate_listing_pdf(analysis_id: str):
    doc_data = await db.listing_analyses.find_one({"analysis_id": analysis_id}, {"_id": 0})
    if not doc_data:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    ext_data = doc_data.get("extracted", {})
    analysis = doc_data.get("analysis", {})
    mkt = doc_data.get("market_reference", {})
    summary = doc_data.get("summary", "")
    comps = doc_data.get("comparables", [])
    date_str = doc_data.get("created_at", "")[:10]

    address = ext_data.get("address") or "Adresse inconnue"
    asking = ext_data.get("asking_price", 0)
    surface = ext_data.get("surface_carrez", 0) or ext_data.get("surface_habitable", 0) or 0

    styles = build_pdf_styles()
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=24*mm, bottomMargin=22*mm)
    story = []

    # Cover
    story.append(Spacer(1, 25*mm))
    story.append(Paragraph("ANALYSE DE FICHE D'AGENCE", styles["H1"]))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=PDF_BLACK))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(address, styles["H2"]))
    story.append(Paragraph(f"{ext_data.get('postal_code', '')} {ext_data.get('arrondissement', '')} — {ext_data.get('neighborhood', '')}", styles["Body"]))
    story.append(Spacer(1, 6*mm))

    if summary:
        story.append(Paragraph(summary, styles["Body"]))
        story.append(Spacer(1, 6*mm))

    # Price opinion box
    opinion_labels = {"sous-évalué": "SOUS-ÉVALUÉ", "prix_juste": "PRIX JUSTE", "surévalué": "SURÉVALUÉ", "très_surévalué": "TRÈS SURÉVALUÉ"}
    opinion_label = opinion_labels.get(analysis.get("price_opinion", ""), analysis.get("price_opinion", ""))

    price_data = [
        ["PRIX DEMANDÉ", "ESTIMATION JUSTE", "AVIS", "MÉDIANE LOCALE DVF"],
        [
            fmt_price(asking),
            f"{fmt_price(analysis.get('estimated_fair_price_low'))} — {fmt_price(analysis.get('estimated_fair_price_high'))}",
            opinion_label,
            f"{fmt_price(mkt.get('local_dvf_median_sqm'))}/m²",
        ],
    ]
    price_table = Table(price_data, colWidths=[40*mm, 50*mm, 38*mm, 34*mm])
    price_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PDF_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), PDF_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 1), (-1, 1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E4E4E7")),
    ]))
    story.append(price_table)
    story.append(Spacer(1, 4*mm))

    # Market context
    story.append(Paragraph(f"Rayon de recherche DVF : {mkt.get('search_radius_m', '?')}m — {mkt.get('num_comparables', 0)} transactions — Moy. zone : {fmt_price(mkt.get('arrondissement_avg_sqm'))}/m²", styles["Small"]))
    story.append(Spacer(1, 6*mm))

    # Characteristics
    chars_items = [
        ("Surface", f"{surface} m²"), ("Pièces", str(ext_data.get("rooms", "?"))),
        ("Chambres", str(ext_data.get("bedrooms", "?"))), ("Étage", f"{ext_data.get('floor', '?')}/{ext_data.get('total_floors', '?')}"),
        ("DPE", str(ext_data.get("dpe", "?"))), ("État", str(ext_data.get("general_state", "?")).replace("_", " ")),
        ("Ascenseur", "Oui" if ext_data.get("elevator") else "Non"),
        ("Parking", str(ext_data.get("parking", "aucun"))),
        ("Extérieur", str(ext_data.get("exterior_type", "aucun"))),
        ("Immeuble", str(ext_data.get("building_type", "?")).replace("_", " ")),
    ]
    char_data = [["CARACTÉRISTIQUE", "VALEUR"]]
    for label, val in chars_items:
        char_data.append([label, val])
    char_table = Table(char_data, colWidths=[80*mm, 82*mm])
    char_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PDF_LIGHT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (0, -1), PDF_GRAY),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#E4E4E7")),
    ]))
    story.append(Paragraph("Caractéristiques extraites", styles["H2"]))
    story.append(char_table)

    story.append(PageBreak())

    # Verdict
    if analysis.get("verdict"):
        story.append(Paragraph("Verdict", styles["H1"]))
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(analysis["verdict"], styles["Body"]))
        story.append(Spacer(1, 6*mm))

    # Arguments
    if analysis.get("arguments_for"):
        story.append(Paragraph("Arguments pour le prix", styles["H2"]))
        for arg in analysis["arguments_for"]:
            story.append(Paragraph(f'<font color="#008A00">+</font> {arg}', styles["Body"]))
        story.append(Spacer(1, 4*mm))

    if analysis.get("arguments_against"):
        story.append(Paragraph("Arguments contre le prix", styles["H2"]))
        for arg in analysis["arguments_against"]:
            story.append(Paragraph(f'<font color="#E60000">-</font> {arg}', styles["Body"]))
        story.append(Spacer(1, 4*mm))

    if analysis.get("negotiation_tips"):
        story.append(Paragraph("Conseils de négociation", styles["H2"]))
        for tip in analysis["negotiation_tips"]:
            story.append(Paragraph(f"• {tip}", styles["Body"]))
        story.append(Spacer(1, 4*mm))

    # Comparables
    if comps:
        story.append(Paragraph(f"Transactions DVF proches ({len(comps)})", styles["H2"]))
        comp_data = [["DATE", "ADRESSE", "DIST.", "SURFACE", "PRIX/M²"]]
        for c in comps[:15]:
            comp_data.append([
                str(c.get("date", ""))[:10],
                str(c.get("address", ""))[:35],
                f"{c.get('distance_m', '?')}m",
                f"{c.get('surface', 0):.0f} m²",
                fmt_price(c.get("price_per_sqm")),
            ])
        comp_table = Table(comp_data, colWidths=[22*mm, 55*mm, 18*mm, 22*mm, 28*mm])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PDF_BLACK),
            ("TEXTCOLOR", (0, 0), (-1, 0), PDF_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 6.5),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#E4E4E7")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PDF_WHITE, PDF_LIGHT]),
        ]))
        story.append(comp_table)

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("Avertissement", styles["H2"]))
    story.append(Paragraph("Ce rapport est généré automatiquement à partir d'une fiche d'agence analysée par IA. Les données extraites peuvent contenir des erreurs. Les prix de référence proviennent exclusivement des transactions DVF réelles. Ce document ne constitue pas une expertise immobilière.", styles["Body"]))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"Rapport généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')} UTC", styles["Small"]))

    def on_page(canvas, doc):
        _header_footer(canvas, doc, address, date_str)

    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    buffer.seek(0)

    safe_addr = address.replace(" ", "_").replace("/", "-")[:50]
    filename = f"Analyse_{safe_addr}_{date_str}.pdf"

    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


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
