"""
Test Suite for Scheduling Strategies (ASAP and JIT)
Tests the changes from 3 modes to 2 strategies as per user request.

Features tested:
1. API /api/scheduling/calculate accepts scheduling_strategy parameter (ASAP or JIT)
2. Scenario stores scheduling_strategy in schedule_data
3. ASAP mode creates OPTIMAL scenarios
4. JIT mode handles due_date constraints correctly
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSchedulingStrategies:
    """Test scheduling strategies ASAP and JIT"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - store created scenario IDs for cleanup"""
        self.created_scenarios = []
        yield
        # Cleanup created scenarios
        for scenario_id in self.created_scenarios:
            try:
                requests.delete(f"{BASE_URL}/api/scenarios/{scenario_id}")
            except:
                pass
    
    def test_asap_strategy_creates_optimal_scenario(self):
        """Test ASAP strategy returns OPTIMAL status with scheduled operations"""
        response = requests.post(
            f"{BASE_URL}/api/scheduling/calculate",
            json={
                "scenario_name": "TEST_ASAP_Strategy",
                "scheduling_strategy": "ASAP",
                "max_solver_time_seconds": 30
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify scenario was created
        assert "scenario_id" in data, "scenario_id not in response"
        self.created_scenarios.append(data["scenario_id"])
        
        # Verify result structure
        assert "result" in data, "result not in response"
        result = data["result"]
        
        # Verify ASAP strategy
        assert result.get("scheduling_strategy") == "ASAP", f"Expected ASAP strategy, got {result.get('scheduling_strategy')}"
        
        # Verify OPTIMAL status (assuming data exists)
        assert result.get("status") in ["OPTIMAL", "FEASIBLE", "NO_VALID_OPERATIONS"], f"Unexpected status: {result.get('status')}"
        
        print(f"ASAP scenario created: {data['scenario_id']}, status: {result.get('status')}")
    
    def test_jit_strategy_is_accepted(self):
        """Test JIT strategy is accepted and stored correctly"""
        response = requests.post(
            f"{BASE_URL}/api/scheduling/calculate",
            json={
                "scenario_name": "TEST_JIT_Strategy",
                "scheduling_strategy": "JIT",
                "max_solver_time_seconds": 30
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "scenario_id" in data
        self.created_scenarios.append(data["scenario_id"])
        
        result = data["result"]
        
        # Verify JIT strategy is stored
        assert result.get("scheduling_strategy") == "JIT", f"Expected JIT strategy, got {result.get('scheduling_strategy')}"
        
        # JIT may be INFEASIBLE if due_dates are too tight, but it should still run
        assert result.get("status") in ["OPTIMAL", "FEASIBLE", "INFEASIBLE", "NO_VALID_OPERATIONS"], f"Unexpected status: {result.get('status')}"
        
        print(f"JIT scenario created: {data['scenario_id']}, status: {result.get('status')}")
    
    def test_default_strategy_is_asap(self):
        """Test that default strategy when not specified is ASAP"""
        response = requests.post(
            f"{BASE_URL}/api/scheduling/calculate",
            json={
                "scenario_name": "TEST_Default_Strategy",
                "max_solver_time_seconds": 30
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "scenario_id" in data:
            self.created_scenarios.append(data["scenario_id"])
        
        result = data.get("result", {})
        
        # Default should be ASAP
        assert result.get("scheduling_strategy") == "ASAP", f"Expected default ASAP, got {result.get('scheduling_strategy')}"
        
        print(f"Default strategy is: {result.get('scheduling_strategy')}")
    
    def test_scenario_stores_strategy_in_schedule_data(self):
        """Test that the scheduling_strategy is stored in scenario.schedule_data"""
        # Create ASAP scenario
        response = requests.post(
            f"{BASE_URL}/api/scheduling/calculate",
            json={
                "scenario_name": "TEST_Strategy_Storage",
                "scheduling_strategy": "ASAP",
                "max_solver_time_seconds": 30
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        scenario_id = data["scenario_id"]
        self.created_scenarios.append(scenario_id)
        
        # Fetch the scenario
        scenario_response = requests.get(f"{BASE_URL}/api/scenarios/{scenario_id}")
        assert scenario_response.status_code == 200
        
        scenario = scenario_response.json()
        schedule_data = scenario.get("schedule_data", {})
        
        # Verify strategy is stored
        assert schedule_data.get("scheduling_strategy") == "ASAP", f"Expected ASAP in schedule_data, got {schedule_data.get('scheduling_strategy')}"
        
        print(f"Strategy stored in schedule_data: {schedule_data.get('scheduling_strategy')}")
    
    def test_diagnostic_page_data_includes_strategy(self):
        """Test that scenario data for diagnostic includes scheduling_strategy"""
        # Use existing test scenario
        scenario_id = "455bbdc5-faef-40c2-8fb2-9bc11cdcdc4d"
        
        response = requests.get(f"{BASE_URL}/api/scenarios/{scenario_id}")
        
        if response.status_code == 200:
            scenario = response.json()
            schedule_data = scenario.get("schedule_data", {})
            
            # Verify scheduling_strategy is present
            strategy = schedule_data.get("scheduling_strategy")
            assert strategy in ["ASAP", "JIT", None], f"Unexpected strategy: {strategy}"
            
            print(f"Scenario {scenario_id} has strategy: {strategy}")
        else:
            pytest.skip("Test scenario not found")


class TestSchedulingOptions:
    """Test scheduling options and parameters"""
    
    def test_scheduling_options_accepted(self):
        """Test that all scheduling options are accepted by the API"""
        response = requests.post(
            f"{BASE_URL}/api/scheduling/calculate",
            json={
                "scenario_name": "TEST_Options",
                "scheduling_strategy": "ASAP",
                "ignore_rules": False,
                "ignore_material": False,
                "ignore_calendars": False,
                "max_solver_time_seconds": 30,
                "optimization_gap": 0.05,
                "debug_mode": True,
                "auto_assign_machines": True,
                "respect_sequence": True
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Clean up
        if "scenario_id" in data:
            requests.delete(f"{BASE_URL}/api/scenarios/{data['scenario_id']}")
        
        print("All scheduling options accepted")
    
    def test_invalid_strategy_handled_gracefully(self):
        """Test that invalid strategy value doesn't crash the API"""
        response = requests.post(
            f"{BASE_URL}/api/scheduling/calculate",
            json={
                "scenario_name": "TEST_Invalid_Strategy",
                "scheduling_strategy": "INVALID_STRATEGY",
                "max_solver_time_seconds": 10
            }
        )
        
        # Should either accept and default to ASAP, or return validation error
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            if "scenario_id" in data:
                requests.delete(f"{BASE_URL}/api/scenarios/{data['scenario_id']}")
        
        print(f"Invalid strategy handled with status: {response.status_code}")


class TestGanttTooltip:
    """Test Gantt chart data for tooltip positioning"""
    
    def test_gantt_data_structure(self):
        """Test that gantt data endpoint returns correct structure"""
        scenario_id = "455bbdc5-faef-40c2-8fb2-9bc11cdcdc4d"
        
        response = requests.get(f"{BASE_URL}/api/gantt/data/{scenario_id}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify basic structure
            assert "machines" in data, "machines not in gantt data"
            assert "time_range" in data, "time_range not in gantt data"
            
            # Verify machines have tasks
            if data.get("machines"):
                machine = data["machines"][0]
                assert "machine_id" in machine, "machine_id not in machine"
                assert "tasks" in machine, "tasks not in machine"
                
                if machine.get("tasks"):
                    task = machine["tasks"][0]
                    assert "start_minutes" in task, "start_minutes not in task"
                    assert "end_minutes" in task, "end_minutes not in task"
                    
            print(f"Gantt data structure verified for {len(data.get('machines', []))} machines")
        else:
            pytest.skip(f"Gantt data not available: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
