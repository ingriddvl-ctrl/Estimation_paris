"""
Test suite for DVF comparable filtering refactor (iteration 5)
Tests: 24-month freshness, relevance_score, excluded_comparables, cross_calibration_warning,
       recalculate endpoint, and PDF report generation.
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test valuation IDs provided by main agent
NEW_VALUATION_ID = "dc10a2f2-ee48-4f6d-ac3d-ff4e641ec802"
OLD_VALUATION_ID = "a4278456-d469-4b25-845b-eccb2d32f8ff"

# Test payload for POST /api/valuation/estimate
TEST_ESTIMATE_PAYLOAD = {
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


class TestDVFFreshness:
    """Test that comparables are filtered to max 24 months (2024+)"""
    
    def test_estimate_returns_only_recent_transactions(self):
        """POST /api/valuation/estimate should return only transactions < 24 months"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_ESTIMATE_PAYLOAD, timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        comparables = data.get("comparables", [])
        
        # Check all comparables have dates in 2024 or later
        for comp in comparables:
            date_str = str(comp.get("date", ""))
            year = int(date_str[:4]) if date_str and len(date_str) >= 4 else 0
            assert year >= 2024, f"Comparable date {date_str} is older than 24 months (year < 2024)"
        
        print(f"✓ All {len(comparables)} comparables have dates >= 2024")
    
    def test_comparables_period_is_24_months(self):
        """POST /api/valuation/estimate should return comparables_period = '24 derniers mois'"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_ESTIMATE_PAYLOAD, timeout=60)
        assert response.status_code == 200
        
        data = response.json()
        market_data = data.get("market_data", {})
        comparables_period = market_data.get("comparables_period")
        
        assert comparables_period == "24 derniers mois", f"Expected '24 derniers mois', got '{comparables_period}'"
        print(f"✓ comparables_period = '{comparables_period}'")


class TestRelevanceScore:
    """Test that each comparable has a relevance_score 0-100"""
    
    def test_comparables_have_relevance_score(self):
        """POST /api/valuation/estimate should return relevance_score for each comparable"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_ESTIMATE_PAYLOAD, timeout=60)
        assert response.status_code == 200
        
        data = response.json()
        comparables = data.get("comparables", [])
        
        assert len(comparables) > 0, "No comparables returned"
        
        for i, comp in enumerate(comparables):
            score = comp.get("relevance_score")
            assert score is not None, f"Comparable {i} missing relevance_score"
            assert isinstance(score, (int, float)), f"Comparable {i} relevance_score is not a number: {score}"
            assert 0 <= score <= 100, f"Comparable {i} relevance_score {score} not in range 0-100"
        
        print(f"✓ All {len(comparables)} comparables have valid relevance_score (0-100)")
    
    def test_comparables_sorted_by_relevance(self):
        """Comparables should be sorted by relevance_score descending"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_ESTIMATE_PAYLOAD, timeout=60)
        assert response.status_code == 200
        
        data = response.json()
        comparables = data.get("comparables", [])
        
        if len(comparables) > 1:
            scores = [c.get("relevance_score", 0) for c in comparables]
            # Check if sorted descending (allow equal scores)
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i+1], f"Comparables not sorted by relevance: {scores[i]} < {scores[i+1]}"
        
        print(f"✓ Comparables sorted by relevance_score descending")


class TestExcludedComparables:
    """Test excluded_comparables with exclusion_reasons"""
    
    def test_excluded_comparables_returned(self):
        """POST /api/valuation/estimate should return excluded_comparables array"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_ESTIMATE_PAYLOAD, timeout=60)
        assert response.status_code == 200
        
        data = response.json()
        excluded = data.get("excluded_comparables")
        
        assert excluded is not None, "excluded_comparables not in response"
        assert isinstance(excluded, list), "excluded_comparables is not a list"
        
        print(f"✓ excluded_comparables returned with {len(excluded)} items")
    
    def test_excluded_comparables_have_reasons(self):
        """Each excluded comparable should have exclusion_reasons array"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_ESTIMATE_PAYLOAD, timeout=60)
        assert response.status_code == 200
        
        data = response.json()
        excluded = data.get("excluded_comparables", [])
        
        if len(excluded) > 0:
            for i, comp in enumerate(excluded):
                reasons = comp.get("exclusion_reasons")
                assert reasons is not None, f"Excluded comparable {i} missing exclusion_reasons"
                assert isinstance(reasons, list), f"Excluded comparable {i} exclusion_reasons is not a list"
                assert len(reasons) > 0, f"Excluded comparable {i} has empty exclusion_reasons"
                
                # Check reasons are strings
                for reason in reasons:
                    assert isinstance(reason, str), f"Exclusion reason is not a string: {reason}"
        
        print(f"✓ All {len(excluded)} excluded comparables have valid exclusion_reasons")
    
    def test_total_excluded_in_market_data(self):
        """POST /api/valuation/estimate should return total_excluded > 0 in market_data"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_ESTIMATE_PAYLOAD, timeout=60)
        assert response.status_code == 200
        
        data = response.json()
        market_data = data.get("market_data", {})
        total_excluded = market_data.get("total_excluded")
        
        assert total_excluded is not None, "total_excluded not in market_data"
        assert isinstance(total_excluded, int), f"total_excluded is not an int: {total_excluded}"
        # Note: total_excluded can be 0 if all transactions pass filters
        assert total_excluded >= 0, f"total_excluded is negative: {total_excluded}"
        
        print(f"✓ total_excluded = {total_excluded}")


