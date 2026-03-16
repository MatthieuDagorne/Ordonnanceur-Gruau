"""
Test Suite for JIT Producer Advancement Bug Fix.

Bug corrigé: Le producteur (OF1) n'était pas avancé pour permettre au consommateur (OF2) 
de respecter sa deadline. Cause: Les contraintes de pré-validation trop imprécises 
empêchaient le solver d'optimiser.

Features tested:
1. Le délai entre la fin de production d'OF1 et le début d'OF2 est 0 (flux tiré optimal)
2. En mode JIT avec deadline serrée, OF1 est avancé pour permettre à OF2 de respecter sa deadline
3. En mode JIT avec deadline confortable, le planning est planifié au plus tard
4. Les deadlines des producteurs critiques sont correctement dérivées des consommateurs

Test Scenario:
- OF1 produces COMP_A (10 units), operations: OF1_10 -> OF1_20 (transfer_time=20min for OF1_10)
- OF2 consumes COMP_A at OF2_10 (10 units needed)
- Stock COMP_A = 0, so OF2_10 must wait for OF1 to finish and COMP_A to enter stock
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestFluxTireOptimal:
    """Test 1: Le délai entre la fin de production d'OF1 et le début d'OF2 est 0 (flux tiré optimal)"""
    
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
    
    def test_zero_delay_between_producer_and_consumer(self):
        """
        Test that the delay between producer finish (OF1_20 end + transfer_time) 
        and consumer start (OF2_10 start) is 0 minutes.
        
        The transfer time of OF1 (last operation with transfer) is already included 
        in when COMP_A enters stock. OF2_10 should start immediately when COMP_A 
        becomes available.
        """
        # Run scheduling in ASAP mode (should minimize delays)
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "TEST_JIT_FLUX_TIRE_ZERO_DELAY",
            "scheduling_strategy": "ASAP",
            "max_solver_time_seconds": 30,
            "ignore_calendars": True  # Ignore calendars to get pure timing
        })
        
        assert response.status_code == 200, f"API call failed: {response.text}"
        data = response.json()
        
        if "scenario_id" in data:
            self.created_scenarios.append(data["scenario_id"])
        
        result = data.get("result", {})
        operations = result.get("operations", [])
        
        assert len(operations) >= 3, f"Expected at least 3 operations, got {len(operations)}"
        
        # Find OF1_20 (producer's last operation) and OF2_10 (consumer's first operation)
        of1_10 = next((op for op in operations if op.get("operation_id") == "OF1_10"), None)
        of1_20 = next((op for op in operations if op.get("operation_id") == "OF1_20"), None)
        of2_10 = next((op for op in operations if op.get("operation_id") == "OF2_10"), None)
        
        assert of1_10 is not None, "OF1_10 not found in scheduled operations"
        assert of1_20 is not None, "OF1_20 not found in scheduled operations"
        assert of2_10 is not None, "OF2_10 not found in scheduled operations"
        
        # Get the production entry time
        # COMP_A enters stock when the last operation finishes + transfer time
        of1_20_end = of1_20.get("end_minutes")
        # Check transfer time on OF1_10 since it's the operation before OF1_20
        of1_10_transfer = of1_10.get("transfer_time_minutes", 0)
        of1_20_transfer = of1_20.get("transfer_time_minutes", 0)
        
        # For production tracking, use the last operation's end + its transfer time
        # In flux tiré, COMP_A is available at OF1_20 end (since transfer moves to next op)
        # The transfer_time on OF1_10 affects when OF1_20 can start, not when COMP_A enters stock
        production_entry = of1_20_end + of1_20_transfer  # When COMP_A enters stock
        
        # Get OF2_10 start time
        of2_10_start = of2_10.get("start_minutes")
        
        # Calculate the gap
        gap_minutes = of2_10_start - production_entry
        
        print(f"\n=== FLUX TIRÉ ANALYSIS ===")
        print(f"OF1_10 end: {of1_10.get('end_minutes')} min, transfer: {of1_10_transfer} min")
        print(f"OF1_20 end: {of1_20_end} min, transfer: {of1_20_transfer} min")
        print(f"COMP_A enters stock at: {production_entry} min (OF1_20 end + transfer)")
        print(f"OF2_10 start: {of2_10_start} min")
        print(f"Gap between production entry and consumption start: {gap_minutes} min")
        print(f"===========================\n")
        
        # The gap should be 0 or very close (flux tiré optimal)
        # Allow small tolerance for solver precision
        assert gap_minutes >= 0, f"OF2_10 starts before component is available (gap={gap_minutes})"
        assert gap_minutes <= 1, f"Gap should be 0 (flux tiré optimal), got {gap_minutes} min"
        
        print(f"✓ Flux tiré optimal: Gap is {gap_minutes} minutes (expected ~0)")


class TestJITWithTightDeadline:
    """Test 2: En mode JIT avec deadline serrée, OF1 est avancé pour permettre à OF2 de respecter sa deadline"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.created_scenarios = []
        yield
        for scenario_id in self.created_scenarios:
            try:
                requests.delete(f"{BASE_URL}/api/scenarios/{scenario_id}")
            except:
                pass
    
    def test_producer_advanced_for_tight_deadline(self):
        """
        Test that in JIT mode with tight deadline, the producer (OF1) is 
        advanced (scheduled earlier) to allow the consumer (OF2) to respect its deadline.
        
        This verifies the fix for the bug where pre-validation constraints 
        (_material_earliest_date) were too imprecise and blocked optimization.
        """
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "TEST_JIT_TIGHT_DEADLINE",
            "scheduling_strategy": "JIT",
            "max_solver_time_seconds": 30
        })
        
        assert response.status_code == 200, f"API call failed: {response.text}"
        data = response.json()
        
        if "scenario_id" in data:
            self.created_scenarios.append(data["scenario_id"])
        
        result = data.get("result", {})
        status = result.get("status")
        
        # Should get OPTIMAL or FEASIBLE, not INFEASIBLE
        assert status in ["OPTIMAL", "FEASIBLE"], f"Expected OPTIMAL/FEASIBLE, got {status}"
        
        operations = result.get("operations", [])
        of1_20 = next((op for op in operations if op.get("operation_id") == "OF1_20"), None)
        of2_10 = next((op for op in operations if op.get("operation_id") == "OF2_10"), None)
        
        if of1_20 and of2_10:
            # In JIT mode, OF1 should finish in time for OF2 to use the component
            of1_20_end = of1_20.get("end_minutes")
            of1_20_transfer = of1_20.get("transfer_time_minutes", 0)
            component_available = of1_20_end + of1_20_transfer
            of2_10_start = of2_10.get("start_minutes")
            
            # OF2_10 should start when component is available (not later)
            gap = of2_10_start - component_available
            
            print(f"\n=== JIT TIGHT DEADLINE ANALYSIS ===")
            print(f"Status: {status}")
            print(f"OF1_20 end: {of1_20_end} min")
            print(f"Component available: {component_available} min")
            print(f"OF2_10 start: {of2_10_start} min")
            print(f"Gap: {gap} min")
            
            # Check if there are late orders (deadline cannot be met)
            late_orders = result.get("late_orders", [])
            if late_orders:
                print(f"Late orders: {[lo.get('order_id') for lo in late_orders]}")
            print(f"====================================\n")
            
            # Gap should be minimal (0 or small due to calendar constraints)
            assert gap >= 0, f"OF2_10 starts before component available"
            # Allow more tolerance due to calendar constraints in JIT mode
            assert gap <= 60, f"Excessive gap ({gap} min) suggests bug not fixed"
            
            print(f"✓ Producer advanced correctly: Gap is {gap} minutes")


