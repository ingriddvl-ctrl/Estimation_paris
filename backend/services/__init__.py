"""
Service de scraping du marché actif (annonces en cours).
Sources: BienIci (API JSON), Castorus (URL lookup), defaults zonés
Produit la "Couche 2" du modèle de valorisation.
"""

import httpx
import re
import json
import math
import logging
import urllib.parse
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Spread par défaut par zone (calibré sur données DVF vs annonces 2023-2024) ──
# spread = (prix demandé - prix transaction) / prix demandé
_DEFAULT_SPREADS = {
    # Paris center — marché très tendu, peu de marge
    "75001": 3.5, "75002": 4.0, "75003": 3.5, "75004": 3.0,
    "75005": 4.0, "75006": 3.0, "75007": 3.0, "75008": 4.5,
    # Paris intermediate
    "75009": 5.5, "75010": 6.0, "75011": 5.5, "75012": 6.0,
    "75014": 5.5, "75015": 5.5, "75016": 5.0, "75017": 5.5,
    # Paris peripheral
    "75013": 6.5, "75018": 7.0, "75019": 8.0, "75020": 7.5,
    # Hauts-de-Seine premium
    "92200": 4.5, "92300": 5.0, "92100": 5.5, "92130": 5.5,
    "92210": 4.5, "92150": 5.5,
    # Hauts-de-Seine moderate
    "92120": 6.5, "92170": 6.5, "92240": 7.0, "92800": 6.5,
    "92400": 7.0, "92600": 6.5, "92110": 7.0, "92140": 6.5,
    # Seine-Saint-Denis
    "93100": 8.0, "93200": 10.0, "93400": 8.5, "93300": 11.0,
    "93500": 8.5, "93170": 8.0, "93260": 7.5, "93310": 7.0,
    # Val-de-Marne premium
    "94300": 5.0, "94160": 4.5, "94220": 5.5,
    # Val-de-Marne moderate
    "94200": 8.0, "94270": 7.0, "94120": 7.0, "94130": 6.5,
    "94100": 6.5, "94000": 9.0, "94400": 9.5, "94700": 7.0,
}

# Default tension scores by zone type
_DEFAULT_TENSIONS = {
    "central": 75,      # Paris center — très tendu
    "intermediate": 60,  # Paris intermédiaire / banlieue premium
    "peripheral": 45,    # Paris périphérique / banlieue
}


def _get_default_spread(postal_code: str) -> float:
    if postal_code in _DEFAULT_SPREADS:
        return _DEFAULT_SPREADS[postal_code]
    dept = postal_code[:2]
    if dept == "75":
        return 6.0
    if dept == "92":
        return 6.5
    if dept == "93":
        return 9.0
    if dept == "94":
        return 7.0
    return 7.0


def _get_default_tension(zone: str) -> int:
    return _DEFAULT_TENSIONS.get(zone, 50)


# ── BienIci API (internal JSON endpoint) ──

_BIENICI_ZONE_IDS = {}  # Will be populated dynamically via suggest API

def _postal_to_insee_paris(postal_code: str) -> str:
    """Convert Paris postal code (75001-75020) to INSEE code (75101-75120).
    BienIci uses INSEE codes, not postal codes for Paris arrondissements."""
    if postal_code.startswith("75") and len(postal_code) == 5:
        arr = int(postal_code[3:])
        if 1 <= arr <= 20:
            return f"751{arr:02d}"
    return postal_code


