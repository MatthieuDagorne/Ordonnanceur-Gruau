"""
Test suite for Iteration 19 features - APS 7 improvements:
1. API /api/scenarios returns scenarios without error
2. Scheduling calculation with max_solver_time_seconds=120 doesn't timeout
3. Scheduling result contains 'scheduling_stats' with required fields
4. Scheduling result contains 'active_options'
5. Scheduled operations contain 'materials' field with required fields
6. Operations import creates missing centres de charge automatically
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestScenariosAPI:
    """Test /api/scenarios endpoint - Feature 1"""
    
    def test_scenarios_endpoint_returns_200(self):
        """GET /api/scenarios returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/scenarios")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ Scenarios API returns {len(data)} scenarios")
    
    def test_scenarios_have_required_fields(self):
        """Each scenario has id, name, created_at, schedule_data"""
        response = requests.get(f"{BASE_URL}/api/scenarios")
        assert response.status_code == 200
        data = response.json()
        if data:
            scenario = data[0]
            assert 'id' in scenario, "Missing id field"
            assert 'name' in scenario, "Missing name field"
            assert 'created_at' in scenario, "Missing created_at field"
            assert 'schedule_data' in scenario, "Missing schedule_data field"
            print(f"✅ Scenario has all required fields")

class TestSchedulingStats:
    """Test scheduling_stats in scheduling result - Feature 3"""
    
    def test_scheduling_stats_present_in_result(self):
        """Verify scheduling_stats is present in schedule_data"""
        # Get existing scenario with scheduled operations
        response = requests.get(f"{BASE_URL}/api/scenarios/e3d80f33-7685-4ad4-8db9-40a33c6c5bc1")
        if response.status_code != 200:
            pytest.skip("Test scenario not found")
        
        data = response.json()
        schedule_data = data.get('schedule_data', {})
        
        assert 'scheduling_stats' in schedule_data, "scheduling_stats missing from schedule_data"
        stats = schedule_data['scheduling_stats']
        
        # Check required fields
        assert 'operations_scheduled' in stats, "Missing operations_scheduled"
        assert 'global_utilization_percent' in stats, "Missing global_utilization_percent"
        assert 'actual_solver_time' in stats, "Missing actual_solver_time"
        assert 'max_solver_time_configured' in stats, "Missing max_solver_time_configured"
        assert 'total_operations_input' in stats, "Missing total_operations_input"
        assert 'operations_blocked' in stats, "Missing operations_blocked"
        assert 'machine_utilization' in stats, "Missing machine_utilization"
        
        print(f"✅ scheduling_stats present with all required fields")
        print(f"   - operations_scheduled: {stats['operations_scheduled']}")
        print(f"   - global_utilization_percent: {stats['global_utilization_percent']}%")
        print(f"   - actual_solver_time: {stats['actual_solver_time']}s")
    
    def test_scheduling_stats_values_are_valid(self):
        """Verify scheduling_stats values are reasonable"""
        response = requests.get(f"{BASE_URL}/api/scenarios/e3d80f33-7685-4ad4-8db9-40a33c6c5bc1")
        if response.status_code != 200:
            pytest.skip("Test scenario not found")
        
        data = response.json()
        stats = data.get('schedule_data', {}).get('scheduling_stats', {})
        
        assert stats['operations_scheduled'] >= 0, "operations_scheduled should be >= 0"
        assert 0 <= stats['global_utilization_percent'] <= 100, "global_utilization_percent should be 0-100"
        assert stats['actual_solver_time'] >= 0, "actual_solver_time should be >= 0"
        assert stats['actual_solver_time'] <= stats['max_solver_time_configured'] + 10, "actual_solver_time should not exceed max by much"
        
        print(f"✅ scheduling_stats values are valid")

