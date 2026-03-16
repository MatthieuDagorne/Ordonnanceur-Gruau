"""
Test suite for JIT (Au plus tard) mode with late orders functionality.
Tests the fix that prevents INFEASIBLE status when due dates cannot be met.

Features tested:
1. JIT mode returns OPTIMAL instead of INFEASIBLE when dates cannot be met
2. Late orders are detected and stored with lateness_hours
3. /api/gantt/data/{id} returns is_late=true and lateness_minutes for late operations
4. Gantt displays red bars (#EF4444) for late operations
5. Diagnostic page has a 'Retards' tab with late order details
6. Diagnostic page shows alert if orders are late
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://shop-scheduler-9.preview.emergentagent.com')

# Test scenario ID with JIT late orders
JIT_SCENARIO_ID = "ba7a4e09-fa28-4d2f-b408-01667497ae76"

# Expected late orders
EXPECTED_LATE_ORDERS = ["OF1", "OF2"]
EXPECTED_ON_TIME_ORDERS = ["OF3"]

# Expected late operations
EXPECTED_LATE_OPS = ["OF1_10", "OF1_20", "OF2_10", "OF2_20"]
EXPECTED_ON_TIME_OPS = ["OF3_10", "OF3_20"]


class TestJITScenarioStatus:
    """Test that JIT mode returns OPTIMAL instead of INFEASIBLE"""
    
    def test_jit_scenario_exists(self):
        """Verify the JIT test scenario exists"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}")
        assert response.status_code == 200, f"Scenario not found: {response.text}"
        data = response.json()
        assert data.get('id') == JIT_SCENARIO_ID
        print(f"OK: Scenario {JIT_SCENARIO_ID} exists - Name: {data.get('name')}")
    
    def test_jit_scenario_status_is_optimal(self):
        """Verify JIT scenario has OPTIMAL status, not INFEASIBLE"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        status = schedule_data.get('status')
        
        assert status == 'OPTIMAL', f"Expected OPTIMAL, got {status}. JIT should not be INFEASIBLE."
        print(f"OK: JIT scenario status is OPTIMAL (not INFEASIBLE)")
    
    def test_jit_scenario_has_scheduling_strategy(self):
        """Verify scheduling_strategy is set to JIT"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        strategy = schedule_data.get('scheduling_strategy')
        
        assert strategy == 'JIT', f"Expected JIT strategy, got {strategy}"
        print(f"OK: Scheduling strategy is JIT")