async def _resolve_bienici_zone(postal_code: str) -> Optional[Dict]:
    """Resolve a postal code to BienIci zone IDs via their suggest API."""
    if postal_code in _BIENICI_ZONE_IDS:
        return _BIENICI_ZONE_IDS[postal_code]

    is_paris = postal_code.startswith("75") and len(postal_code) == 5 and postal_code[2:].isdigit()
    insee_code = _postal_to_insee_paris(postal_code) if is_paris else postal_code

    if is_paris:
        arr_num = int(postal_code[-2:])
        # Use specific query formats that BienIci recognizes
        query = f"paris {arr_num}e arrondissement"
    else:
        query = postal_code

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"https://res.bienici.com/suggest.json?q={urllib.parse.quote(query)}",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code == 200:
                suggestions = resp.json()
                logger.info(f"BienIci suggest for '{query}': {len(suggestions)} results")
                for s in suggestions:
                    s_postcodes = s.get("postalCodes", [])
                    s_insee_codes = s.get("insee_codes", [])
                    s_insee_single = s.get("insee_code", "")

                    # Match by postal code, INSEE code, or derived INSEE code
                    match = (
                        postal_code in s_postcodes
                        or insee_code in s_postcodes
                        or insee_code in s_insee_codes
                        or s_insee_single == insee_code
                    )

                    if match:
                        zone_data = {
                            "insee_code": s_insee_single or (s_insee_codes[0] if s_insee_codes else insee_code),
                            "zone_ids": s.get("zoneIds", []),
                            "name": s.get("name", ""),
                        }
                        _BIENICI_ZONE_IDS[postal_code] = zone_data
                        logger.info(f"BienIci zone resolved: {postal_code} -> {zone_data['name']} (INSEE: {zone_data['insee_code']}, zones: {zone_data['zone_ids']})")
                        return zone_data

                # Fallback: take first suggestion if it's in the right department
                if suggestions:
                    s = suggestions[0]
                    dept = postal_code[:2]
                    s_postcodes = s.get("postalCodes", [])
                    if any(pc.startswith(dept) for pc in s_postcodes) or not s_postcodes:
                        zone_data = {
                            "insee_code": s.get("insee_code", s.get("insee_codes", [insee_code])[0] if s.get("insee_codes") else insee_code),
                            "zone_ids": s.get("zoneIds", []),
                            "name": s.get("name", ""),
                        }
                        _BIENICI_ZONE_IDS[postal_code] = zone_data
                        logger.info(f"BienIci zone fallback: {postal_code} -> {zone_data['name']}")
                        return zone_data

                logger.warning(f"BienIci: no match found for {postal_code} (INSEE: {insee_code}) in {len(suggestions)} suggestions")
    except Exception as e:
        logger.warning(f"BienIci zone resolve error for {postal_code}: {e}")
    return None


async def scrape_bienici_listings(postal_code: str, surface_min: int = 20, surface_max: int = 200,
                                   rooms_min: int = 1, rooms_max: int = 6) -> List[Dict]:
    """Fetch active listings from BienIci's internal JSON API."""
    zone = await _resolve_bienici_zone(postal_code)
    if not zone:
        logger.warning(f"Could not resolve BienIci zone for {postal_code}")
        return []

    insee = zone["insee_code"]
    zone_ids = zone["zone_ids"]

    filters = {
        "size": 24,
        "from": 0,
        "filterType": "buy",
        "propertyType": ["flat"],
        "minArea": surface_min,
        "maxArea": surface_max,
        "minRooms": rooms_min,
        "maxRooms": rooms_max,
        "page": 1,
        "resultsPerPage": 24,
        "sortBy": "relevance",
        "sortOrder": "desc",
        "onTheMarket": [True],
    }
    if zone_ids:
        filters["zoneIdsByInseeCode"] = {insee: zone_ids}

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.bienici.com/recherche/achat/paris",
            "Origin": "https://www.bienici.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }

        # Try the search API first
        search_url = "https://www.bienici.com/realEstateAds.json"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                search_url,
                params={"filters": json.dumps(filters)},
                headers=headers,
            )
            logger.info(f"BienIci response status: {resp.status_code} for {postal_code}")
            if resp.status_code != 200:
                # Try alternative API endpoint
                alt_url = f"https://res.bienici.com/realEstateAds.json"
                resp = await client.get(
                    alt_url,
                    params={"filters": json.dumps(filters)},
                    headers={**headers, "Origin": "https://res.bienici.com", "Referer": "https://res.bienici.com/"},
                )
                if resp.status_code != 200:
                    logger.warning(f"BienIci both endpoints failed: {resp.status_code}")
                    return []

            data = resp.json()
            ads = data.get("realEstateAds", [])

            listings = []
            target_postal = postal_code
            target_insee = _postal_to_insee_paris(postal_code) if postal_code.startswith("75") else postal_code
            for ad in ads:
                ad_postal = ad.get("postalCode", "")
                ad_city_code = ad.get("cityCode", "") or ad.get("insee_code", "")
                # For Paris: match on exact postal code or exact INSEE code
                # For suburbs: match on exact postal code
                if postal_code.startswith("75"):
                    is_match = (
                        ad_postal == postal_code
                        or ad_postal == target_insee
                        or ad_city_code == target_insee
                    )
                else:
                    is_match = ad_postal == postal_code

                if not is_match:
                    continue

                price = ad.get("price", 0)
                area = ad.get("surfaceArea", 0)
                if isinstance(price, list):
                    price = price[0] if price else 0
                if isinstance(area, list):
                    area = area[0] if area else 0
                if not price or not area:
                    continue

                rooms = ad.get("roomsQuantity", 0)
                if isinstance(rooms, list):
                    rooms = rooms[0] if rooms else 0

                listings.append({
                    "price": int(price),
                    "surface": round(float(area), 1),
                    "price_per_sqm": round(price / area) if area > 0 else 0,
                    "rooms": int(rooms) if rooms else 0,
                    "bedrooms": ad.get("bedroomsQuantity", 0),
                    "floor": ad.get("floor"),
                    "city": ad.get("city", ""),
                    "postal_code": ad_postal,
                    "neighborhood": ad.get("district", {}).get("name", "") if isinstance(ad.get("district"), dict) else "",
                    "source": "bienici",
                })

            logger.info(f"BienIci scrape for {postal_code}: {len(listings)} listings (from {len(ads)} total)")
            return listings
    except Exception as e:
        logger.error(f"BienIci scrape error: {e}")
        return []


