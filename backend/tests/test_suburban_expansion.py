"""
Test suite for suburban expansion (Paris + petite couronne 92/93/94)
Tests the extension of the tool from Paris-only to Paris + petite couronne.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ─── Address Search Tests ───

class TestAddressSearchSuburban:
    """Tests for address search API returning suburban addresses (92, 93, 94)"""
    
    def test_search_neuilly_with_postal_code(self):
        """GET /api/address/search?q=92200 should return Neuilly-sur-Seine results"""
        response = requests.get(f"{BASE_URL}/api/address/search", params={"q": "92200"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0, "Should return results for 92200"
        # Check first result is Neuilly
        assert results[0]["postal_code"] == "92200"
        assert "Neuilly" in results[0]["city"] or "Neuilly" in results[0]["label"]
    
    def test_search_avenue_charles_de_gaulle_neuilly(self):
        """GET /api/address/search?q=avenue charles de gaulle neuilly should return 92200 results"""
        response = requests.get(f"{BASE_URL}/api/address/search", params={"q": "avenue charles de gaulle neuilly"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0, "Should return results for Neuilly address"
        assert results[0]["postal_code"].startswith("92"), f"Expected 92xxx postal code, got {results[0]['postal_code']}"
    
    def test_search_boulogne(self):
        """GET /api/address/search?q=boulogne should return 92100 results"""
        response = requests.get(f"{BASE_URL}/api/address/search", params={"q": "boulogne"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0, "Should return results for Boulogne"
        # At least one result should be 92100
        postal_codes = [r["postal_code"] for r in results]
        assert any(pc.startswith("92") for pc in postal_codes), f"Expected 92xxx postal code in results: {postal_codes}"
    
    def test_search_montreuil_93(self):
        """GET /api/address/search?q=montreuil 93 should return 93100 results"""
        response = requests.get(f"{BASE_URL}/api/address/search", params={"q": "montreuil 93"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0, "Should return results for Montreuil"
        assert results[0]["postal_code"].startswith("93"), f"Expected 93xxx postal code, got {results[0]['postal_code']}"
    
    def test_search_vincennes_94(self):
        """GET /api/address/search?q=vincennes 94 should return 94300 results"""
        response = requests.get(f"{BASE_URL}/api/address/search", params={"q": "vincennes 94"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0, "Should return results for Vincennes"
        assert results[0]["postal_code"].startswith("94"), f"Expected 94xxx postal code, got {results[0]['postal_code']}"
    
    def test_search_filters_non_idf(self):
        """GET /api/address/search?q=marseille should return empty or only IDF results"""
        response = requests.get(f"{BASE_URL}/api/address/search", params={"q": "marseille"})
        assert response.status_code == 200
        results = response.json()
        # All results should be in 75/92/93/94
        for r in results:
            pc = r.get("postal_code", "")
            assert pc.startswith(("75", "92", "93", "94")), f"Non-IDF result found: {r}"
    
    def test_search_paris_still_works(self):
        """GET /api/address/search?q=rue de rivoli paris should return 75xxx results (no regression)"""
        response = requests.get(f"{BASE_URL}/api/address/search", params={"q": "rue de rivoli paris"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0, "Should return results for Paris address"
        assert results[0]["postal_code"].startswith("75"), f"Expected 75xxx postal code, got {results[0]['postal_code']}"


# ─── Valuation Estimate Tests ───

class TestValuationSuburban:
    """Tests for valuation estimate API with suburban addresses"""
    
    @pytest.fixture
    def neuilly_payload(self):
        """Payload for Neuilly (92200) valuation"""
        return {
            "location": {
                "address": "Avenue Charles de Gaulle 92200 Neuilly-sur-Seine",
                "postal_code": "92200",
                "city": "Neuilly-sur-Seine",
                "latitude": 48.882391,
                "longitude": 2.268338,
                "floor": 3
            },
            "characteristics": {
                "surface_carrez": 70,
                "rooms": 3,
                "bedrooms": 2,
                "bathrooms": 1,
                "property_type": "appartement"
            },
            "condition": {"general_state": "bon_etat", "dpe": "D"},
            "building": {"elevator": True, "building_type": "pierre_taille"},
            "legal": {}
        }
    
    @pytest.fixture
    def paris_payload(self):
        """Payload for Paris (75004) valuation"""
        return {
            "location": {
                "address": "5 Rue de Rivoli 75004 Paris",
                "postal_code": "75004",
                "city": "Paris",
                "latitude": 48.855648,
                "longitude": 2.358797,
                "floor": 3
            },
            "characteristics": {
                "surface_carrez": 70,
                "rooms": 3,
                "bedrooms": 2,
                "bathrooms": 1,
                "property_type": "appartement"
            },
            "condition": {"general_state": "bon_etat", "dpe": "D"},
            "building": {"elevator": True, "building_type": "pierre_taille"},
            "legal": {}
        }
    
    def test_neuilly_valuation_zone_label(self, neuilly_payload):
        """POST /api/valuation/estimate for Neuilly should return zone_label='Neuilly-sur-Seine'"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=neuilly_payload)
        assert response.status_code == 200
        data = response.json()
        market_data = data.get("market_data", {})
        assert market_data.get("zone_label") == "Neuilly-sur-Seine", f"Expected zone_label='Neuilly-sur-Seine', got {market_data.get('zone_label')}"
    
    def test_neuilly_valuation_is_paris_false(self, neuilly_payload):
        """POST /api/valuation/estimate for Neuilly should return is_paris=False"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=neuilly_payload)
        assert response.status_code == 200
        data = response.json()
        market_data = data.get("market_data", {})
        assert market_data.get("is_paris") is False, f"Expected is_paris=False, got {market_data.get('is_paris')}"
    
    def test_neuilly_valuation_has_comparables(self, neuilly_payload):
        """POST /api/valuation/estimate for Neuilly should return comparables"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=neuilly_payload)
        assert response.status_code == 200
        data = response.json()
        comparables = data.get("comparables", [])
        assert len(comparables) > 0, "Should have comparables for Neuilly"
        market_data = data.get("market_data", {})
        assert market_data.get("total_comparables", 0) > 0, "total_comparables should be > 0"
    
    def test_paris_valuation_zone_label(self, paris_payload):
        """POST /api/valuation/estimate for Paris 75004 should return zone_label='04e arrondissement' (NO REGRESSION)"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=paris_payload)
        assert response.status_code == 200
        data = response.json()
        market_data = data.get("market_data", {})
        assert market_data.get("zone_label") == "04e arrondissement", f"Expected zone_label='04e arrondissement', got {market_data.get('zone_label')}"
    
    def test_paris_valuation_is_paris_true(self, paris_payload):
        """POST /api/valuation/estimate for Paris 75004 should return is_paris=True (NO REGRESSION)"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=paris_payload)
        assert response.status_code == 200
        data = response.json()
        market_data = data.get("market_data", {})
        assert market_data.get("is_paris") is True, f"Expected is_paris=True, got {market_data.get('is_paris')}"
    
    def test_montreuil_valuation(self):
        """POST /api/valuation/estimate for Montreuil (93100) should work"""
        payload = {
            "location": {
                "address": "Rue de Paris 93100 Montreuil",
                "postal_code": "93100",
                "city": "Montreuil",
                "latitude": 48.863728,
                "longitude": 2.449364,
                "floor": 2
            },
            "characteristics": {"surface_carrez": 50, "rooms": 2},
            "condition": {"general_state": "bon_etat", "dpe": "D"},
            "building": {"elevator": False},
            "legal": {}
        }
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        market_data = data.get("market_data", {})
        assert market_data.get("zone_label") == "Montreuil", f"Expected zone_label='Montreuil', got {market_data.get('zone_label')}"
        assert market_data.get("is_paris") is False
    
    def test_vincennes_valuation(self):
        """POST /api/valuation/estimate for Vincennes (94300) should work"""
        payload = {
            "location": {
                "address": "Avenue de Paris 94300 Vincennes",
                "postal_code": "94300",
                "city": "Vincennes",
                "latitude": 48.847279,
                "longitude": 2.437785,
                "floor": 4
            },
            "characteristics": {"surface_carrez": 60, "rooms": 3},
            "condition": {"general_state": "bon_etat", "dpe": "C"},
            "building": {"elevator": True},
            "legal": {}
        }
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        market_data = data.get("market_data", {})
        assert market_data.get("zone_label") == "Vincennes", f"Expected zone_label='Vincennes', got {market_data.get('zone_label')}"
        assert market_data.get("is_paris") is False