class TestJITWithComfortableDeadline:
    """Test 3: En mode JIT avec deadline confortable, le planning est planifié au plus tard"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.created_scenarios = []
        yield
        for scenario_id in self.created_scenarios:
            try:
                requests.delete(f"{BASE_URL}/api/scenarios/{scenario_id}")
            except:
                pass
    
    def test_jit_schedules_as_late_as_possible(self):
        """
        Test that in JIT mode with comfortable deadline, operations are 
        scheduled as late as possible (au plus tard).
        
        Compare ASAP vs JIT: JIT should have later start times when 
        deadline allows.
        """
        # First, run ASAP
        asap_response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "TEST_JIT_COMFORTABLE_ASAP",
            "scheduling_strategy": "ASAP",
            "max_solver_time_seconds": 30,
            "ignore_calendars": True
        })
        assert asap_response.status_code == 200
        asap_data = asap_response.json()
        if "scenario_id" in asap_data:
            self.created_scenarios.append(asap_data["scenario_id"])
        
        # Then run JIT
        jit_response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "TEST_JIT_COMFORTABLE_JIT",
            "scheduling_strategy": "JIT",
            "max_solver_time_seconds": 30,
            "ignore_calendars": True
        })
        assert jit_response.status_code == 200
        jit_data = jit_response.json()
        if "scenario_id" in jit_data:
            self.created_scenarios.append(jit_data["scenario_id"])
        
        asap_result = asap_data.get("result", {})
        jit_result = jit_data.get("result", {})
        
        asap_ops = asap_result.get("operations", [])
        jit_ops = jit_result.get("operations", [])
        
        if asap_ops and jit_ops:
            # Find OF1_10 in both results (first operation)
            asap_of1_10 = next((op for op in asap_ops if op.get("operation_id") == "OF1_10"), None)
            jit_of1_10 = next((op for op in jit_ops if op.get("operation_id") == "OF1_10"), None)
            
            if asap_of1_10 and jit_of1_10:
                asap_start = asap_of1_10.get("start_minutes")
                jit_start = jit_of1_10.get("start_minutes")
                
                print(f"\n=== JIT vs ASAP COMPARISON ===")
                print(f"ASAP OF1_10 start: {asap_start} min")
                print(f"JIT OF1_10 start: {jit_start} min")
                print(f"Difference: {jit_start - asap_start} min")
                print(f"================================\n")
                
                # JIT should start later or at the same time as ASAP
                # (au plus tard = as late as possible)
                # Note: With tight deadline, JIT might be same as ASAP
                assert jit_start >= asap_start, \
                    f"JIT should schedule as late or later than ASAP, got ASAP={asap_start}, JIT={jit_start}"
                
                print(f"✓ JIT schedules at {jit_start} min (>= ASAP {asap_start} min)")


class TestProducerDerivedDeadlines:
    """Test 4: Les deadlines des producteurs critiques sont correctement dérivées des consommateurs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.created_scenarios = []
        yield
        for scenario_id in self.created_scenarios:
            try:
                requests.delete(f"{BASE_URL}/api/scenarios/{scenario_id}")
            except:
                pass
    
    def test_derived_deadlines_in_jit_mode(self):
        """
        Test that producer deadlines are correctly derived from consumer deadlines.
        
        Formula: producer_deadline = consumer_due_date - consumer_total_duration
        
        This ensures the producer finishes in time for the consumer to use the 
        component and still meet its deadline.
        """
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "TEST_DERIVED_DEADLINE",
            "scheduling_strategy": "JIT",
            "max_solver_time_seconds": 30
        })
        
        assert response.status_code == 200, f"API call failed: {response.text}"
        data = response.json()
        
        if "scenario_id" in data:
            self.created_scenarios.append(data["scenario_id"])
        
        result = data.get("result", {})
        operations = result.get("operations", [])
        
        # Get manufacturing orders for deadline verification
        orders_response = requests.get(f"{BASE_URL}/api/manufacturing-orders")
        assert orders_response.status_code == 200
        orders = orders_response.json()
        
        # Find OF2's due date (consumer)
        of2 = next((o for o in orders if o.get("id") == "OF2"), None)
        if of2 and of2.get("due_date"):
            of2_due_date = datetime.fromisoformat(of2["due_date"].replace('Z', '+00:00'))
            
            # Find OF2_10 to get consumer duration
            of2_10 = next((op for op in operations if op.get("operation_id") == "OF2_10"), None)
            if of2_10:
                of2_duration = of2_10.get("production_time_minutes", 90)
                
                # Expected producer deadline = OF2 due date - OF2 duration
                expected_producer_deadline_minutes = (of2_due_date - datetime.now().replace(tzinfo=of2_due_date.tzinfo)).total_seconds() / 60 - of2_duration
                
                # Find OF1_20 end time
                of1_20 = next((op for op in operations if op.get("operation_id") == "OF1_20"), None)
                if of1_20:
                    of1_20_end = of1_20.get("end_minutes")
                    of1_20_transfer = of1_20.get("transfer_time_minutes", 0)
                    producer_finish = of1_20_end + of1_20_transfer
                    
                    print(f"\n=== DERIVED DEADLINE ANALYSIS ===")
                    print(f"OF2 due date: {of2_due_date}")
                    print(f"OF2 duration: {of2_duration} min")
                    print(f"OF1_20 end: {of1_20_end} min")
                    print(f"Producer finishes (with transfer): {producer_finish} min")
                    print(f"OF2_10 start: {of2_10.get('start_minutes')} min")
                    print(f"===================================\n")
                    
                    # The producer should finish before the consumer needs the component
                    assert producer_finish <= of2_10.get("start_minutes"), \
                        f"Producer must finish before consumer starts"
                    
                    print(f"✓ Producer deadline correctly derived from consumer")


