/**
 * Market Scraper — runs IN THE USER'S BROWSER
 * 
 * Why browser-side? BienIci, MeilleursAgents, Castorus all block requests
 * from datacenter IPs (Render, AWS, etc.). But requests from a real browser
 * pass through because they look like a normal user.
 * 
 * We use CORS proxies to bypass the same-origin restriction.
 * Multiple proxies are tried in sequence for resilience.
 */

const CORS_PROXIES = [
  (url) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
  (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
  (url) => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(url)}`,
];

async function fetchWithProxy(url, options = {}) {
  const timeout = options.timeout || 12000;

  for (let i = 0; i < CORS_PROXIES.length; i++) {
    const proxyUrl = CORS_PROXIES[i](url);
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeout);
      const resp = await fetch(proxyUrl, {
        signal: controller.signal,
        headers: { "Accept": "text/html,application/json,*/*" },
      });
      clearTimeout(timer);
      if (resp.ok) {
        return resp;
      }
    } catch (e) {
      console.warn(`Proxy ${i + 1} failed for ${url}:`, e.message);
      continue;
    }
  }
  return null;
}


// ── BienIci Scraper ──

function postalToInsee(postalCode) {
  if (postalCode.startsWith("75") && postalCode.length === 5) {
    const arr = parseInt(postalCode.substring(3));
    if (arr >= 1 && arr <= 20) {
      return `751${arr.toString().padStart(2, "0")}`;
    }
  }
  return postalCode;
}

export async function scrapeBienIciListings(postalCode, { surfaceMin = 20, surfaceMax = 200, roomsMin = 1, roomsMax = 6 } = {}) {
  try {
    // Step 1: Resolve zone
    const isParis = postalCode.startsWith("75");
    const arrNum = isParis ? parseInt(postalCode.slice(-2)) : 0;
    const query = isParis ? `paris ${arrNum}e arrondissement` : postalCode;
    const inseeCode = postalToInsee(postalCode);

    const suggestUrl = `https://res.bienici.com/suggest.json?q=${encodeURIComponent(query)}`;
    const suggestResp = await fetchWithProxy(suggestUrl);
    if (!suggestResp) {
      console.warn("BienIci suggest failed");
      return [];
    }

    const suggestions = await suggestResp.json();
    let zoneIds = [];
    let insee = inseeCode;

    for (const s of suggestions) {
      const postcodes = s.postalCodes || [];
      const inseeCodes = s.insee_codes || [];
      const inseeCode2 = s.insee_code || "";
      if (
        postcodes.includes(postalCode) ||
        postcodes.includes(inseeCode) ||
        inseeCodes.includes(inseeCode) ||
        inseeCode2 === inseeCode
      ) {
        zoneIds = s.zoneIds || [];
        insee = inseeCode2 || (inseeCodes[0] || inseeCode);
        break;
      }
    }

    // Fallback: use first suggestion
    if (!zoneIds.length && suggestions.length > 0) {
      zoneIds = suggestions[0].zoneIds || [];
      insee = suggestions[0].insee_code || suggestions[0].insee_codes?.[0] || inseeCode;
    }

    if (!zoneIds.length) {
      console.warn("BienIci: no zone found for", postalCode);
      return [];
    }

    // Step 2: Search listings
    const filters = {
      size: 24,
      from: 0,
      filterType: "buy",
      propertyType: ["flat"],
      minArea: surfaceMin,
      maxArea: surfaceMax,
      minRooms: roomsMin,
      maxRooms: roomsMax,
      page: 1,
      resultsPerPage: 24,
      sortBy: "relevance",
      sortOrder: "desc",
      onTheMarket: [true],
      zoneIdsByInseeCode: { [insee]: zoneIds },
    };

    const searchUrl = `https://www.bienici.com/realEstateAds.json?filters=${encodeURIComponent(JSON.stringify(filters))}`;
    const searchResp = await fetchWithProxy(searchUrl);
    if (!searchResp) {
      console.warn("BienIci search failed");
      return [];
    }

    const data = await searchResp.json();
    const ads = data.realEstateAds || [];

    const listings = [];
    for (const ad of ads) {
      const adPostal = ad.postalCode || "";
      const adCityCode = ad.cityCode || "";

      // Filter to correct area
      let isMatch = false;
      if (isParis) {
        isMatch = adPostal === postalCode || adPostal === inseeCode || adCityCode === inseeCode;
      } else {
        isMatch = adPostal === postalCode;
      }
      if (!isMatch) continue;

      let price = ad.price || 0;
      let area = ad.surfaceArea || 0;
      if (Array.isArray(price)) price = price[0] || 0;
      if (Array.isArray(area)) area = area[0] || 0;
      if (!price || !area) continue;

      let rooms = ad.roomsQuantity || 0;
      if (Array.isArray(rooms)) rooms = rooms[0] || 0;

      listings.push({
        price: Math.round(price),
        surface: Math.round(area * 10) / 10,
        price_per_sqm: area > 0 ? Math.round(price / area) : 0,
        rooms: parseInt(rooms) || 0,
        bedrooms: ad.bedroomsQuantity || 0,
        floor: ad.floor,
        city: ad.city || "",
        postal_code: adPostal,
        neighborhood: ad.district?.name || "",
        title: ad.title || "",
        url: ad.id ? `https://www.bienici.com/annonce/achat/${ad.id}` : "",
        source: "bienici_browser",
        photos: (ad.photos || []).slice(0, 1).map(p => p.url_photo || p),
      });
    }

    console.log(`BienIci browser scrape: ${listings.length} listings for ${postalCode}`);
    return listings;
  } catch (e) {
    console.error("BienIci browser scrape error:", e);
    return [];
  }
}