# ── SeLoger Scraper (backup, works when JS renders) ──

async def scrape_seloger_listings(postal_code: str, surface_min: int = 20, surface_max: int = 200,
                                   rooms_min: int = 1, rooms_max: int = 6,
                                   price_max: int = 3000000) -> List[Dict]:
    """Attempt SeLoger scraping (may fail due to JS requirement)."""
    return []  # SeLoger requires JS rendering, disabled for now


async def scrape_seloger_listing_url(url: str) -> Optional[Dict]:
    """Scrape a single SeLoger listing page for detailed info."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html", "Accept-Language": "fr-FR,fr;q=0.9",
            })
            if resp.status_code != 200:
                return None

            text = resp.text
            data = {"source_url": url}

            for pattern, key in [
                (r'"price"\s*:\s*(\d+)', "price"),
                (r'"livingArea"\s*:\s*([\d.]+)', "surface"),
                (r'"numberOfRooms"\s*:\s*(\d+)', "rooms"),
                (r'"numberOfBedrooms"\s*:\s*(\d+)', "bedrooms"),
            ]:
                m = re.search(pattern, text)
                if m:
                    data[key] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))

            city_m = re.search(r'"addressLocality"\s*:\s*"([^"]+)"', text)
            if city_m:
                data["city"] = city_m.group(1)
            postal_m = re.search(r'"postalCode"\s*:\s*"(\d+)"', text)
            if postal_m:
                data["postal_code"] = postal_m.group(1)

            if data.get("price") and data.get("surface"):
                data["price_per_sqm"] = round(data["price"] / data["surface"])
                return data
            return None
    except Exception as e:
        logger.error(f"SeLoger single listing scrape error: {e}")
        return None


# ── Castorus URL Lookup ──

async def lookup_castorus_url(listing_url: str) -> Optional[Dict]:
    """
    Try to look up a listing URL on Castorus for price history.
    Returns dict with days_on_market, price_drops, etc.
    Castorus is community-powered — data may not exist for all listings.
    """
    if not listing_url:
        return None
    try:
        # Try direct search on Castorus
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.castorus.com/",
        }

        # Method 1: Search by URL on Castorus
        encoded = urllib.parse.quote(listing_url, safe="")
        castorus_urls = [
            f"https://www.castorus.com/s/{encoded}",
            f"https://www.castorus.com/s/?q={encoded}",
        ]

        for castorus_url in castorus_urls:
            async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
                resp = await client.get(castorus_url, headers=headers)
                if resp.status_code != 200:
                    continue

                text = resp.text
                data = {"source": "castorus", "url": listing_url}

                # Parse price history
                prices = re.findall(r'(\d[\d\s]*)\s*€', text.replace('\u202f', ' ').replace('\xa0', ' '))
                dates = re.findall(r'(\d{2}/\d{2}/\d{4})', text)

                if prices and dates:
                    history = []
                    for p, d in zip(prices[:10], dates[:10]):
                        p_clean = p.replace(" ", "")
                        if p_clean.isdigit() and int(p_clean) > 10000:
                            history.append({"price": int(p_clean), "date": d})

                    if history:
                        data["price_history"] = history
                        data["initial_price"] = history[0]["price"]
                        data["current_price"] = history[-1]["price"]
                        data["total_drop_pct"] = round(
                            (history[0]["price"] - history[-1]["price"]) / history[0]["price"] * 100, 1
                        ) if history[0]["price"] > 0 else 0
                        data["num_price_drops"] = sum(
                            1 for i in range(1, len(history)) if history[i]["price"] < history[i-1]["price"]
                        )

                # Parse days on market
                dom_match = re.search(r'(\d+)\s*jour', text)
                if dom_match:
                    data["days_on_market"] = int(dom_match.group(1))

                # Parse creation date
                creation_match = re.search(r'(?:mise en ligne|créée?|publiée?)\s*(?:le\s*)?(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
                if creation_match:
                    data["first_seen"] = creation_match.group(1)

                if len(data) > 2:
                    logger.info(f"Castorus found data for {listing_url}: DOM={data.get('days_on_market')}, drops={data.get('num_price_drops')}")
                    return data

        logger.info(f"Castorus: no data found for {listing_url}")
        return None
    except Exception as e:
        logger.error(f"Castorus lookup error: {e}")
        return None



# ── Castorus Zone Stats (aggregate market data for a commune) ──

async def scrape_castorus_zone_stats(postal_code: str) -> Optional[Dict]:
    """
    Scrape Castorus commune page for aggregate market stats:
    - Average days on market
    - % of listings with price drops
    - Average drop amplitude
    These feed into the tension index (Couche 2).
    """
    try:
        # Castorus uses commune search
        is_paris = postal_code.startswith("75") and len(postal_code) == 5
        if is_paris:
            arr_num = int(postal_code[-2:])
            query = f"paris {arr_num}e"
        else:
            query = postal_code

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Referer": "https://www.castorus.com/",
        }

        search_url = f"https://www.castorus.com/s/?q={urllib.parse.quote(query)}&type=buy"
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            resp = await client.get(search_url, headers=headers)
            if resp.status_code != 200:
                logger.info(f"Castorus zone stats: {resp.status_code} for {postal_code}")
                return None

            text = resp.text
            stats = {"source": "castorus_zone", "postal_code": postal_code}

            # Try to extract aggregate stats from the page
            # DOM average
            dom_matches = re.findall(r'(\d+)\s*jour', text)
            if dom_matches:
                dom_values = [int(d) for d in dom_matches if 1 < int(d) < 1000]
                if dom_values:
                    stats["avg_dom"] = round(sum(dom_values) / len(dom_values))
                    stats["dom_count"] = len(dom_values)

            # Price drops
            drop_matches = re.findall(r'(-\s*\d+[\d\s]*)\s*€', text.replace('\u202f', ' ').replace('\xa0', ' '))
            price_matches = re.findall(r'(\d[\d\s]*)\s*€', text.replace('\u202f', ' ').replace('\xa0', ' '))

            if price_matches:
                total_listings = len([p for p in price_matches if p.replace(" ", "").isdigit() and int(p.replace(" ", "")) > 50000])
                listings_with_drops = len(drop_matches)
                if total_listings > 0:
                    stats["pct_with_drops"] = round(listings_with_drops / total_listings * 100, 1)
                    stats["total_listings_seen"] = total_listings

            if len(stats) > 2:
                logger.info(f"Castorus zone stats for {postal_code}: {stats}")
                return stats

        return None
    except Exception as e:
        logger.warning(f"Castorus zone stats error for {postal_code}: {e}")
        return None


# ── Market Analysis Functions ──

def calculate_spread(dvf_comparables: List[Dict], active_listings: List[Dict],
                     target_surface: float, postal_code: str = "") -> Dict:
    """
    Calculate the spread between asking prices (annonces) and transaction prices (DVF).
    Uses live data when available, falls back to calibrated zone defaults.
    """
    # DVF median price/sqm
    dvf_prices = sorted([c["price_per_sqm"] for c in dvf_comparables if c.get("price_per_sqm")])
    dvf_median = dvf_prices[len(dvf_prices) // 2] if dvf_prices else 0

    # Filter listings by similar surface
    similar_listings = [
        li for li in active_listings
        if li.get("price_per_sqm") and li.get("surface")
        and abs(li["surface"] - target_surface) / max(target_surface, 1) <= 0.5
    ]
    if not similar_listings:
        similar_listings = [li for li in active_listings if li.get("price_per_sqm")]

    listing_prices = sorted([li["price_per_sqm"] for li in similar_listings]) if similar_listings else []
    listing_median = listing_prices[len(listing_prices) // 2] if listing_prices else 0

    # Calculate spread from real data if both sources available
    if listing_median > 0 and dvf_median > 0 and len(similar_listings) >= 3 and len(dvf_prices) >= 3:
        spread_pct = round((listing_median - dvf_median) / listing_median * 100, 1)
        spread_pct = max(0, min(20, spread_pct))
        source = "calcul_local"
        confidence = "haute" if len(similar_listings) >= 10 and len(dvf_prices) >= 10 else "moyenne"
    else:
        # Use calibrated default spread for the zone
        spread_pct = _get_default_spread(postal_code)
        source = "estimation_zone"
        confidence = "moyenne" if listing_median > 0 or dvf_median > 0 else "basse"

    return {
        "spread_pct": spread_pct,
        "spread_source": source,
        "confidence": confidence,
        "dvf_median_sqm": dvf_median,
        "listing_median_sqm": listing_median,
        "num_dvf": len(dvf_prices),
        "num_listings": len(similar_listings),
    }


def calculate_tension_index(active_listings: List[Dict], dvf_comparables: List[Dict],
                            castorus_data: Optional[Dict] = None,
                            zone: str = "intermediate") -> Dict:
    """
    Calculate market tension index (0-100).
    Uses live data when available, calibrated defaults otherwise.
    """
    score = _get_default_tension(zone)
    details = []

    num_listings = len(active_listings)
    num_transactions = len(dvf_comparables)

    # Factor 1: Stock vs Flow ratio (if we have listings data)
    stock_flow = round(num_listings / max(num_transactions, 1), 2) if num_transactions > 0 else None

    if stock_flow is not None and num_listings > 0:
        if stock_flow < 1:
            score += 15
            details.append(f"Ratio stock/flux bas ({stock_flow}) — forte demande")
        elif stock_flow < 2.5:
            score += 5
            details.append(f"Ratio stock/flux modéré ({stock_flow})")
        elif stock_flow > 5:
            score -= 15
            details.append(f"Ratio stock/flux élevé ({stock_flow}) — marché détendu")

    # Factor 2: Price homogeneity of listings
    if active_listings and len(active_listings) >= 5:
        lp = [li["price_per_sqm"] for li in active_listings if li.get("price_per_sqm")]
        if len(lp) >= 3:
            mean_p = sum(lp) / len(lp)
            std_p = (sum((p - mean_p)**2 for p in lp) / len(lp)) ** 0.5
            cv = std_p / mean_p if mean_p > 0 else 0.5
            if cv < 0.1:
                score += 10
                details.append("Très forte homogénéité des prix — marché tendu")
            elif cv > 0.25:
                score -= 5
                details.append("Forte dispersion des prix — marché hétérogène")

    # Factor 3: Castorus data (if available)
    dom_avg = None
    pct_drops = None
    avg_drop = None

    if castorus_data:
        dom = castorus_data.get("days_on_market")
        if dom:
            dom_avg = dom
            if dom < 30:
                score += 20
                details.append(f"DOM très court ({dom}j) — tout part vite")
            elif dom < 60:
                score += 10
                details.append(f"DOM modéré ({dom}j)")
            elif dom > 120:
                score -= 15
                details.append(f"DOM très long ({dom}j) — marché lent")
            elif dom > 90:
                score -= 8
                details.append(f"DOM élevé ({dom}j)")

        if castorus_data.get("num_price_drops") is not None:
            pct_drops = castorus_data["num_price_drops"]
            if pct_drops >= 3:
                score -= 10
                details.append(f"{pct_drops} baisses successives — pression baissière forte")
            elif pct_drops >= 1:
                score -= 5
                details.append(f"{pct_drops} baisse(s) de prix")

        avg_drop = castorus_data.get("total_drop_pct")
        if avg_drop and avg_drop > 10:
            score -= 10
            details.append(f"Prix baissé de {avg_drop}% depuis mise en vente")

    score = max(0, min(100, score))

    # Negotiation recommendation
    if score >= 75:
        nego = "0-3%"
        label = "Marché très tendu"
    elif score >= 55:
        nego = "3-6%"
        label = "Marché dynamique"
    elif score >= 40:
        nego = "5-8%"
        label = "Marché équilibré"
    elif score >= 25:
        nego = "8-12%"
        label = "Marché détendu"
    else:
        nego = "10-15%"
        label = "Marché très détendu"

    if not details:
        details.append(f"Score de tension basé sur la zone ({zone})")

    return {
        "score": score,
        "label": label,
        "dom_avg": dom_avg,
        "pct_price_drops": pct_drops,
        "avg_drop_amplitude": avg_drop,
        "stock_flow_ratio": stock_flow,
        "negotiation_margin_pct": nego,
        "detail": " | ".join(details),
        "num_active_listings": num_listings,
        "num_transactions_dvf": num_transactions,
    }


def calculate_market_coefficient(spread: Dict, tension: Dict,
                                 castorus_specific: Optional[Dict] = None) -> Dict:
    """
    Calculate the "Couche 2" market coefficient.
    Adjusts DVF estimate for current market conditions.
    """
    base_coeff = 1.0
    tension_score = tension.get("score", 50)

    # Tension adjustment
    if tension_score >= 70:
        base_coeff += 0.02
    elif tension_score >= 55:
        base_coeff += 0.01
    elif tension_score <= 30:
        base_coeff -= 0.03
    elif tension_score <= 40:
        base_coeff -= 0.01

    # Specific listing adjustment
    listing_adjustment = 0
    listing_details = []

    if castorus_specific:
        dom = castorus_specific.get("days_on_market")
        drops = castorus_specific.get("num_price_drops", 0)
        total_drop = castorus_specific.get("total_drop_pct", 0)

        if dom and dom > 120:
            listing_adjustment -= 0.04
            listing_details.append(f"En vente depuis {dom}j (+120j = décote -4%)")
        elif dom and dom > 90:
            listing_adjustment -= 0.03
            listing_details.append(f"En vente depuis {dom}j (décote -3%)")
        elif dom and dom > 60:
            listing_adjustment -= 0.015
            listing_details.append(f"En vente depuis {dom}j (décote -1.5%)")
        elif dom and dom < 15 and tension_score >= 60:
            listing_details.append("Annonce récente en marché tendu — prix ferme")

        if drops >= 3:
            listing_adjustment -= 0.03
            listing_details.append(f"{drops} baisses de prix — forte pression vendeuse")
        elif drops >= 2:
            listing_adjustment -= 0.02
            listing_details.append(f"{drops} baisses de prix — pression vendeuse")
        elif drops == 1:
            listing_adjustment -= 0.01
            listing_details.append("1 baisse de prix — le vendeur est flexible")

        if total_drop and total_drop > 10:
            listing_adjustment -= 0.02
            listing_details.append(f"Déjà baissé de {total_drop}% au total")
        elif total_drop and total_drop > 5:
            listing_adjustment -= 0.01
            listing_details.append(f"Baissé de {total_drop}% depuis mise en vente")

    final_coeff = round(base_coeff + listing_adjustment, 4)
    final_coeff = max(0.85, min(1.10, final_coeff))

    return {
        "coefficient": final_coeff,
        "base_coefficient": round(base_coeff, 4),
        "listing_adjustment": round(listing_adjustment, 4),
        "tension_factor": tension_score,
        "details": listing_details,
        "explanation": f"Coefficient marché = {final_coeff:.3f} (tension {tension_score}/100, spread {spread.get('spread_pct', '?')}%)",
    }


def estimate_transaction_price_from_asking(asking_price: float, spread_pct: float,
                                            tension_score: int,
                                            castorus_data: Optional[Dict] = None) -> Dict:
    """
    Given an asking price and the local spread, estimate the probable transaction price.
    This is the KEY insight: prix affiché != prix de transaction.
    """
    base_discount = spread_pct / 100

    # Adjust based on tension
    if tension_score >= 70:
        adjusted_discount = base_discount * 0.7
    elif tension_score <= 30:
        adjusted_discount = base_discount * 1.3
    else:
        adjusted_discount = base_discount

    # Specific listing adjustments from Castorus
    if castorus_data:
        dom = castorus_data.get("days_on_market", 0)
        drops = castorus_data.get("num_price_drops", 0)
        total_drop = castorus_data.get("total_drop_pct", 0)
        if dom and dom > 120:
            adjusted_discount += 0.04
        elif dom and dom > 60:
            adjusted_discount += 0.02
        if drops >= 2:
            adjusted_discount += 0.02
        if total_drop and total_drop > 5:
            adjusted_discount += 0.01

    adjusted_discount = min(0.25, max(0, adjusted_discount))

    estimated = round(asking_price * (1 - adjusted_discount))
    low = round(asking_price * (1 - adjusted_discount - 0.03))
    high = round(asking_price * (1 - max(0, adjusted_discount - 0.02)))

    return {
        "asking_price": asking_price,
        "estimated_transaction_price": estimated,
        "estimated_transaction_low": low,
        "estimated_transaction_high": high,
        "discount_pct": round(adjusted_discount * 100, 1),
        "spread_used": spread_pct,
        "tension_used": tension_score,
    }