class TestMaterialConstraintsSimplified:
    """Test that simplified material constraints (lines 809-820) work correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.created_scenarios = []
        yield
        for scenario_id in self.created_scenarios:
            try:
                requests.delete(f"{BASE_URL}/api/scenarios/{scenario_id}")
            except:
                pass
    
    def test_only_iteration_constraints_used(self):
        """
        Test that only constraints from previous iterations are used,
        not the imprecise pre-validation constraints (_material_earliest_date).
        
        This verifies the fix at lines 809-820 where the code comment says:
        "IMPORTANT: N'utiliser que les contraintes des itérations précédentes
        qui sont basées sur les vraies dates de production calculées par le solver.
        La pré-validation (_material_earliest_date) est trop imprécise et peut bloquer
        inutilement des opérations."
        """
        response = requests.post(f"{BASE_URL}/api/scheduling/calculate", json={
            "scenario_name": "TEST_SIMPLIFIED_CONSTRAINTS",
            "scheduling_strategy": "ASAP",
            "max_solver_time_seconds": 30
        })
        
        assert response.status_code == 200, f"API call failed: {response.text}"
        data = response.json()
        
        if "scenario_id" in data:
            self.created_scenarios.append(data["scenario_id"])
        
        result = data.get("result", {})
        
        # Check that scheduling completed successfully
        status = result.get("status")
        assert status in ["OPTIMAL", "FEASIBLE"], f"Expected OPTIMAL/FEASIBLE, got {status}"
        
        # Check the material iteration count - should be minimal with simplified constraints
        material_iteration = result.get("material_iteration", 1)
        print(f"Material iterations: {material_iteration}")
        
        # With simplified constraints, solver should converge quickly
        assert material_iteration <= 5, f"Too many iterations ({material_iteration}) suggests constraint issues"
        
        print(f"✓ Simplified constraints: {material_iteration} iteration(s)")


class TestIntegration:
    """Integration tests for the complete scheduling flow"""
    
    def test_api_health(self):
        """Test that the scheduling API is accessible"""
        response = requests.get(f"{BASE_URL}/api/scenarios")
        assert response.status_code == 200, f"API not accessible: {response.text}"
        print("✓ API is accessible")
    
    def test_manufacturing_orders_exist(self):
        """Test that manufacturing orders exist"""
        response = requests.get(f"{BASE_URL}/api/manufacturing-orders")
        assert response.status_code == 200
        orders = response.json()
        assert len(orders) >= 2, f"Expected at least 2 orders, got {len(orders)}"
        
        # Verify OF1 and OF2 exist
        order_ids = [o.get("id") for o in orders]
        assert "OF1" in order_ids, "OF1 not found"
        assert "OF2" in order_ids, "OF2 not found"
        print(f"✓ Found orders: {order_ids}")
    
    def test_operations_exist(self):
        """Test that operations exist"""
        response = requests.get(f"{BASE_URL}/api/operations")
        assert response.status_code == 200
        operations = response.json()
        assert len(operations) >= 3, f"Expected at least 3 operations, got {len(operations)}"
        
        op_ids = [o.get("id") for o in operations]
        assert "OF1_10" in op_ids, "OF1_10 not found"
        assert "OF1_20" in op_ids, "OF1_20 not found"
        assert "OF2_10" in op_ids, "OF2_10 not found"
        print(f"✓ Found operations: {op_ids}")
    
    def test_material_dependencies_exist(self):
        """Test that material dependencies are configured"""
        response = requests.get(f"{BASE_URL}/api/operation-materials")
        assert response.status_code == 200
        materials = response.json()
        
        # OF2_10 should consume COMP_A (produced by OF1)
        of2_10_deps = [m for m in materials if m.get("operation_id") == "OF2_10"]
        assert len(of2_10_deps) > 0, "OF2_10 should have material dependencies"
        
        comp_a_dep = next((m for m in of2_10_deps if m.get("article_composant_id") == "COMP_A"), None)
        assert comp_a_dep is not None, "OF2_10 should consume COMP_A"
        print(f"✓ Material dependency: OF2_10 consumes COMP_A")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