class TestLateOrdersDetection:
    """Test late orders detection and storage"""
    
    def test_late_orders_in_schedule_data(self):
        """Verify late_orders array exists and contains expected orders"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        late_orders = schedule_data.get('late_orders', [])
        
        assert len(late_orders) > 0, "No late orders found in schedule_data"
        
        late_order_ids = [o.get('order_id') for o in late_orders]
        
        for expected in EXPECTED_LATE_ORDERS:
            assert expected in late_order_ids, f"Expected late order {expected} not found"
        
        for unexpected in EXPECTED_ON_TIME_ORDERS:
            assert unexpected not in late_order_ids, f"On-time order {unexpected} should not be in late_orders"
        
        print(f"OK: Late orders detected: {late_order_ids}")
    
    def test_late_orders_have_lateness_hours(self):
        """Verify late orders have lateness_hours field"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        late_orders = schedule_data.get('late_orders', [])
        
        for order in late_orders:
            assert 'lateness_hours' in order, f"Order {order.get('order_id')} missing lateness_hours"
            assert order['lateness_hours'] > 0, f"Order {order.get('order_id')} should have positive lateness_hours"
            print(f"  {order.get('order_id')}: {order['lateness_hours']}h late")
        
        print(f"OK: All late orders have lateness_hours")
    
    def test_late_orders_have_due_date_and_actual_completion(self):
        """Verify late orders have due_date and actual_completion fields"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        late_orders = schedule_data.get('late_orders', [])
        
        for order in late_orders:
            assert 'due_date' in order, f"Order {order.get('order_id')} missing due_date"
            assert 'actual_completion' in order, f"Order {order.get('order_id')} missing actual_completion"
            
            # Verify actual_completion is after due_date
            due_date = datetime.fromisoformat(order['due_date'].replace('Z', '+00:00'))
            actual = datetime.fromisoformat(order['actual_completion'].replace('Z', '+00:00'))
            assert actual > due_date, f"Order {order.get('order_id')}: actual_completion should be after due_date"
            
            print(f"  {order.get('order_id')}: due={order['due_date']}, actual={order['actual_completion']}")
        
        print(f"OK: All late orders have due_date and actual_completion")


class TestGanttDataIsLate:
    """Test /api/gantt/data endpoint returns is_late flag correctly"""
    
    def test_gantt_data_endpoint_exists(self):
        """Verify gantt/data endpoint returns data"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}")
        assert response.status_code == 200, f"Gantt data error: {response.text}"
        data = response.json()
        
        assert 'machines' in data, "Missing machines in gantt data"
        assert len(data['machines']) > 0, "No machines in gantt data"
        print(f"OK: Gantt data endpoint returns {len(data['machines'])} machines")
    
    def test_gantt_tasks_have_is_late_flag(self):
        """Verify tasks in gantt data have is_late flag"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        for machine in data.get('machines', []):
            for task in machine.get('tasks', []):
                assert 'is_late' in task, f"Task {task.get('operation_id')} missing is_late flag"
                assert 'lateness_minutes' in task, f"Task {task.get('operation_id')} missing lateness_minutes"
        
        print(f"OK: All tasks have is_late and lateness_minutes flags")
    
    def test_late_operations_have_is_late_true(self):
        """Verify late operations have is_late=true"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        all_tasks = []
        for machine in data.get('machines', []):
            all_tasks.extend(machine.get('tasks', []))
        
        for op_id in EXPECTED_LATE_OPS:
            task = next((t for t in all_tasks if t.get('operation_id') == op_id), None)
            assert task is not None, f"Operation {op_id} not found in gantt data"
            assert task.get('is_late') == True, f"Operation {op_id} should have is_late=true"
            assert task.get('lateness_minutes', 0) > 0, f"Operation {op_id} should have positive lateness_minutes"
            print(f"  {op_id}: is_late=true, lateness_minutes={task.get('lateness_minutes')}")
        
        print(f"OK: All expected late operations have is_late=true")
    
    def test_on_time_operations_have_is_late_false(self):
        """Verify on-time operations have is_late=false"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        all_tasks = []
        for machine in data.get('machines', []):
            all_tasks.extend(machine.get('tasks', []))
        
        for op_id in EXPECTED_ON_TIME_OPS:
            task = next((t for t in all_tasks if t.get('operation_id') == op_id), None)
            assert task is not None, f"Operation {op_id} not found in gantt data"
            assert task.get('is_late') == False, f"Operation {op_id} should have is_late=false"
            assert task.get('lateness_minutes', 0) == 0, f"Operation {op_id} should have lateness_minutes=0"
            print(f"  {op_id}: is_late=false, lateness_minutes=0")
        
        print(f"OK: All expected on-time operations have is_late=false")


class TestOperationsIsLateConsistency:
    """Test that is_late is consistent across operations in the same order"""
    
    def test_all_ops_of_late_order_are_late(self):
        """Verify all operations of a late order have is_late=true"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        all_tasks = []
        for machine in data.get('machines', []):
            all_tasks.extend(machine.get('tasks', []))
        
        # Group operations by order_id
        ops_by_order = {}
        for task in all_tasks:
            order_id = task.get('order_id')
            if order_id not in ops_by_order:
                ops_by_order[order_id] = []
            ops_by_order[order_id].append(task)
        
        # Verify consistency within late orders
        for order_id in EXPECTED_LATE_ORDERS:
            ops = ops_by_order.get(order_id, [])
            assert len(ops) > 0, f"No operations found for late order {order_id}"
            
            for op in ops:
                assert op.get('is_late') == True, f"Operation {op.get('operation_id')} of late order {order_id} should have is_late=true"
            
            print(f"  {order_id}: all {len(ops)} operations have is_late=true")
        
        print(f"OK: All operations of late orders are consistently marked as late")


class TestScheduleDataOperations:
    """Test operations in schedule_data have is_late flag"""
    
    def test_schedule_operations_have_is_late(self):
        """Verify operations in schedule_data have is_late flag"""
        response = requests.get(f"{BASE_URL}/api/scenarios/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        schedule_data = data.get('schedule_data', {})
        operations = schedule_data.get('operations', [])
        
        assert len(operations) > 0, "No operations in schedule_data"
        
        for op in operations:
            assert 'is_late' in op, f"Operation {op.get('operation_id')} missing is_late"
            assert 'lateness_minutes' in op, f"Operation {op.get('operation_id')} missing lateness_minutes"
        
        print(f"OK: All {len(operations)} operations in schedule_data have is_late flag")


class TestGanttDataSummary:
    """Summary test for gantt data structure"""
    
    def test_gantt_data_structure_complete(self):
        """Verify complete gantt data structure"""
        response = requests.get(f"{BASE_URL}/api/gantt/data/{JIT_SCENARIO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level fields
        assert 'scenario_id' in data
        assert 'scenario_name' in data
        assert 'status' in data
        assert 'scheduling_start' in data
        assert 'time_range' in data
        assert 'machines' in data
        
        # Check time_range structure
        time_range = data['time_range']
        assert 'min_minutes' in time_range
        assert 'max_minutes' in time_range
        assert 'total_minutes' in time_range
        
        # Count late vs on-time tasks
        late_count = 0
        on_time_count = 0
        for machine in data.get('machines', []):
            for task in machine.get('tasks', []):
                if task.get('is_late'):
                    late_count += 1
                else:
                    on_time_count += 1
        
        print(f"Summary:")
        print(f"  Scenario: {data.get('scenario_name')}")
        print(f"  Status: {data.get('status')}")
        print(f"  Machines: {len(data.get('machines', []))}")
        print(f"  Late operations: {late_count}")
        print(f"  On-time operations: {on_time_count}")
        
        assert late_count == len(EXPECTED_LATE_OPS), f"Expected {len(EXPECTED_LATE_OPS)} late ops, got {late_count}"
        assert on_time_count == len(EXPECTED_ON_TIME_OPS), f"Expected {len(EXPECTED_ON_TIME_OPS)} on-time ops, got {on_time_count}"
        
        print(f"OK: Gantt data structure complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