// ── MeilleursAgents Price/m² Scraper ──

export async function scrapeMeilleursAgentsStreet(streetName, postalCode) {
  try {
    // MeilleursAgents has a public page per street with price data in the HTML
    const slug = streetName
      .toLowerCase()
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")  // remove accents
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");

    const url = `https://www.meilleursagents.com/prix-immobilier/paris-75000/${slug}/`;
    const resp = await fetchWithProxy(url);
    if (!resp) return null;

    const html = await resp.text();

    // Extract price data from the HTML
    const data = { source: "meilleursagents", street: streetName, postal_code: postalCode };

    // Look for price/m² patterns
    const priceMatch = html.match(/(\d[\d\s]*)\s*€\/m²/g);
    if (priceMatch) {
      const prices = priceMatch
        .map(p => parseInt(p.replace(/\s/g, "")))
        .filter(p => p > 3000 && p < 25000);
      if (prices.length > 0) {
        data.price_per_sqm = prices[0];
        if (prices.length >= 2) {
          data.price_low = Math.min(...prices);
          data.price_high = Math.max(...prices);
        }
      }
    }

    // Look for the main estimation value
    const mainPrice = html.match(/prix\s*(?:moyen\s*)?(?:du\s*)?m(?:è|e)tre\s*carr(?:é|e)\s*[^0-9]*(\d[\d\s]*)\s*€/i);
    if (mainPrice) {
      data.price_per_sqm = parseInt(mainPrice[1].replace(/\s/g, ""));
    }

    if (data.price_per_sqm) {
      console.log(`MeilleursAgents: ${streetName} → ${data.price_per_sqm}€/m²`);
      return data;
    }

    return null;
  } catch (e) {
    console.error("MeilleursAgents scrape error:", e);
    return null;
  }
}


// ── Castorus Listing Lookup ──

export async function lookupCastorus(listingUrl) {
  if (!listingUrl) return null;
  try {
    const encoded = encodeURIComponent(listingUrl);
    const urls = [
      `https://www.castorus.com/s/${encoded}`,
      `https://www.castorus.com/s/?q=${encoded}`,
    ];

    for (const url of urls) {
      const resp = await fetchWithProxy(url);
      if (!resp) continue;

      const text = await resp.text();
      const data = { source: "castorus_browser", url: listingUrl };

      // Parse prices
      const prices = [...text.matchAll(/(\d[\d\s]*)\s*€/g)]
        .map(m => parseInt(m[1].replace(/\s/g, "")))
        .filter(p => p > 10000);

      // Parse dates
      const dates = [...text.matchAll(/(\d{2}\/\d{2}\/\d{4})/g)]
        .map(m => m[1]);

      if (prices.length > 0 && dates.length > 0) {
        const history = [];
        for (let i = 0; i < Math.min(prices.length, dates.length, 10); i++) {
          history.push({ price: prices[i], date: dates[i] });
        }
        if (history.length > 0) {
          data.price_history = history;
          data.initial_price = history[0].price;
          data.current_price = history[history.length - 1].price;
          data.total_drop_pct = history[0].price > 0
            ? Math.round((history[0].price - history[history.length - 1].price) / history[0].price * 1000) / 10
            : 0;
          data.num_price_drops = history.filter((h, i) => i > 0 && h.price < history[i - 1].price).length;
        }
      }

      // DOM
      const domMatch = text.match(/(\d+)\s*jour/);
      if (domMatch) {
        data.days_on_market = parseInt(domMatch[1]);
      }

      if (Object.keys(data).length > 2) {
        console.log(`Castorus browser: found data for ${listingUrl}`, data);
        return data;
      }
    }

    return null;
  } catch (e) {
    console.error("Castorus browser lookup error:", e);
    return null;
  }
}


// ── Combined Market Data Fetch ──

export async function fetchBrowserMarketData(postalCode, streetName, surface, rooms, listingUrl) {
  console.log(`Fetching browser market data for ${postalCode}, ${streetName}, ${surface}m², ${rooms}p`);

  const results = {
    listings: [],
    meilleursagents: null,
    castorus: null,
    source: "browser",
  };

  // Run all scrapers in parallel
  const [listings, maData, castorus] = await Promise.allSettled([
    scrapeBienIciListings(postalCode, {
      surfaceMin: Math.max(15, Math.round(surface * 0.5)),
      surfaceMax: Math.round(surface * 2),
      roomsMin: Math.max(1, rooms - 1),
      roomsMax: rooms + 2,
    }),
    streetName ? scrapeMeilleursAgentsStreet(streetName, postalCode) : Promise.resolve(null),
    listingUrl ? lookupCastorus(listingUrl) : Promise.resolve(null),
  ]);

  results.listings = listings.status === "fulfilled" ? listings.value : [];
  results.meilleursagents = maData.status === "fulfilled" ? maData.value : null;
  results.castorus = castorus.status === "fulfilled" ? castorus.value : null;

  // Calculate browser-side metrics
  if (results.listings.length > 0) {
    const prices = results.listings
      .map(l => l.price_per_sqm)
      .filter(p => p > 5000 && p < 25000)
      .sort((a, b) => a - b);

    if (prices.length > 0) {
      results.listing_median_sqm = prices[Math.floor(prices.length / 2)];
      results.listing_count = prices.length;
      results.listing_low_sqm = prices[0];
      results.listing_high_sqm = prices[prices.length - 1];
    }
  }

  console.log("Browser market data results:", {
    listings: results.listings.length,
    meilleursagents: !!results.meilleursagents,
    castorus: !!results.castorus,
    median: results.listing_median_sqm,
  });

  return results;
}