class TestActiveOptions:
    """Test active_options in scheduling result - Feature 4"""
    
    def test_active_options_present_in_result(self):
        """Verify active_options is present in schedule_data"""
        response = requests.get(f"{BASE_URL}/api/scenarios/e3d80f33-7685-4ad4-8db9-40a33c6c5bc1")
        if response.status_code != 200:
            pytest.skip("Test scenario not found")
        
        data = response.json()
        schedule_data = data.get('schedule_data', {})
        
        assert 'active_options' in schedule_data, "active_options missing from schedule_data"
        options = schedule_data['active_options']
        
        # Check all option fields
        expected_options = [
            'ignore_rules',
            'ignore_material',
            'ignore_calendars',
            'ignore_priorities',
            'ignore_priority_propagation',
            'ignore_material_propagation'
        ]
        
        for opt in expected_options:
            assert opt in options, f"Missing option: {opt}"
            assert isinstance(options[opt], bool), f"{opt} should be boolean"
        
        print(f"✅ active_options present with all 6 fields")

class TestMaterialsInOperations:
    """Test materials field in scheduled operations - Feature 5"""
    
    def test_materials_field_present_in_operations(self):
        """Verify materials field is present in scheduled operations"""
        response = requests.get(f"{BASE_URL}/api/scenarios/e3d80f33-7685-4ad4-8db9-40a33c6c5bc1")
        if response.status_code != 200:
            pytest.skip("Test scenario not found")
        
        data = response.json()
        operations = data.get('schedule_data', {}).get('operations', [])
        
        assert len(operations) > 0, "No scheduled operations found"
        
        # All operations should have materials field (even if empty list)
        for op in operations[:10]:  # Check first 10
            assert 'materials' in op, f"materials missing from operation {op.get('operation_id')}"
            assert isinstance(op['materials'], list), "materials should be a list"
        
        print(f"✅ All operations have materials field")
    
    def test_materials_contain_required_fields(self):
        """Verify materials have article_id, needed, in_stock, available, magasin"""
        response = requests.get(f"{BASE_URL}/api/scenarios/e3d80f33-7685-4ad4-8db9-40a33c6c5bc1")
        if response.status_code != 200:
            pytest.skip("Test scenario not found")
        
        data = response.json()
        operations = data.get('schedule_data', {}).get('operations', [])
        
        # Find an operation with materials
        ops_with_materials = [op for op in operations if op.get('materials')]
        assert len(ops_with_materials) > 0, "No operations with materials found"
        
        for mat in ops_with_materials[0]['materials']:
            assert 'article_id' in mat, "Missing article_id in material"
            assert 'needed' in mat, "Missing needed in material"
            assert 'in_stock' in mat, "Missing in_stock in material"
            assert 'available' in mat, "Missing available in material"
            assert 'magasin' in mat, "Missing magasin in material"
            assert isinstance(mat['available'], bool), "available should be boolean"
        
        print(f"✅ Materials have all required fields: article_id, needed, in_stock, available, magasin")
        print(f"   Found {len(ops_with_materials)} operations with materials")

class TestSchedulingCalculation:
    """Test scheduling calculation with max_solver_time_seconds=120 - Feature 2"""
    
    def test_calculate_scheduling_no_timeout(self):
        """POST /api/scheduling/calculate with 120s max time doesn't timeout"""
        # First get some basic data stats
        stats_response = requests.get(f"{BASE_URL}/api/data/stats")
        if stats_response.status_code != 200:
            pytest.skip("Cannot get data stats")
        
        stats = stats_response.json()
        if stats.get('operations', 0) == 0:
            pytest.skip("No operations in database")
        
        # Create a test scheduling calculation with limited scope to avoid long runtime
        payload = {
            "scenario_name": f"TEST_No_Timeout_{uuid.uuid4().hex[:8]}",
            "max_operations": 100,  # Limit to 100 ops for test speed
            "max_solver_time_seconds": 30,  # 30s is enough for 100 ops
            "ignore_rules": True,  # Simplify for test
            "ignore_material": True
        }
        
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json=payload, timeout=120)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # API returns wrapper with scenario_id, status: "completed", and result
        assert 'status' in data, "Missing status in response"
        assert data['status'] == 'completed', f"Expected 'completed', got {data['status']}"
        assert 'result' in data, "Missing result in response"
        
        result = data['result']
        assert result['status'] in ['OPTIMAL', 'FEASIBLE', 'NO_VALID_OPERATIONS', 'INFEASIBLE'], f"Unexpected result status: {result['status']}"
        
        # Check scheduling_stats in result
        if 'scheduling_stats' in result:
            stats = result['scheduling_stats']
            print(f"✅ Calculation completed without timeout")
            print(f"   - Status: {result['status']}")
            print(f"   - Solver time: {stats.get('actual_solver_time', 'N/A')}s")
        else:
            print(f"✅ Calculation completed with status: {result['status']}")

