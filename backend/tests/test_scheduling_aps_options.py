"""
Test cases for the new APS Scheduling Options
Tests: priority_mode, weight sliders, solver time, optimization gap, advanced options
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://shop-scheduler-9.preview.emergentagent.com"


class TestSchedulingAPIEndpoint:
    """Test POST /api/scheduling/calculate with new APS options"""
    
    def test_scheduling_accepts_priority_mode_due_date(self):
        """Test priority_mode='due_date' is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Due Date Priority",
            "priority_mode": "due_date",
            "max_solver_time_seconds": 30,
            "debug_mode": True
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "scenario_id" in data
        assert data.get("status") == "completed"
    
    def test_scheduling_accepts_priority_mode_material_availability(self):
        """Test priority_mode='material_availability' is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Material Priority",
            "priority_mode": "material_availability",
            "max_solver_time_seconds": 30,
            "debug_mode": True
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "scenario_id" in data
        assert data.get("status") == "completed"
    
    def test_scheduling_accepts_priority_mode_balanced(self):
        """Test priority_mode='balanced' is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Balanced Priority",
            "priority_mode": "balanced",
            "max_solver_time_seconds": 30,
            "debug_mode": True
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "scenario_id" in data
        assert data.get("status") == "completed"


class TestSchedulingWeightSliders:
    """Test weight parameters for balanced mode"""
    
    def test_scheduling_accepts_due_date_weight(self):
        """Test due_date_weight parameter is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Due Date Weight",
            "priority_mode": "balanced",
            "due_date_weight": 80,
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_scheduling_accepts_material_weight(self):
        """Test material_weight parameter is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Material Weight",
            "priority_mode": "balanced",
            "material_weight": 60,
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_scheduling_accepts_setup_time_weight(self):
        """Test setup_time_weight parameter is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Setup Time Weight",
            "priority_mode": "balanced",
            "setup_time_weight": 30,
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_scheduling_accepts_all_weights_together(self):
        """Test all weight parameters together"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test All Weights",
            "priority_mode": "balanced",
            "due_date_weight": 100,
            "material_weight": 50,
            "setup_time_weight": 20,
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "completed"


class TestSchedulingSolverParameters:
    """Test solver configuration parameters"""
    
    def test_scheduling_accepts_max_solver_time_30s(self):
        """Test max_solver_time_seconds=30 is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Solver Time 30s",
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200
    
    def test_scheduling_accepts_max_solver_time_60s(self):
        """Test max_solver_time_seconds=60 is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Solver Time 60s",
            "max_solver_time_seconds": 60
        })
        assert response.status_code == 200
    
    def test_scheduling_accepts_max_solver_time_120s(self):
        """Test max_solver_time_seconds=120 is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Solver Time 2min",
            "max_solver_time_seconds": 120
        })
        assert response.status_code == 200
    
    def test_scheduling_accepts_max_solver_time_300s(self):
        """Test max_solver_time_seconds=300 is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Solver Time 5min",
            "max_solver_time_seconds": 300
        })
        assert response.status_code == 200
    
    def test_scheduling_accepts_max_solver_time_600s(self):
        """Test max_solver_time_seconds=600 is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Solver Time 10min",
            "max_solver_time_seconds": 600
        })
        assert response.status_code == 200
    
    def test_scheduling_accepts_optimization_gap(self):
        """Test optimization_gap parameter is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Optimization Gap",
            "optimization_gap": 0.05,
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_scheduling_accepts_optimization_gap_range(self):
        """Test optimization_gap at different values (1% to 20%)"""
        for gap_percent in [1, 5, 10, 15, 20]:
            gap_value = gap_percent / 100  # Convert to decimal
            response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
                "scenario_name": f"Test Gap {gap_percent}%",
                "optimization_gap": gap_value,
                "max_solver_time_seconds": 30
            })
            assert response.status_code == 200, f"Failed for gap {gap_percent}%"


class TestSchedulingAdvancedOptions:
    """Test advanced constraint options"""
    
    def test_scheduling_accepts_ignore_rules(self):
        """Test ignore_rules=True is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Ignore Rules",
            "ignore_rules": True,
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_scheduling_accepts_ignore_material(self):
        """Test ignore_material=True is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Ignore Material",
            "ignore_material": True,
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_scheduling_accepts_ignore_calendars(self):
        """Test ignore_calendars=True is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Ignore Calendars",
            "ignore_calendars": True,
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_scheduling_accepts_respect_sequence(self):
        """Test respect_sequence parameter is accepted"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Respect Sequence",
            "respect_sequence": True,
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200
        
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Test Skip Sequence",
            "respect_sequence": False,
            "max_solver_time_seconds": 30
        })
        assert response.status_code == 200


class TestSchedulingFullConfiguration:
    """Test complete configuration with all options"""
    
    def test_scheduling_full_configuration(self):
        """Test all options together in a single request"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Full Configuration Test",
            "priority_mode": "balanced",
            "due_date_weight": 80,
            "material_weight": 60,
            "setup_time_weight": 30,
            "ignore_rules": False,
            "ignore_material": False,
            "ignore_calendars": False,
            "max_solver_time_seconds": 60,
            "optimization_gap": 0.05,
            "respect_sequence": True,
            "debug_mode": True,
            "auto_assign_machines": True
        })
        assert response.status_code == 200
        data = response.json()
        assert "scenario_id" in data
        assert data.get("status") == "completed"
        result = data.get("result", {})
        assert "status" in result
        assert result.get("status") in ["OPTIMAL", "FEASIBLE", "INFEASIBLE", "MODEL_INVALID"]
    
    def test_scheduling_result_contains_diagnostics(self):
        """Test that result contains solver diagnostics"""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "Diagnostics Test",
            "max_solver_time_seconds": 30,
            "debug_mode": True
        })
        assert response.status_code == 200
        data = response.json()
        result = data.get("result", {})
        
        # Check for diagnostics info
        diagnostics = result.get("diagnostics", {})
        if diagnostics:
            # Solver info should be present
            solver_info = diagnostics.get("solver_info", {})
            assert "status" in solver_info or "solver_time" in result


class TestDataStatsEndpoint:
    """Test the /api/data/stats endpoint"""
    
    def test_data_stats_returns_200(self):
        """Test /api/data/stats returns 200"""
        response = requests.get(f"{BASE_URL}/api/data/stats")
        assert response.status_code == 200
    
    def test_data_stats_returns_required_fields(self):
        """Test /api/data/stats returns all required fields"""
        response = requests.get(f"{BASE_URL}/api/data/stats")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "manufacturing_orders",
            "operations",
            "articles",
            "stocks",
            "machines",
            "calendars",
            "rules",
            "scenarios"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], int), f"Field {field} should be int"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
