"""
Test suite for new features: PDF Report Generation and Listing Analyzer
Tests the /api/report/pdf/{valuation_id} and /api/listing/analyze endpoints
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test valuation ID provided by main agent
TEST_VALUATION_ID = "ca781754-4fdc-45bb-8a46-8faac27c9b07"


class TestPdfReportGeneration:
    """Tests for PDF report generation endpoint"""
    
    def test_pdf_report_returns_200_for_existing_valuation(self):
        """Test that PDF report endpoint returns 200 for existing valuation"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/{TEST_VALUATION_ID}", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ PDF report endpoint returns 200 for existing valuation")
    
    def test_pdf_report_returns_valid_pdf_content_type(self):
        """Test that PDF report returns correct content type"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/{TEST_VALUATION_ID}", timeout=30)
        assert response.status_code == 200
        content_type = response.headers.get('content-type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        print(f"✓ PDF report returns correct content-type: {content_type}")
    
    def test_pdf_report_returns_valid_pdf_data(self):
        """Test that PDF report returns valid PDF data (starts with %PDF)"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/{TEST_VALUATION_ID}", timeout=30)
        assert response.status_code == 200
        content = response.content
        assert content.startswith(b'%PDF'), f"PDF should start with %PDF, got: {content[:20]}"
        assert len(content) > 1000, f"PDF should be larger than 1KB, got {len(content)} bytes"
        print(f"✓ PDF report returns valid PDF data ({len(content)} bytes)")
    
    def test_pdf_report_has_content_disposition_header(self):
        """Test that PDF report has proper content-disposition header for download"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/{TEST_VALUATION_ID}", timeout=30)
        assert response.status_code == 200
        disposition = response.headers.get('content-disposition', '')
        assert 'attachment' in disposition or 'filename' in disposition, f"Expected content-disposition with filename, got: {disposition}"
        print(f"✓ PDF report has content-disposition header: {disposition}")
    
    def test_pdf_report_returns_404_for_nonexistent_valuation(self):
        """Test that PDF report returns 404 for non-existent valuation"""
        response = requests.get(f"{BASE_URL}/api/report/pdf/nonexistent-id-12345", timeout=30)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ PDF report returns 404 for non-existent valuation")


class TestListingAnalyzerEndpoint:
    """Tests for listing analyzer endpoint"""
    
    def test_listing_analyze_endpoint_exists(self):
        """Test that listing analyze endpoint exists (returns 422 without file)"""
        response = requests.post(f"{BASE_URL}/api/listing/analyze", timeout=30)
        # Without a file, it should return 422 (Unprocessable Entity) not 404
        assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"
        print(f"✓ Listing analyze endpoint exists (returns {response.status_code} without file)")
    
    def test_listing_analyze_rejects_unsupported_file_types(self):
        """Test that listing analyze rejects unsupported file types"""
        # Create a fake text file
        files = {'file': ('test.txt', b'This is a test file', 'text/plain')}
        response = requests.post(f"{BASE_URL}/api/listing/analyze", files=files, timeout=30)
        assert response.status_code == 400, f"Expected 400 for unsupported file type, got {response.status_code}"
        data = response.json()
        assert 'detail' in data, "Response should contain detail field"
        assert 'PDF' in data['detail'] or 'JPG' in data['detail'] or 'PNG' in data['detail'], f"Error should mention supported formats: {data['detail']}"
        print(f"✓ Listing analyze rejects unsupported file types: {data['detail']}")
    
    def test_listing_analyze_rejects_csv_file(self):
        """Test that listing analyze rejects CSV files"""
        files = {'file': ('data.csv', b'col1,col2\nval1,val2', 'text/csv')}
        response = requests.post(f"{BASE_URL}/api/listing/analyze", files=files, timeout=30)
        assert response.status_code == 400, f"Expected 400 for CSV file, got {response.status_code}"
        print(f"✓ Listing analyze rejects CSV files")
    
    def test_listing_analyze_rejects_doc_file(self):
        """Test that listing analyze rejects DOC files"""
        files = {'file': ('document.doc', b'fake doc content', 'application/msword')}
        response = requests.post(f"{BASE_URL}/api/listing/analyze", files=files, timeout=30)
        assert response.status_code == 400, f"Expected 400 for DOC file, got {response.status_code}"
        print(f"✓ Listing analyze rejects DOC files")


class TestExistingValuationEndpoints:
    """Tests for existing valuation endpoints to ensure they still work"""
    
    def test_get_valuation_returns_data(self):
        """Test that GET valuation returns proper data"""
        response = requests.get(f"{BASE_URL}/api/valuation/{TEST_VALUATION_ID}", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'id' in data, "Response should contain id"
        assert 'price_median' in data, "Response should contain price_median"
        assert 'request' in data, "Response should contain request"
        print(f"✓ GET valuation returns proper data with price_median: {data.get('price_median')}")
    
    def test_list_valuations_returns_array(self):
        """Test that list valuations returns an array"""
        response = requests.get(f"{BASE_URL}/api/valuations", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ List valuations returns array with {len(data)} items")


class TestNavigationEndpoints:
    """Tests for navigation-related endpoints"""
    
    def test_algorithm_config_endpoint(self):
        """Test algorithm config endpoint"""
        response = requests.get(f"{BASE_URL}/api/algorithm/config", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'floor_rdc' in data, "Config should contain floor_rdc"
        print(f"✓ Algorithm config endpoint works")
    
    def test_address_search_endpoint(self):
        """Test address search endpoint"""
        response = requests.get(f"{BASE_URL}/api/address/search", params={"q": "Paris"}, timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Address search endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