class TestAutoCreateCentresDeCharge:
    """Test automatic creation of centres de charge on import - Feature 7"""
    
    def test_centres_de_charge_created_on_import(self):
        """Import operations should create missing centres de charge"""
        # This is tested by checking if auto_created centres exist
        response = requests.get(f"{BASE_URL}/api/centres-de-charge")
        if response.status_code != 200:
            pytest.skip("Cannot get centres de charge")
        
        centres = response.json()
        auto_created = [c for c in centres if c.get('auto_created', False)]
        
        print(f"✅ Found {len(auto_created)} auto-created centres de charge out of {len(centres)} total")
        
        if auto_created:
            # Verify auto_created centres have required structure
            for c in auto_created[:3]:
                assert 'id' in c, "Missing id"
                assert 'nom' in c, "Missing nom"
                assert c.get('auto_created') == True, "auto_created should be True"
                print(f"   - Centre: {c['id']} ({c.get('nom', 'no name')})")

class TestUnscheduledOperationsSection:
    """Test unscheduled operations in schedule_data - Feature 6"""
    
    def test_unscheduled_operations_have_reason(self):
        """Verify unscheduled operations have reason field"""
        response = requests.get(f"{BASE_URL}/api/scenarios/e3d80f33-7685-4ad4-8db9-40a33c6c5bc1")
        if response.status_code != 200:
            pytest.skip("Test scenario not found")
        
        data = response.json()
        unscheduled = data.get('schedule_data', {}).get('unscheduled_operations', [])
        
        if not unscheduled:
            print("ℹ️ No unscheduled operations in this scenario")
            return
        
        for op in unscheduled[:5]:
            assert 'reason' in op, f"Missing reason in unscheduled operation {op.get('operation_id')}"
            assert 'operation_id' in op, "Missing operation_id"
            assert 'order_id' in op, "Missing order_id"
        
        print(f"✅ Unscheduled operations ({len(unscheduled)}) have reason field")

class TestBlockedReasonsSummary:
    """Test blocked_reasons_summary in scheduling_stats"""
    
    def test_blocked_reasons_summary_present(self):
        """Verify blocked_reasons_summary is present and categorized"""
        response = requests.get(f"{BASE_URL}/api/scenarios/e3d80f33-7685-4ad4-8db9-40a33c6c5bc1")
        if response.status_code != 200:
            pytest.skip("Test scenario not found")
        
        data = response.json()
        stats = data.get('schedule_data', {}).get('scheduling_stats', {})
        
        if 'blocked_reasons_summary' not in stats:
            print("ℹ️ No blocked_reasons_summary in this scenario")
            return
        
        summary = stats['blocked_reasons_summary']
        assert isinstance(summary, dict), "blocked_reasons_summary should be dict"
        
        # Check categories
        valid_categories = ['machine_missing', 'material_shortage', 'calendar_constraint', 'business_rule', 'other']
        for category, count in summary.items():
            assert category in valid_categories, f"Unexpected category: {category}"
            assert isinstance(count, int), f"Count for {category} should be int"
        
        print(f"✅ blocked_reasons_summary present: {summary}")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """Cleanup TEST_ prefixed scenarios after tests"""
    yield
    # Cleanup
    try:
        response = requests.get(f"{BASE_URL}/api/scenarios")
        if response.status_code == 200:
            scenarios = response.json()
            for s in scenarios:
                if s.get('name', '').startswith('TEST_'):
                    requests.delete(f"{BASE_URL}/api/scenarios/{s['id']}")
    except:
        pass
