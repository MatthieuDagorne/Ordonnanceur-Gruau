"""
Iteration 10 Tests: Calendar HH:MM, Import CSV Stats, Smart Filters
- Calendars: Input time HH:MM avec step 15min (07:45, 16:45)
- Import CSV: 3 sections - ERP, Supply Chain, Configuration with all counters
- API /api/data/stats: Returns all counters including operation_materials, planned_receipts, bom_lines, unavailabilities
- Filters on 4 pages: Business Rules, Manufacturing Orders, Diagnostic, Projected Stock
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDataStatsAPI:
    """Test /api/data/stats endpoint with all counters"""
    
    def test_data_stats_returns_all_counters(self):
        """Verify all counters are returned in the stats response"""
        response = requests.get(f"{BASE_URL}/api/data/stats")
        assert response.status_code == 200
        
        data = response.json()
        
        # ERP counters
        assert 'manufacturing_orders' in data
        assert 'operations' in data
        assert 'articles' in data
        assert 'stocks' in data
        
        # Supply Chain counters
        assert 'operation_materials' in data
        assert 'planned_receipts' in data
        assert 'bom_lines' in data
        assert 'unavailabilities' in data
        
        # Configuration counters
        assert 'machines' in data
        assert 'work_centers' in data
        assert 'calendars' in data
        assert 'rules' in data
        assert 'scenarios' in data
        
        print(f"✓ All stats counters present")
        print(f"  ERP: OF={data['manufacturing_orders']}, ops={data['operations']}, articles={data['articles']}, stocks={data['stocks']}")
        print(f"  Supply Chain: materials={data['operation_materials']}, receipts={data['planned_receipts']}, bom={data['bom_lines']}, unavail={data['unavailabilities']}")
        print(f"  Config: machines={data['machines']}, centers={data['work_centers']}, calendars={data['calendars']}, rules={data['rules']}, scenarios={data['scenarios']}")


class TestCalendarsAPI:
    """Test Calendars API with HH:MM time format"""
    
    def test_calendars_list(self):
        """Verify calendars endpoint returns list with time fields"""
        response = requests.get(f"{BASE_URL}/api/calendars")
        assert response.status_code == 200
        
        calendars = response.json()
        assert isinstance(calendars, list)
        print(f"✓ Calendars endpoint returns {len(calendars)} calendars")
        
    def test_create_calendar_with_quarter_hours(self):
        """Test creating calendar with 15-minute increments (07:45, 16:45)"""
        calendar_data = {
            "name": "TEST_QuarterHour",
            "working_days": [1, 2, 3, 4, 5],
            "start_time": "07:45",
            "end_time": "16:45",
            "start_hour": 7,  # Backward compatibility
            "end_hour": 16
        }
        
        response = requests.post(f"{BASE_URL}/api/calendars", json=calendar_data)
        assert response.status_code == 200
        
        created = response.json()
        assert created['name'] == "TEST_QuarterHour"
        assert created['start_time'] == "07:45"
        assert created['end_time'] == "16:45"
        
        print(f"✓ Calendar created with quarter-hour times: {created['start_time']} - {created['end_time']}")
        
        # Cleanup
        calendar_id = created.get('id')
        if calendar_id:
            requests.delete(f"{BASE_URL}/api/calendars/{calendar_id}")


class TestBusinessRulesAPI:
    """Test Business Rules API for filtering"""
    
    def test_rules_list(self):
        """Verify rules endpoint returns list with filter-relevant fields"""
        response = requests.get(f"{BASE_URL}/api/rules")
        assert response.status_code == 200
        
        rules = response.json()
        assert isinstance(rules, list)
        
        if len(rules) > 0:
            rule = rules[0]
            # Verify fields needed for filtering
            assert 'machine_id' in rule
            assert 'rule_type' in rule
            assert 'active' in rule
            print(f"✓ Rules endpoint returns {len(rules)} rules with filter fields")
        else:
            print("✓ Rules endpoint returns empty list (no rules)")


class TestOperationsEnrichiesAPI:
    """Test Operations Enrichies API for filtering"""
    
    def test_operations_enrichies_list(self):
        """Verify operations-enrichies endpoint returns data with filter-relevant fields"""
        response = requests.get(f"{BASE_URL}/api/operations-enrichies")
        assert response.status_code == 200
        
        operations = response.json()
        assert isinstance(operations, list)
        
        if len(operations) > 0:
            op = operations[0]
            # Verify fields needed for filtering
            assert 'article_id' in op
            assert 'date_besoin' in op
            print(f"✓ Operations enrichies endpoint returns {len(operations)} operations with filter fields")
        else:
            print("✓ Operations enrichies endpoint returns empty list")


class TestDiagnosticAPI:
    """Test Diagnostic Assignment API for filtering"""
    
    def test_diagnostic_assignment(self):
        """Verify diagnostic/assignment endpoint returns data with filter-relevant fields"""
        response = requests.get(f"{BASE_URL}/api/diagnostic/assignment")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify structure
        assert 'summary' in data
        assert 'diagnostics_table' in data
        
        diagnostics = data.get('diagnostics_table', [])
        if len(diagnostics) > 0:
            diag = diagnostics[0]
            # Verify fields needed for filtering
            assert 'operation_id' in diag or 'id' in diag
            print(f"✓ Diagnostic endpoint returns {len(diagnostics)} diagnostics with filter fields")
        else:
            print("✓ Diagnostic endpoint returns empty diagnostics list")


class TestProjectedStockAPI:
    """Test Projected Stock API for filtering"""
    
    def test_projected_stock(self):
        """Verify projected-stock endpoint returns data with filter-relevant fields"""
        response = requests.get(f"{BASE_URL}/api/projected-stock")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify structure
        assert 'summary' in data
        assert 'projected_stock' in data
        
        stocks = data.get('projected_stock', [])
        if len(stocks) > 0:
            stock = stocks[0]
            # Verify fields needed for filtering
            assert 'article_id' in stock
            assert 'has_shortage' in stock
            print(f"✓ Projected stock endpoint returns {len(stocks)} articles with filter fields")
        else:
            print("✓ Projected stock endpoint returns empty list")


class TestMachinesAndCentresAPI:
    """Test Machines and Centres de Charge APIs for filter dropdowns"""
    
    def test_machines_list(self):
        """Verify machines endpoint returns list for filter dropdown"""
        response = requests.get(f"{BASE_URL}/api/machines")
        assert response.status_code == 200
        
        machines = response.json()
        assert isinstance(machines, list)
        print(f"✓ Machines endpoint returns {len(machines)} machines")
        
    def test_centres_de_charge_list(self):
        """Verify centres-de-charge endpoint returns list for filter dropdown"""
        response = requests.get(f"{BASE_URL}/api/centres-de-charge")
        assert response.status_code == 200
        
        centres = response.json()
        assert isinstance(centres, list)
        print(f"✓ Centres de charge endpoint returns {len(centres)} centres")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
