"""
Test P1/P2 Features: Matrix View, Scenarios Comparison, Gantt Interactive, Projected Stock Advanced
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

class TestMatrixAPI:
    """Tests for /api/matrix/machine-task endpoint"""
    
    def test_matrix_machine_task_returns_200(self):
        """Matrix endpoint should return 200 status"""
        response = requests.get(f"{BASE_URL}/api/matrix/machine-task")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Matrix API returns 200")
    
    def test_matrix_has_required_fields(self):
        """Matrix response should contain required fields"""
        response = requests.get(f"{BASE_URL}/api/matrix/machine-task")
        data = response.json()
        
        assert 'machines' in data, "Missing 'machines' field"
        assert 'taches' in data, "Missing 'taches' field"
        assert 'matrix' in data, "Missing 'matrix' field"
        assert 'rules_count' in data, "Missing 'rules_count' field"
        
        assert isinstance(data['machines'], list), "'machines' should be a list"
        assert isinstance(data['taches'], list), "'taches' should be a list"
        assert isinstance(data['matrix'], list), "'matrix' should be a list"
        
        print(f"✓ Matrix has {len(data['machines'])} machines, {len(data['taches'])} taches, {data['rules_count']} rules")
    
    def test_matrix_row_structure(self):
        """Each matrix row should have proper structure"""
        response = requests.get(f"{BASE_URL}/api/matrix/machine-task")
        data = response.json()
        
        if data['matrix']:
            row = data['matrix'][0]
            assert 'machine_id' in row, "Matrix row missing 'machine_id'"
            assert 'centre_id' in row, "Matrix row missing 'centre_id'"
            assert 'compatibilities' in row, "Matrix row missing 'compatibilities'"
            
            # Check compatibility structure
            if data['taches'] and row['compatibilities']:
                first_tache = data['taches'][0]
                compat = row['compatibilities'].get(first_tache, {})
                assert 'status' in compat, "Compatibility missing 'status'"
                
        print("✓ Matrix row structure is correct")


class TestScenariosAPI:
    """Tests for scenarios endpoints"""
    
    def test_scenarios_list_returns_200(self):
        """Scenarios list should return 200"""
        response = requests.get(f"{BASE_URL}/api/scenarios")
        assert response.status_code == 200
        print("✓ Scenarios list returns 200")
    
    def test_scenarios_compare_requires_two_ids(self):
        """Compare endpoint should require at least 2 IDs"""
        response = requests.get(f"{BASE_URL}/api/scenarios/compare?ids=single-id")
        assert response.status_code == 400, "Should return 400 for single ID"
        print("✓ Compare requires at least 2 IDs")
    
    def test_scenarios_compare_with_valid_ids(self):
        """Compare endpoint with valid scenario IDs"""
        # First get existing scenarios
        scenarios_resp = requests.get(f"{BASE_URL}/api/scenarios")
        scenarios = scenarios_resp.json()
        
        if len(scenarios) >= 2:
            ids = f"{scenarios[0]['id']},{scenarios[1]['id']}"
            response = requests.get(f"{BASE_URL}/api/scenarios/compare?ids={ids}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            assert 'scenarios' in data, "Missing 'scenarios' in comparison"
            assert 'best' in data, "Missing 'best' indicators"
            assert 'comparison_count' in data, "Missing 'comparison_count'"
            assert data['comparison_count'] == 2, f"Expected 2 scenarios compared, got {data['comparison_count']}"
            
            # Check metrics structure
            for scenario in data['scenarios']:
                assert 'scenario_id' in scenario
                assert 'scenario_name' in scenario
                assert 'metrics' in scenario
                metrics = scenario['metrics']
                assert 'operations_scheduled' in metrics
                assert 'conflicts' in metrics
                assert 'makespan_hours' in metrics
            
            print(f"✓ Comparison successful for {data['comparison_count']} scenarios")
        else:
            pytest.skip("Not enough scenarios for comparison test")
    
    def test_scenario_delete(self):
        """Test scenario deletion (only test structure, don't actually delete)"""
        # Just verify endpoint exists by checking a non-existent ID
        response = requests.delete(f"{BASE_URL}/api/scenarios/non-existent-id")
        assert response.status_code == 404, "Expected 404 for non-existent scenario"
        print("✓ Delete endpoint returns 404 for non-existent scenario")


class TestGanttAPI:
    """Tests for Gantt data endpoint"""
    
    def test_gantt_data_with_valid_scenario(self):
        """Gantt data endpoint with valid scenario"""
        # Get a valid scenario ID
        scenarios_resp = requests.get(f"{BASE_URL}/api/scenarios")
        scenarios = scenarios_resp.json()
        
        if scenarios:
            scenario_id = scenarios[0]['id']
            response = requests.get(f"{BASE_URL}/api/gantt/data/{scenario_id}")
            assert response.status_code == 200
            
            data = response.json()
            assert 'scenario_id' in data, "Missing 'scenario_id'"
            assert 'scenario_name' in data, "Missing 'scenario_name'"
            assert 'machines' in data, "Missing 'machines'"
            assert 'time_range' in data, "Missing 'time_range'"
            assert 'total_tasks' in data, "Missing 'total_tasks'"
            
            # Check time_range structure
            time_range = data['time_range']
            assert 'min_minutes' in time_range
            assert 'max_minutes' in time_range
            assert 'total_minutes' in time_range
            
            # Check machines structure
            if data['machines']:
                machine = data['machines'][0]
                assert 'machine_id' in machine
                assert 'tasks' in machine
                assert 'color' in machine
            
            print(f"✓ Gantt data: {data['total_tasks']} tasks, {len(data['machines'])} machines")
        else:
            pytest.skip("No scenarios available for Gantt test")
    
    def test_gantt_data_invalid_scenario(self):
        """Gantt data with invalid scenario ID"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/invalid-id")
        # Should return 404 or empty data
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print("✓ Gantt handles invalid scenario ID")


class TestProjectedStockAdvancedAPI:
    """Tests for /api/projected-stock/advanced endpoint"""
    
    def test_projected_stock_advanced_returns_200(self):
        """Projected stock advanced endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/advanced")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Projected stock advanced returns 200")
    
    def test_projected_stock_advanced_structure(self):
        """Projected stock advanced response structure"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/advanced")
        data = response.json()
        
        assert 'projected_stock' in data, "Missing 'projected_stock'"
        assert 'consumption_details' in data, "Missing 'consumption_details'"
        assert 'summary' in data, "Missing 'summary'"
        
        # Check summary structure
        summary = data['summary']
        assert 'total_articles' in summary
        assert 'articles_with_shortage' in summary
        assert 'articles_ok' in summary
        
        # Check projected_stock item structure
        if data['projected_stock']:
            item = data['projected_stock'][0]
            assert 'article_id' in item
            assert 'initial_stock' in item
            assert 'total_consumption' in item
            assert 'final_stock' in item
            assert 'has_shortage' in item
        
        print(f"✓ Projected stock: {summary['total_articles']} articles, {summary['articles_with_shortage']} shortages")


class TestNavigationIntegration:
    """Test that navigation endpoints exist"""
    
    def test_main_endpoints_accessible(self):
        """Verify main endpoints are accessible"""
        endpoints = [
            "/api/scenarios",
            "/api/machines",
            "/api/matrix/machine-task",
            "/api/projected-stock",
            "/api/projected-stock/advanced",
            "/api/data/stats"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"{endpoint} returned {response.status_code}"
        
        print(f"✓ All {len(endpoints)} main endpoints accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