# ─── Circle Stats and Reliability Tests ───

class TestCircleStatsAndReliability:
    """Tests for concentric circle badges and reliability indicator"""
    
    def test_valuation_has_circle_stats(self):
        """POST /api/valuation/estimate should return circle_stats"""
        payload = {
            "location": {
                "address": "Avenue Charles de Gaulle 92200 Neuilly-sur-Seine",
                "postal_code": "92200",
                "latitude": 48.882391,
                "longitude": 2.268338,
                "floor": 3
            },
            "characteristics": {"surface_carrez": 70, "rooms": 3},
            "condition": {"general_state": "bon_etat", "dpe": "D"},
            "building": {"elevator": True},
            "legal": {}
        }
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Check circle_stats exists
        circle_stats = data.get("circle_stats", {})
        assert "circle_1_count" in circle_stats, "circle_stats should have circle_1_count"
        assert "circle_2_count" in circle_stats, "circle_stats should have circle_2_count"
        assert "circle_3_count" in circle_stats, "circle_stats should have circle_3_count"
        assert "reliability" in circle_stats, "circle_stats should have reliability"
    
    def test_comparables_have_circle_field(self):
        """POST /api/valuation/estimate comparables should have circle field (1, 2, or 3)"""
        payload = {
            "location": {
                "address": "5 Rue de Rivoli 75004 Paris",
                "postal_code": "75004",
                "latitude": 48.855648,
                "longitude": 2.358797,
                "floor": 3
            },
            "characteristics": {"surface_carrez": 70, "rooms": 3},
            "condition": {"general_state": "bon_etat", "dpe": "D"},
            "building": {"elevator": True},
            "legal": {}
        }
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        comparables = data.get("comparables", [])
        if len(comparables) > 0:
            for comp in comparables[:5]:  # Check first 5
                assert "circle" in comp, f"Comparable should have circle field: {comp}"
                assert comp["circle"] in [1, 2, 3], f"Circle should be 1, 2, or 3, got {comp['circle']}"
    
    def test_reliability_indicator_values(self):
        """POST /api/valuation/estimate reliability should be HAUTE, MOYENNE, or BASSE"""
        payload = {
            "location": {
                "address": "Avenue Charles de Gaulle 92200 Neuilly-sur-Seine",
                "postal_code": "92200",
                "latitude": 48.882391,
                "longitude": 2.268338,
                "floor": 3
            },
            "characteristics": {"surface_carrez": 70, "rooms": 3},
            "condition": {"general_state": "bon_etat", "dpe": "D"},
            "building": {"elevator": True},
            "legal": {}
        }
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        market_data = data.get("market_data", {})
        reliability = market_data.get("reliability")
        assert reliability in ["HAUTE", "MOYENNE", "BASSE"], f"Reliability should be HAUTE/MOYENNE/BASSE, got {reliability}"


