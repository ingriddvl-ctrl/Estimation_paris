"""
Test suite for the new valuation engine features:
- Progressive radius DVF search (200m→300m→500m→800m)
- Weighted median price (distance + freshness)
- Micro-score computation
- search_radius_m and distance_m fields in response
- base_source should mention 'médiane pondérée' not 'Moyenne parisienne'
- Listing PDF endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test payload for valuation estimate
TEST_VALUATION_PAYLOAD = {
    "location": {
        "address": "22 Avenue de Lamballe 75016 Paris",
        "postal_code": "75016",
        "floor": 7,
        "latitude": 48.8575,
        "longitude": 2.2745
    },
    "characteristics": {
        "surface_carrez": 89,
        "rooms": 4,
        "bedrooms": 3,
        "bathrooms": 1,
        "exposure": "sud",
        "view": "degagee",
        "exterior_type": "balcon",
        "exterior_surface": 6,
        "ceiling_height": "2.80-3.20",
        "parking": "aucun",
        "cave": True
    },
    "condition": {
        "general_state": "bon_etat",
        "dpe": "D",
        "windows": "double_vitrage"
    },
    "building": {
        "construction_era": "haussmannien",
        "building_type": "pierre_taille",
        "total_floors": 8,
        "elevator": True,
        "concierge": True,
        "total_lots": 18
    },
    "legal": {
        "ownership_type": "pleine_propriete"
    }
}

EXISTING_VALUATION_ID = "ca781754-4fdc-45bb-8a46-8faac27c9b07"


class TestValuationEstimateEndpoint:
    """Tests for POST /api/valuation/estimate with new progressive DVF search"""

    def test_estimate_returns_200(self):
        """Test that estimate endpoint returns 200 with valid payload"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_VALUATION_PAYLOAD, timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ POST /api/valuation/estimate returns 200")

    def test_estimate_returns_search_radius_m(self):
        """Test that response includes search_radius_m in market_data"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_VALUATION_PAYLOAD, timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "market_data" in data, "Response missing market_data"
        market_data = data["market_data"]
        assert "search_radius_m" in market_data, "market_data missing search_radius_m"
        
        search_radius = market_data["search_radius_m"]
        assert search_radius in [200, 300, 500, 800], f"search_radius_m should be one of [200, 300, 500, 800], got {search_radius}"
        print(f"✓ search_radius_m present in response: {search_radius}m")

    def test_estimate_returns_micro_score(self):
        """Test that response includes micro_score in market_data"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_VALUATION_PAYLOAD, timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        market_data = data.get("market_data", {})
        assert "micro_score" in market_data, "market_data missing micro_score"
        
        micro_score = market_data["micro_score"]
        assert isinstance(micro_score, dict), "micro_score should be a dict"
        assert "score" in micro_score, "micro_score missing 'score' field"
        assert "detail" in micro_score, "micro_score missing 'detail' field"
        assert "local_premium_pct" in micro_score, "micro_score missing 'local_premium_pct' field"
        assert "density_300m" in micro_score, "micro_score missing 'density_300m' field"
        print(f"✓ micro_score present in response: score={micro_score['score']}, premium={micro_score['local_premium_pct']}%")

    def test_estimate_comparables_have_distance_m(self):
        """Test that each comparable has distance_m field"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_VALUATION_PAYLOAD, timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        comparables = data.get("comparables", [])
        if len(comparables) > 0:
            for i, comp in enumerate(comparables[:5]):  # Check first 5
                assert "distance_m" in comp, f"Comparable {i} missing distance_m field"
                assert isinstance(comp["distance_m"], (int, float)), f"distance_m should be numeric, got {type(comp['distance_m'])}"
            print(f"✓ All comparables have distance_m field (checked {min(5, len(comparables))} of {len(comparables)})")
        else:
            print("⚠ No comparables returned (DVF API may be unavailable)")

    def test_estimate_base_source_mentions_mediane_ponderee(self):
        """Test that base_source mentions 'médiane pondérée' not 'Moyenne parisienne'"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_VALUATION_PAYLOAD, timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        market_data = data.get("market_data", {})
        base_source = market_data.get("base_source", "")
        
        # If comparables were found, base_source should mention médiane pondérée
        comparables = data.get("comparables", [])
        if len(comparables) > 0:
            assert "médiane pondérée" in base_source.lower() or "mediane ponderee" in base_source.lower(), \
                f"base_source should mention 'médiane pondérée' when comparables exist, got: {base_source}"
            assert "moyenne parisienne" not in base_source.lower(), \
                f"base_source should NOT mention 'Moyenne parisienne', got: {base_source}"
            print(f"✓ base_source correctly mentions 'médiane pondérée': {base_source}")
        else:
            # Fallback case - no comparables found
            print(f"⚠ No comparables found, base_source is fallback: {base_source}")


class TestPdfReportEndpoints:
    """Tests for PDF report generation endpoints"""

    def test_valuation_pdf_returns_200(self):
        """Test GET /api/report/pdf/{valuation_id} returns PDF for existing valuation"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/{EXISTING_VALUATION_ID}", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/pdf" in response.headers.get("Content-Type", ""), "Response should be PDF"
        assert response.content[:4] == b"%PDF", "PDF content should start with %PDF"
        print(f"✓ GET /api/report/pdf/{EXISTING_VALUATION_ID} returns valid PDF")

    def test_valuation_pdf_returns_404_for_nonexistent(self):
        """Test GET /api/report/pdf/{valuation_id} returns 404 for nonexistent ID"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/nonexistent-id-12345", timeout=30)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/report/pdf/nonexistent returns 404")

    def test_listing_pdf_returns_404_for_nonexistent(self):
        """Test GET /api/listing/report/pdf/{analysis_id} returns 404 for nonexistent ID"""
        response = requests.get(f"{BASE_URL}/api/listing/report/pdf/nonexistent-analysis-id", timeout=30)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/listing/report/pdf/nonexistent returns 404")


class TestExistingEndpoints:
    """Verify existing endpoints still work"""

    def test_health_check(self):
        """Test basic API health"""
        response = requests.get(f"{BASE_URL}/api/", timeout=10)
        # May return 404 if no root endpoint, but server should respond
        assert response.status_code in [200, 404], f"Server not responding: {response.status_code}"
        print("✓ Server is responding")

    def test_address_search(self):
        """Test address search endpoint"""
        response = requests.get(f"{BASE_URL}/api/address/search", params={"q": "22 Avenue de Lamballe"}, timeout=15)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Address search returns {len(data)} results")

    def test_get_valuation(self):
        """Test getting existing valuation"""
        response = requests.get(f"{BASE_URL}/api/valuation/{EXISTING_VALUATION_ID}", timeout=15)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "id" in data or "price_median" in data, "Response should contain valuation data"
        print(f"✓ GET /api/valuation/{EXISTING_VALUATION_ID} returns valuation data")

    def test_list_valuations(self):
        """Test listing valuations"""
        response = requests.get(f"{BASE_URL}/api/valuations", timeout=15)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/valuations returns {len(data)} valuations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