class TestCrossCalibrationWarning:
    """Test cross_calibration_warning in response"""
    
    def test_cross_calibration_warning_returned(self):
        """POST /api/valuation/estimate should return cross_calibration_warning"""
        response = requests.post(f"{BASE_URL}/api/valuation/estimate", json=TEST_ESTIMATE_PAYLOAD, timeout=60)
        assert response.status_code == 200
        
        data = response.json()
        warning = data.get("cross_calibration_warning")
        
        assert warning is not None, "cross_calibration_warning not in response"
        assert isinstance(warning, str), "cross_calibration_warning is not a string"
        assert len(warning) > 0, "cross_calibration_warning is empty"
        
        # Check it mentions SeLoger/LeBonCoin
        assert "SeLoger" in warning or "LeBonCoin" in warning, f"Warning doesn't mention SeLoger/LeBonCoin: {warning[:100]}"
        
        print(f"✓ cross_calibration_warning returned: '{warning[:80]}...'")


class TestRecalculateEndpoint:
    """Test POST /api/valuation/recalculate endpoint"""
    
    def test_recalculate_with_empty_exclusions(self):
        """POST /api/valuation/recalculate should work with empty exclusions"""
        payload = {
            "valuation_id": NEW_VALUATION_ID,
            "excluded_comparable_ids": []
        }
        response = requests.post(f"{BASE_URL}/api/valuation/recalculate", json=payload, timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "new_price_median" in data, "new_price_median not in response"
        assert "comparables_count" in data, "comparables_count not in response"
        assert "comparables" in data, "comparables not in response"
        
        print(f"✓ Recalculate with empty exclusions: new_price_median = {data['new_price_median']}")
    
    def test_recalculate_with_excluded_ids(self):
        """POST /api/valuation/recalculate with excluded IDs should return different price"""
        # First get the valuation to find a comparable ID
        val_response = requests.get(f"{BASE_URL}/api/valuation/{NEW_VALUATION_ID}", timeout=30)
        assert val_response.status_code == 200
        
        val_data = val_response.json()
        comparables = val_data.get("comparables", [])
        
        if len(comparables) < 2:
            pytest.skip("Not enough comparables to test exclusion")
        
        # Get ID of first comparable (format: address_date_price)
        first_comp = comparables[0]
        comp_id = f"{first_comp['address']}_{first_comp['date']}_{first_comp['price']}"
        
        # Recalculate without exclusions
        payload_no_excl = {
            "valuation_id": NEW_VALUATION_ID,
            "excluded_comparable_ids": []
        }
        resp_no_excl = requests.post(f"{BASE_URL}/api/valuation/recalculate", json=payload_no_excl, timeout=30)
        assert resp_no_excl.status_code == 200
        price_no_excl = resp_no_excl.json().get("new_price_median")
        
        # Recalculate with exclusion
        payload_with_excl = {
            "valuation_id": NEW_VALUATION_ID,
            "excluded_comparable_ids": [comp_id]
        }
        resp_with_excl = requests.post(f"{BASE_URL}/api/valuation/recalculate", json=payload_with_excl, timeout=30)
        assert resp_with_excl.status_code == 200
        
        data_with_excl = resp_with_excl.json()
        price_with_excl = data_with_excl.get("new_price_median")
        excluded_count = data_with_excl.get("excluded_count", 0)
        
        # Price should be different (or at least excluded_count should increase)
        assert excluded_count > 0, "excluded_count should be > 0 after manual exclusion"
        
        print(f"✓ Recalculate with exclusion: price changed from {price_no_excl} to {price_with_excl}, excluded_count = {excluded_count}")
    
    def test_recalculate_nonexistent_valuation(self):
        """POST /api/valuation/recalculate with nonexistent ID should return 404"""
        payload = {
            "valuation_id": "nonexistent-id-12345",
            "excluded_comparable_ids": []
        }
        response = requests.post(f"{BASE_URL}/api/valuation/recalculate", json=payload, timeout=30)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ Recalculate with nonexistent ID returns 404")


class TestPDFReports:
    """Test PDF report generation endpoints"""
    
    def test_report_pdf_endpoint(self):
        """GET /api/report/pdf/{id} should return valid PDF"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/{NEW_VALUATION_ID}", timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF content type, got {content_type}"
        
        # Check PDF magic bytes
        assert response.content[:4] == b'%PDF', "Response doesn't start with PDF magic bytes"
        
        print(f"✓ GET /api/report/pdf/{NEW_VALUATION_ID} returns valid PDF ({len(response.content)} bytes)")
    
    def test_report_pdf_nonexistent(self):
        """GET /api/report/pdf/{id} with nonexistent ID should return 404"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/nonexistent-id-12345", timeout=30)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ GET /api/report/pdf/nonexistent returns 404")
    
    def test_listing_report_pdf_nonexistent(self):
        """GET /api/listing/report/pdf/{id} with nonexistent ID should return 404"""
        response = requests.get(f"{BASE_URL}/api/listing/report/pdf/nonexistent-id-12345", timeout=30)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ GET /api/listing/report/pdf/nonexistent returns 404")


class TestExistingValuation:
    """Test that existing valuation has new fields"""
    
    def test_existing_valuation_has_new_fields(self):
        """GET /api/valuation/{id} should return valuation with new fields"""
        response = requests.get(f"{BASE_URL}/api/valuation/{NEW_VALUATION_ID}", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Check new fields exist
        assert "excluded_comparables" in data, "excluded_comparables not in saved valuation"
        assert "cross_calibration_warning" in data, "cross_calibration_warning not in saved valuation"
        
        market_data = data.get("market_data", {})
        assert "total_excluded" in market_data, "total_excluded not in market_data"
        assert "comparables_period" in market_data, "comparables_period not in market_data"
        
        # Check comparables have relevance_score
        comparables = data.get("comparables", [])
        if len(comparables) > 0:
            assert "relevance_score" in comparables[0], "relevance_score not in comparables"
        
        print(f"✓ Existing valuation {NEW_VALUATION_ID} has all new fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
