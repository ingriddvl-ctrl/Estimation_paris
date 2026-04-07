#!/usr/bin/env python3
"""
Backend API Testing for Paris Apartment Valuation App
Tests all endpoints with real data to verify functionality
"""

import requests
import json
import sys
from datetime import datetime

class ValuationAPITester:
    def __init__(self, base_url="https://paris-appart-value.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def test_address_search(self):
        """Test BAN address search API"""
        try:
            response = requests.get(f"{self.api_url}/address/search", 
                                  params={"q": "rue de rivoli paris"}, 
                                  timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Check first result has required fields
                    first = data[0]
                    required_fields = ["label", "postal_code", "latitude", "longitude"]
                    if all(field in first for field in required_fields):
                        self.log_test("Address Search API", True, f"Found {len(data)} addresses")
                        return True
                    else:
                        self.log_test("Address Search API", False, "Missing required fields in response")
                else:
                    self.log_test("Address Search API", False, "Empty or invalid response format")
            else:
                self.log_test("Address Search API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Address Search API", False, str(e))
        return False

    def test_dvf_search(self):
        """Test DVF property data search"""
        try:
            # Test with coordinates near Louvre
            response = requests.get(f"{self.api_url}/dvf/search", 
                                  params={"lat": 48.856, "lon": 2.352, "radius": 500}, 
                                  timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("DVF Search API", True, f"Found {len(data)} transactions")
                    return True
                else:
                    self.log_test("DVF Search API", False, "Invalid response format")
            else:
                self.log_test("DVF Search API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("DVF Search API", False, str(e))
        return False

    def test_geo_risks(self):
        """Test Georisques API"""
        try:
            response = requests.get(f"{self.api_url}/geo/risks", 
                                  params={"lat": 48.856, "lon": 2.352}, 
                                  timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Geo Risks API", True, f"Found {len(data)} risks")
                    return True
                else:
                    self.log_test("Geo Risks API", False, "Invalid response format")
            else:
                self.log_test("Geo Risks API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Geo Risks API", False, str(e))
        return False

    def test_algorithm_config(self):
        """Test algorithm configuration endpoints"""
        try:
            # Test GET config
            response = requests.get(f"{self.api_url}/algorithm/config", timeout=10)
            
            if response.status_code == 200:
                config = response.json()
                required_fields = ["floor_rdc", "balcony_pct", "dpe_ab", "parking_central"]
                if all(field in config for field in required_fields):
                    self.log_test("Algorithm Config GET", True, "All config fields present")
                    
                    # Test PUT config (update)
                    test_config = config.copy()
                    test_config["floor_rdc"] = -10.0  # Slight modification
                    
                    put_response = requests.put(f"{self.api_url}/algorithm/config", 
                                              json=test_config, timeout=10)
                    
                    if put_response.status_code == 200:
                        self.log_test("Algorithm Config PUT", True, "Config updated successfully")
                        return True
                    else:
                        self.log_test("Algorithm Config PUT", False, f"HTTP {put_response.status_code}")
                else:
                    self.log_test("Algorithm Config GET", False, "Missing required config fields")
            else:
                self.log_test("Algorithm Config GET", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Algorithm Config", False, str(e))
        return False

    def test_valuation_estimate(self):
        """Test valuation estimation with sample data"""
        try:
            # Sample valuation request
            sample_request = {
                "location": {
                    "address": "12 rue de Rivoli, 75004 Paris",
                    "street_number": "12",
                    "street_name": "rue de Rivoli",
                    "postal_code": "75004",
                    "city": "Paris",
                    "arrondissement": "04",
                    "floor": 3,
                    "position": "sur_rue",
                    "latitude": 48.856,
                    "longitude": 2.352,
                    "iris_code": ""
                },
                "characteristics": {
                    "surface_carrez": 65.0,
                    "surface_habitable": 65.0,
                    "rooms": 3,
                    "bedrooms": 2,
                    "bathrooms": 1,
                    "property_type": "appartement",
                    "exposure": "sud",
                    "luminosity": "bon",
                    "view": "degagee",
                    "exterior_type": "balcon",
                    "exterior_surface": 5.0,
                    "ceiling_height": "2.80-3.20",
                    "parking": "aucun",
                    "cave": False,
                    "cave_surface": 0.0,
                    "annexes": []
                },
                "condition": {
                    "general_state": "bon_etat",
                    "renovation_year": None,
                    "kitchen_quality": "equipee_basique",
                    "bathroom_quality": "standard",
                    "flooring": "parquet_massif",
                    "windows": "double_vitrage",
                    "insulation": "partielle",
                    "heating": "individuel_gaz",
                    "dpe": "C",
                    "ges": "C",
                    "asbestos": False,
                    "lead": False,
                    "electrical_compliance": True
                },
                "building": {
                    "construction_era": "haussmannien",
                    "building_type": "pierre_taille",
                    "total_floors": 6,
                    "total_lots": 20,
                    "elevator": True,
                    "concierge": False,
                    "security": "digicode",
                    "common_areas_state": "bon",
                    "facade_state": "correct",
                    "roof_state": "correct",
                    "annual_charges": 2400.0,
                    "ongoing_procedures": "aucune",
                    "syndic_type": "professionnel"
                },
                "legal": {
                    "ownership_type": "pleine_propriete",
                    "property_tax": 800.0,
                    "current_rent": 0.0,
                    "remaining_lease_months": 0,
                    "carrez_certified": True,
                    "servitudes": "",
                    "plu_zone": ""
                }
            }

            response = requests.post(f"{self.api_url}/valuation/estimate", 
                                   json=sample_request, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                required_fields = ["id", "price_median", "confidence_score", "adjustments", "comparables"]
                if all(field in result for field in required_fields):
                    price = result.get("price_median", 0)
                    confidence = result.get("confidence_score", 0)
                    comparables_count = len(result.get("comparables", []))
                    
                    self.log_test("Valuation Estimate", True, 
                                f"Price: €{price:,.0f}, Confidence: {confidence}%, Comparables: {comparables_count}")
                    return result
                else:
                    self.log_test("Valuation Estimate", False, "Missing required fields in response")
            else:
                self.log_test("Valuation Estimate", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Valuation Estimate", False, str(e))
        return None

    def test_valuation_crud(self, valuation_result):
        """Test valuation save/get/delete operations"""
        if not valuation_result:
            self.log_test("Valuation CRUD", False, "No valuation result to test with")
            return False

        try:
            # Test save
            save_response = requests.post(f"{self.api_url}/valuation/save", 
                                        json=valuation_result, timeout=10)
            
            if save_response.status_code == 200:
                self.log_test("Valuation Save", True, "Valuation saved successfully")
                
                val_id = valuation_result["id"]
                
                # Test get by ID
                get_response = requests.get(f"{self.api_url}/valuation/{val_id}", timeout=10)
                
                if get_response.status_code == 200:
                    self.log_test("Valuation Get", True, "Retrieved valuation by ID")
                    
                    # Test list all
                    list_response = requests.get(f"{self.api_url}/valuations", timeout=10)
                    
                    if list_response.status_code == 200:
                        valuations = list_response.json()
                        self.log_test("Valuation List", True, f"Found {len(valuations)} valuations")
                        
                        # Test delete
                        delete_response = requests.delete(f"{self.api_url}/valuation/{val_id}", timeout=10)
                        
                        if delete_response.status_code == 200:
                            self.log_test("Valuation Delete", True, "Valuation deleted successfully")
                            return True
                        else:
                            self.log_test("Valuation Delete", False, f"HTTP {delete_response.status_code}")
                    else:
                        self.log_test("Valuation List", False, f"HTTP {list_response.status_code}")
                else:
                    self.log_test("Valuation Get", False, f"HTTP {get_response.status_code}")
            else:
                self.log_test("Valuation Save", False, f"HTTP {save_response.status_code}")
        except Exception as e:
            self.log_test("Valuation CRUD", False, str(e))
        return False

    def test_simulation_calculate(self):
        """Test purchase cost simulation"""
        try:
            simulation_request = {
                "property_price": 650000.0,
                "notary_rate": 7.5,
                "broker_fee": 0.0,
                "broker_pct": 3.0,
                "loan_amount": 520000.0,
                "interest_rate": 3.5,
                "loan_duration_years": 25,
                "insurance_rate": 0.34,
                "down_payment": 130000.0,
                "renovation_budget": 15000.0
            }

            response = requests.post(f"{self.api_url}/simulation/calculate", 
                                   json=simulation_request, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                required_fields = ["total_monthly", "total_cost", "cost_breakdown"]
                if all(field in result for field in required_fields):
                    monthly = result.get("total_monthly", 0)
                    total = result.get("total_cost", 0)
                    self.log_test("Simulation Calculate", True, 
                                f"Monthly: €{monthly:,.0f}, Total: €{total:,.0f}")
                    return True
                else:
                    self.log_test("Simulation Calculate", False, "Missing required fields")
            else:
                self.log_test("Simulation Calculate", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Simulation Calculate", False, str(e))
        return False

    def test_shared_valuation(self, valuation_result):
        """Test shared valuation access"""
        if not valuation_result:
            self.log_test("Shared Valuation", False, "No valuation result to test with")
            return False

        try:
            share_id = valuation_result.get("share_id")
            if not share_id:
                self.log_test("Shared Valuation", False, "No share_id in valuation result")
                return False

            # First save the valuation
            requests.post(f"{self.api_url}/valuation/save", json=valuation_result, timeout=10)
            
            # Test shared access
            response = requests.get(f"{self.api_url}/share/{share_id}", timeout=10)
            
            if response.status_code == 200:
                shared_data = response.json()
                if "price_median" in shared_data:
                    self.log_test("Shared Valuation", True, f"Shared access works with ID: {share_id}")
                    return True
                else:
                    self.log_test("Shared Valuation", False, "Invalid shared data format")
            else:
                self.log_test("Shared Valuation", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Shared Valuation", False, str(e))
        return False

    def test_market_listings(self):
        """Test market listings API"""
        try:
            response = requests.get(f"{self.api_url}/market/listings", 
                                  params={"lat": 48.856, "lon": 2.352, "radius": 800}, 
                                  timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Market Listings API", True, f"Found {len(data)} market listings")
                    return True
                else:
                    self.log_test("Market Listings API", False, "Invalid response format")
            else:
                self.log_test("Market Listings API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Market Listings API", False, str(e))
        return False

    def test_document_upload(self):
        """Test document upload functionality"""
        try:
            # Create a simple test file
            test_content = b"Test document content for valuation"
            files = {'file': ('test_document.txt', test_content, 'text/plain')}
            
            # Test upload
            response = requests.post(f"{self.api_url}/documents/upload", 
                                   files=files,
                                   params={"valuation_id": "test-123", "category": "autre"},
                                   timeout=30)
            
            if response.status_code == 200:
                doc_data = response.json()
                if "id" in doc_data and "storage_path" in doc_data:
                    doc_id = doc_data["id"]
                    self.log_test("Document Upload", True, f"Document uploaded with ID: {doc_id}")
                    
                    # Test list documents
                    list_response = requests.get(f"{self.api_url}/documents/test-123", timeout=10)
                    if list_response.status_code == 200:
                        docs = list_response.json()
                        self.log_test("Document List", True, f"Found {len(docs)} documents")
                        
                        # Test download
                        download_response = requests.get(f"{self.api_url}/documents/download/{doc_id}", timeout=10)
                        if download_response.status_code == 200:
                            self.log_test("Document Download", True, "Document downloaded successfully")
                            
                            # Test delete
                            delete_response = requests.delete(f"{self.api_url}/documents/{doc_id}", timeout=10)
                            if delete_response.status_code == 200:
                                self.log_test("Document Delete", True, "Document deleted successfully")
                                return True
                            else:
                                self.log_test("Document Delete", False, f"HTTP {delete_response.status_code}")
                        else:
                            self.log_test("Document Download", False, f"HTTP {download_response.status_code}")
                    else:
                        self.log_test("Document List", False, f"HTTP {list_response.status_code}")
                else:
                    self.log_test("Document Upload", False, "Missing required fields in response")
            else:
                self.log_test("Document Upload", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Document Upload", False, str(e))
        return False

    def test_market_position_in_valuation(self, valuation_result):
        """Test that valuation includes market position data"""
        if not valuation_result:
            self.log_test("Market Position in Valuation", False, "No valuation result to test")
            return False
        
        try:
            market_data = valuation_result.get("market_data", {})
            market_position = market_data.get("market_position")
            
            if market_position:
                required_fields = ["label", "description", "diff_pct", "arr_avg", "estimated_sqm"]
                if all(field in market_position for field in required_fields):
                    label = market_position["label"]
                    diff_pct = market_position["diff_pct"]
                    self.log_test("Market Position in Valuation", True, 
                                f"Position: {label} ({diff_pct:+.1f}% vs arr.)")
                    return True
                else:
                    self.log_test("Market Position in Valuation", False, "Missing required market position fields")
            else:
                self.log_test("Market Position in Valuation", False, "No market_position in market_data")
        except Exception as e:
            self.log_test("Market Position in Valuation", False, str(e))
        return False

    def run_all_tests(self):
        """Run comprehensive backend API tests"""
        print("🏠 Testing Paris Apartment Valuation Backend APIs")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)

        # Test external API proxies
        self.test_address_search()
        self.test_dvf_search()
        self.test_geo_risks()

        # Test algorithm configuration
        self.test_algorithm_config()

        # Test core valuation functionality
        valuation_result = self.test_valuation_estimate()
        self.test_valuation_crud(valuation_result)
        self.test_shared_valuation(valuation_result)

        # Test simulation
        self.test_simulation_calculate()

        # Test new features
        self.test_market_listings()
        self.test_document_upload()
        self.test_market_position_in_valuation(valuation_result)

        # Print summary
        print("=" * 60)
        print(f"📊 Tests completed: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed! Backend is fully functional.")
            return 0
        else:
            print("⚠️  Some tests failed. Check the details above.")
            return 1

def main():
    tester = ValuationAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())