# ─── PDF Report Tests ───

class TestPdfReport:
    """Tests for PDF report generation"""
    
    @pytest.fixture
    def saved_valuation_id(self):
        """Create and save a valuation, return its ID"""
        payload = {
            "location": {
                "address": "TEST Avenue Charles de Gaulle 92200 Neuilly-sur-Seine",
                "postal_code": "92200",
                "latitude": 48.882391,
                "longitude": 2.268338,
                "floor": 3
            },
            "characteristics": {"surface_carrez": 70, "rooms": 3},
            "condition": {"general_state": "bon_etat", "dpe": "D"},
            "building": {"elevator": True},
            "legal": {}
        }
        # Create valuation
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        valuation_id = data.get("id")
        
        # Save valuation
        save_response = requests.post(f"{BASE_URL}/api/valuation/save", json=data)
        assert save_response.status_code == 200
        
        return valuation_id
    
    def test_pdf_report_generation(self, saved_valuation_id):
        """GET /api/report/pdf/{id} should return valid PDF"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/{saved_valuation_id}")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        # Check PDF magic bytes
        assert response.content[:4] == b"%PDF", "Response should be a valid PDF"
    
    def test_pdf_report_nonexistent(self):
        """GET /api/report/pdf/nonexistent should return 404"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/nonexistent-id-12345")
        assert response.status_code == 404


