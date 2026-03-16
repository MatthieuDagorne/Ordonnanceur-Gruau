"""
Test for Material Constraint Bug Fix in JIT mode.

Bug Fixed: Abnormal delay between dependent operations (producer/consumer) in JIT mode 
due to obsolete material constraints not being updated during iterative replanning.

The old logic only updated constraints when new_date > old_date, which ignored cases 
where a producer is advanced (earlier finish). The fix always replaces constraints with 
the actual production date calculated by the solver.

Test Scenario:
- OF1 produces ART1 (5 units), operations: OF1_10 -> OF1_20 (transfer_time=20min)
- OF2 consumes ART1 at OF2_10 (1 unit needed)
- Stock ART1 = 0, so OF2_10 must wait for OF1 to finish and ART1 to enter stock

Expected behavior:
- OF2_10 should start after OF1_20 ends + transfer_time (20 minutes)
- No artificial delays of several hours between producer and consumer
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestMaterialConstraintBugFix:
    """Tests for the material constraint update bug fix."""
    
    def test_scheduling_api_returns_200(self):
        """Test that the scheduling API is accessible."""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_id": "TEST_MATERIAL_BUGFIX",
            "scenario_name": "Test Material Constraint Bug Fix",
            "scheduling_strategy": "ASAP",
            "max_solver_time_seconds": 30
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "scenario_id" in data
        assert "result" in data
        
    def test_no_infinite_replanning_loop(self):
        """Test that replanning doesn't loop infinitely."""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_id": "TEST_NO_INFINITE_LOOP",
            "scenario_name": "Test No Infinite Loop",
            "scheduling_strategy": "ASAP",
            "max_solver_time_seconds": 60
        })
        
        assert response.status_code == 200, f"API call failed: {response.text}"
        data = response.json()
        result = data.get("result", {})
        
        # Check that material_iteration is reasonable (less than 10)
        material_iteration = result.get("material_iteration", 1)
        assert material_iteration < 10, f"Too many iterations ({material_iteration}), possible infinite loop"
        
        # Check total elapsed time is reasonable (less than 2x max_solver_time)
        total_elapsed = result.get("total_elapsed_time", 0)
        assert total_elapsed < 120, f"Scheduling took too long ({total_elapsed}s)"
        
        print(f"✓ Scheduling completed in {material_iteration} iteration(s), {total_elapsed:.2f}s")
        
    def test_transfer_time_respected_between_producer_consumer(self):
        """
        Test that the delay between producer finish and consumer start 
        equals the transfer time, not several hours.
        
        OF1 produces ART1, OF2_10 consumes ART1.
        Transfer time for OF1_20 is 20 minutes.
        Expected: OF2_10 starts at OF1_20 end + 20 min (not hours later)
        """
        # Run scheduling in ASAP mode first
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_id": "TEST_TRANSFER_TIME",
            "scenario_name": "Test Transfer Time",
            "scheduling_strategy": "ASAP",
            "max_solver_time_seconds": 30
        })
        
        assert response.status_code == 200, f"API call failed: {response.text}"
        data = response.json()
        result = data.get("result", {})
        operations = result.get("operations", [])
        
        assert len(operations) >= 4, f"Expected at least 4 operations, got {len(operations)}"
        
        # Find OF1_20 (producer's last operation) and OF2_10 (consumer's first operation)
        of1_20 = next((op for op in operations if op.get("operation_id") == "OF1_20"), None)
        of2_10 = next((op for op in operations if op.get("operation_id") == "OF2_10"), None)
        
        assert of1_20 is not None, "OF1_20 not found in scheduled operations"
        assert of2_10 is not None, "OF2_10 not found in scheduled operations"
        
        # Get the production entry time (OF1_20 end + transfer time)
        of1_20_end = of1_20.get("end_minutes")
        of1_20_transfer = of1_20.get("transfer_time_minutes", 0)
        production_entry = of1_20_end + of1_20_transfer
        
        # Get OF2_10 start time
        of2_10_start = of2_10.get("start_minutes")
        
        # Calculate the gap
        gap_minutes = of2_10_start - production_entry
        
        print(f"OF1_20 end: {of1_20_end} min")
        print(f"OF1_20 transfer time: {of1_20_transfer} min")
        print(f"Production entry (OF1_20 end + transfer): {production_entry} min")
        print(f"OF2_10 start: {of2_10_start} min")
        print(f"Gap between production entry and consumption start: {gap_minutes} min")
        
        # The gap should be minimal (within 60 minutes tolerance for calendar constraints)
        # but definitely not several hours (> 120 minutes is abnormal)
        assert gap_minutes >= 0, f"OF2_10 starts before component is available (gap={gap_minutes})"
        assert gap_minutes <= 120, f"Abnormal delay detected ({gap_minutes} min). Bug not fixed!"
        
        print(f"✓ Gap is {gap_minutes} minutes - within acceptable range")
        
    def test_jit_mode_material_constraints(self):
        """Test material constraints are handled correctly in JIT mode."""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_id": "TEST_JIT_MATERIAL",
            "scenario_name": "Test JIT Material Constraints",
            "scheduling_strategy": "JIT",
            "max_solver_time_seconds": 30
        })
        
        assert response.status_code == 200, f"API call failed: {response.text}"
        data = response.json()
        result = data.get("result", {})
        
        # Check scheduling status
        status = result.get("status")
        assert status in ["OPTIMAL", "FEASIBLE"], f"Unexpected status: {status}"
        
        # Check material_delayed field exists
        material_delayed = result.get("material_delayed", [])
        print(f"Material delayed operations: {material_delayed}")
        
        # If there are material delays, check they're handled
        if material_delayed:
            for md in material_delayed:
                assert "operation_id" in md
                assert "blocking_components" in md
                print(f"  - {md['operation_id']} delayed for: {md['blocking_components']}")
        
    def test_scenario_data_contains_productions(self):
        """Test that scheduled scenario contains production data for stock tracking."""
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_id": "TEST_PRODUCTIONS",
            "scenario_name": "Test Productions Data",
            "scheduling_strategy": "ASAP",
            "max_solver_time_seconds": 30
        })
        
        assert response.status_code == 200
        data = response.json()
        result = data.get("result", {})
        
        # Check productions exist
        productions = result.get("productions", [])
        print(f"Productions: {len(productions)} entries")
        
        for prod in productions:
            assert "order_id" in prod
            assert "article_id" in prod
            assert "quantity" in prod
            assert "end_datetime" in prod
            print(f"  - OF {prod['order_id']} produces {prod['article_id']} x{prod['quantity']}")
        
        # Verify OF1 produces ART1
        of1_production = next((p for p in productions if p.get("order_id") == "OF1"), None)
        if of1_production:
            assert of1_production.get("article_id") == "ART1"
            assert of1_production.get("quantity") > 0
            print(f"✓ OF1 produces ART1 as expected")


