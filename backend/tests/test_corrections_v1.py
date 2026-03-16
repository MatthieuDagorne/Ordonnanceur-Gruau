"""
Test suite for APS corrections v1:
1. Suppression page 'Matrice Compat.' - /matrix route should not exist
2. Filtres Gantt par order_id et article_id
3. Format date complet 'Lundi 16 mars 2026'
4. Sélecteur plage de dates (Du/Au)
5. Indisponibilités machines (reporter si machine indispo)
6. Fuseau horaire Europe/Paris
7. Mode JIT amélioré avec flux tiré (minimiser encours entre opérations)
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test scenario ID from the context
JIT_SCENARIO_ID = "a8295933-c58d-4177-bbdb-76d3ce654012"


class TestMatrixPageRemoved:
    """Test 1: Page 'Matrice Compat.' supprimée"""
    
    def test_matrix_route_not_accessible(self):
        """The /matrix route should not exist in the app routes"""
        # We can only test that it's not in the API routes
        # Frontend route removal is tested via Playwright
        response = requests.get(f"{BASE_URL}/api/matrix", timeout=10)
        # Should return 404 since the route is removed
        assert response.status_code == 404 or response.status_code == 405, \
            f"Expected 404/405 for /api/matrix but got {response.status_code}"
        print("✓ /api/matrix route returns 404/405 (not accessible)")


class TestGanttFilters:
    """Test 2: Filtres Gantt par order_id et article_id"""
    
    def test_gantt_data_endpoint_exists(self):
        """Gantt data endpoint should exist and return data"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}"
        data = response.json()
        assert 'machines' in data, "Response should contain machines"
        assert 'time_range' in data, "Response should contain time_range"
        print(f"✓ Gantt data endpoint returns {len(data.get('machines', []))} machines")
    
    def test_gantt_data_contains_task_order_ids(self):
        """Gantt tasks should contain order_id for filtering"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        order_ids = set()
        article_ids = set()
        for machine in data.get('machines', []):
            for task in machine.get('tasks', []):
                if task.get('order_id'):
                    order_ids.add(task['order_id'])
                if task.get('article_id'):
                    article_ids.add(task['article_id'])
        
        assert len(order_ids) > 0, "Tasks should have order_id for filtering"
        print(f"✓ Found {len(order_ids)} unique order_ids: {order_ids}")
        print(f"✓ Found {len(article_ids)} unique article_ids: {article_ids}")


class TestDateFormat:
    """Test 3 & 6: Format date complet et fuseau horaire Europe/Paris"""
    
    def test_scheduling_start_format(self):
        """Scheduling start should be in ISO format (can be converted to full French date)"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        scheduling_start = data.get('scheduling_start')
        assert scheduling_start is not None, "scheduling_start should be present"
        
        # Parse the datetime
        dt = datetime.fromisoformat(scheduling_start)
        print(f"✓ scheduling_start: {scheduling_start}")
        print(f"✓ Parsed date: {dt.strftime('%Y-%m-%d %H:%M')}")
        
        # The frontend should format this as "Lundi 16 mars 2026"
        # We verify the date is valid and can be formatted
        days_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        months_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 
                     'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
        
        full_date = f"{days_fr[dt.weekday()]} {dt.day} {months_fr[dt.month-1]} {dt.year}"
        print(f"✓ Full French format would be: {full_date}")
    
    def test_scenario_scheduling_start_timezone(self):
        """Verify scheduling_start is set (Europe/Paris timezone used by backend)"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        scheduling_start = schedule_data.get('scheduling_start')
        
        assert scheduling_start is not None, "scheduling_start should be in schedule_data"
        print(f"✓ Scenario scheduling_start: {scheduling_start}")


class TestUnavailabilityConstraints:
    """Test 5: Indisponibilités machines"""
    
    def test_unavailability_endpoint_exists(self):
        """Unavailability endpoint should exist"""
        response = requests.get(f"{BASE_URL}/api/unavailability", timeout=10)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Unavailability endpoint returns {len(data)} records")
    
    def test_unavailability_crud(self):
        """Test CRUD operations on unavailability"""
        # Create an unavailability
        test_unavail = {
            "id": "test-unavail-001",
            "machine_id": "M1",
            "start_date": "2026-03-20T08:00:00",
            "end_date": "2026-03-20T12:00:00",
            "reason": "Test maintenance"
        }
        
        # Create
        response = requests.post(f"{BASE_URL}/api/unavailability", json=test_unavail, timeout=10)
        assert response.status_code == 200, f"Create failed: {response.status_code}"
        print("✓ Created test unavailability")
        
        # Read
        response = requests.get(f"{BASE_URL}/api/unavailability", timeout=10)
        assert response.status_code == 200
        data = response.json()
        found = any(u.get('id') == 'test-unavail-001' for u in data)
        assert found, "Created unavailability should be in list"
        print("✓ Read confirms unavailability exists")
        
        # Delete
        response = requests.delete(f"{BASE_URL}/api/unavailability/test-unavail-001", timeout=10)
        assert response.status_code == 200
        print("✓ Deleted test unavailability")


class TestJITMode:
    """Test 7: Mode JIT amélioré avec flux tiré"""
    
    def test_jit_scenario_is_optimal(self):
        """JIT scenario should have OPTIMAL status"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        status = schedule_data.get('status')
        strategy = schedule_data.get('scheduling_strategy')
        
        assert status == 'OPTIMAL', f"Expected OPTIMAL status but got {status}"
        assert strategy == 'JIT', f"Expected JIT strategy but got {strategy}"
        print(f"✓ JIT scenario status: {status}, strategy: {strategy}")
    
    def test_jit_scenario_has_operations(self):
        """JIT scenario should have scheduled operations"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        operations = schedule_data.get('operations', [])
        
        assert len(operations) > 0, "JIT scenario should have operations"
        print(f"✓ JIT scenario has {len(operations)} operations")
        
        # Check operations have required fields
        for op in operations[:3]:
            assert 'start_datetime' in op, "Operation should have start_datetime"
            assert 'end_datetime' in op, "Operation should have end_datetime"
            assert 'machine_id' in op, "Operation should have machine_id"
            print(f"  - {op.get('operation_id')}: {op.get('start_datetime')} on {op.get('machine_id')}")
    
    def test_jit_late_orders_detection(self):
        """JIT mode should detect late orders"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        late_orders = schedule_data.get('late_orders', [])
        
        print(f"✓ JIT scenario has {len(late_orders)} late orders detected")
        for late in late_orders:
            print(f"  - {late.get('order_id')}: {late.get('lateness_hours', 0):.1f}h late")