# ─── Recalculate Tests ───

class TestRecalculate:
    """Tests for manual comparable exclusion and recalculate"""
    
    @pytest.fixture
    def saved_valuation_with_comparables(self):
        """Create and save a valuation with comparables"""
        payload = {
            "location": {
                "address": "TEST 5 Rue de Rivoli 75004 Paris",
                "postal_code": "75004",
                "latitude": 48.855648,
                "longitude": 2.358797,
                "floor": 3
            },
            "characteristics": {"surface_carrez": 70, "rooms": 3},
            "condition": {"general_state": "bon_etat", "dpe": "D"},
            "building": {"elevator": True},
            "legal": {}
        }
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Save valuation
        save_response = requests.post(f"{BASE_URL}/api/valuation/save", json=data)
        assert save_response.status_code == 200
        
        return data
    
    def test_recalculate_with_exclusions(self, saved_valuation_with_comparables):
        """POST /api/valuation/recalculate should work with excluded comparables"""
        valuation_id = saved_valuation_with_comparables.get("id")
        comparables = saved_valuation_with_comparables.get("comparables", [])
        
        if len(comparables) < 2:
            pytest.skip("Not enough comparables to test exclusion")
        
        # Exclude first comparable
        first_comp = comparables[0]
        excluded_id = f"{first_comp['address']}_{first_comp['date']}_{first_comp['price']}"
        
        recalc_payload = {
            "valuation_id": valuation_id,
            "excluded_comparable_ids": [excluded_id]
        }
        
        response = requests.post(f"{BASE_URL}/api/valuation/recalculate", json=recalc_payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "new_price_median" in data, "Recalculate should return new_price_median"
        assert "comparables_count" in data, "Recalculate should return comparables_count"
        assert "excluded_count" in data, "Recalculate should return excluded_count"
        # The excluded_count should be > 0 since we excluded one comparable
        assert data["excluded_count"] > 0, "Should have at least 1 excluded comparable"
    
    def test_recalculate_nonexistent_valuation(self):
        """POST /api/valuation/recalculate with nonexistent ID should return 404"""
        recalc_payload = {
            "valuation_id": "nonexistent-id-12345",
            "excluded_comparable_ids": []
        }
        response = requests.post(f"{BASE_URL}/api/valuation/recalculate", json=recalc_payload)
        assert response.status_code == 404


# ─── Zone Classification Tests ───

class TestZoneClassification:
    """Tests for zone classification (central, intermediate, peripheral)"""
    
    def test_paris_central_zone(self):
        """Paris 75004 should be classified as 'central' zone"""
        payload = {
            "location": {"postal_code": "75004", "latitude": 48.855648, "longitude": 2.358797},
            "characteristics": {"surface_carrez": 50},
            "condition": {},
            "building": {},
            "legal": {}
        }
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["market_data"]["zone"] == "central"
    
    def test_neuilly_intermediate_zone(self):
        """Neuilly 92200 should be classified as 'intermediate' zone (premium suburb)"""
        payload = {
            "location": {"postal_code": "92200", "latitude": 48.882391, "longitude": 2.268338},
            "characteristics": {"surface_carrez": 50},
            "condition": {},
            "building": {},
            "legal": {}
        }
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["market_data"]["zone"] == "intermediate"
    
    def test_creteil_peripheral_zone(self):
        """Créteil 94000 should be classified as 'peripheral' zone"""
        payload = {
            "location": {"postal_code": "94000", "latitude": 48.790367, "longitude": 2.455572},
            "characteristics": {"surface_carrez": 50},
            "condition": {},
            "building": {},
            "legal": {}
        }
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["market_data"]["zone"] == "peripheral"