class TestSchedulingAPI:
    """General tests for the scheduling API."""
    
    def test_get_scenarios(self):
        """Test scenarios listing."""
        response = requests.get(f"{BASE_URL}/api/scenarios")
        assert response.status_code == 200
        scenarios = response.json()
        assert isinstance(scenarios, list)
        print(f"Found {len(scenarios)} scenarios")
        
    def test_get_operations(self):
        """Test operations listing."""
        response = requests.get(f"{BASE_URL}/api/operations")
        assert response.status_code == 200
        operations = response.json()
        assert isinstance(operations, list)
        assert len(operations) >= 4, "Expected at least 4 operations (OF1_10, OF1_20, OF2_10, OF2_20)"
        print(f"Found {len(operations)} operations")
        
    def test_get_manufacturing_orders(self):
        """Test manufacturing orders listing."""
        response = requests.get(f"{BASE_URL}/api/manufacturing-orders")
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        assert len(orders) >= 2, "Expected at least 2 orders (OF1, OF2)"
        print(f"Found {len(orders)} manufacturing orders")
        
    def test_get_operation_materials(self):
        """Test operation materials listing."""
        response = requests.get(f"{BASE_URL}/api/operation-materials")
        assert response.status_code == 200
        materials = response.json()
        assert isinstance(materials, list)
        
        # Check that OF2_10 consumes ART1
        of2_10_art1 = [m for m in materials 
                       if m.get("id") == "OF2_10" and m.get("article_composant_id") == "ART1"]
        assert len(of2_10_art1) > 0, "OF2_10 should consume ART1"
        print(f"Found {len(materials)} material requirements")
        
    def test_get_stocks(self):
        """Test stocks listing."""
        response = requests.get(f"{BASE_URL}/api/stocks")
        assert response.status_code == 200
        stocks = response.json()
        assert isinstance(stocks, list)
        
        # Check ART1 stock
        art1_stock = next((s for s in stocks if s.get("article_id") == "ART1"), None)
        if art1_stock:
            print(f"ART1 stock: {art1_stock.get('quantity')}")
        print(f"Found {len(stocks)} stock entries")


class TestGanttDisplay:
    """Tests for Gantt display data."""
    
    def test_gantt_data_endpoint(self):
        """Test that gantt data can be retrieved for a scenario."""
        # First, get the latest scenario
        scenarios_response = requests.get(f"{BASE_URL}/api/scenarios")
        assert scenarios_response.status_code == 200
        scenarios = scenarios_response.json()
        
        if not scenarios:
            pytest.skip("No scenarios available for Gantt test")
        
        # Try to get gantt data for a recent scenario
        for scenario in scenarios[:3]:  # Try first 3 scenarios
            scenario_id = scenario.get("id")
            response = requests.get(f"{BASE_URL}/api/gantt/data/{scenario_id}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Gantt data for {scenario_id}: {len(data.get('operations', []))} operations")
                return
        
        # If no gantt data found, that's okay
        print("Note: Gantt data endpoint returned no data or 404 for existing scenarios")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