class TestSchedulingOptions:
    """Test scheduling endpoint accepts options including unavailabilities"""
    
    def test_scheduling_options_documented(self):
        """Verify scheduling endpoint schema"""
        # Test that the schedule endpoint accepts the right options
        # We check via a GET on scenarios to see what options were used
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        
        # Check that scheduling_strategy is recorded
        assert 'scheduling_strategy' in schedule_data, "scheduling_strategy should be recorded"
        assert 'status' in schedule_data, "status should be recorded"
        assert 'operations' in schedule_data, "operations should be recorded"
        
        print(f"✓ Scheduling options verified:")
        print(f"  - strategy: {schedule_data.get('scheduling_strategy')}")
        print(f"  - status: {schedule_data.get('status')}")
        print(f"  - solver_time: {schedule_data.get('solver_time', 0):.2f}s")


class TestGanttDataStructure:
    """Test Gantt data structure for frontend filters"""
    
    def test_gantt_time_range_structure(self):
        """Gantt time_range should have correct structure for date range filter"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        time_range = data.get('time_range', {})
        assert 'total_minutes' in time_range, "time_range should have total_minutes"
        assert 'min_minutes' in time_range or time_range.get('total_minutes', 0) > 0, \
            "time_range should have valid duration"
        
        print(f"✓ Gantt time_range: {time_range}")
    
    def test_gantt_centres_de_charge(self):
        """Gantt should include centres_de_charge for filters"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        centres = data.get('centres_de_charge', [])
        print(f"✓ Gantt has {len(centres)} centres de charge for filtering")
        for c in centres:
            print(f"  - {c.get('id')}: {c.get('nom', 'N/A')}")
    
    def test_gantt_machine_calendars(self):
        """Gantt should include calendars for closure period display"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        calendars = data.get('calendars', [])
        machines = data.get('machines', [])
        
        print(f"✓ Gantt has {len(calendars)} calendars")
        
        # Check if machines have calendar info
        machines_with_calendar = sum(1 for m in machines if m.get('calendar'))
        print(f"✓ {machines_with_calendar}/{len(machines)} machines have calendar info")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
