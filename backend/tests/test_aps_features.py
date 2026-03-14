"""
Test APS Features - Iteration 4
================================
Tests for:
1. PUT /api/rules/{id} - Edit existing business rule
2. GET /api/aps/kpis - APS KPIs (OTD, late orders, utilization, WIP)
3. GET /api/aps/capacity - Capacity by machine with calendars
4. GET /api/aps/bom - BOM list
5. POST /api/import/bom - BOM CSV import
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API = f"{BASE_URL}/api"


class TestBusinessRulesEdit:
    """Tests for PUT /api/rules/{id} endpoint - Edit business rules."""
    
    def test_put_rule_updates_name(self):
        """Test PUT /api/rules/{id} updates rule name."""
        # First, get existing rules
        response = requests.get(f"{API}/rules")
        assert response.status_code == 200, f"GET /rules failed: {response.text}"
        rules = response.json()
        
        if len(rules) == 0:
            pytest.skip("No rules to test PUT endpoint")
        
        rule = rules[0]
        original_name = rule['name']
        rule_id = rule['id']
        
        # Update the rule
        test_name = f"TEST_UPDATE_{uuid.uuid4().hex[:8]}"
        update_response = requests.put(
            f"{API}/rules/{rule_id}",
            json={"name": test_name}
        )
        assert update_response.status_code == 200, f"PUT /rules failed: {update_response.text}"
        
        updated_rule = update_response.json()
        assert updated_rule['name'] == test_name
        
        # Verify with GET
        get_response = requests.get(f"{API}/rules/{rule_id}")
        assert get_response.status_code == 200
        assert get_response.json()['name'] == test_name
        
        # Restore original name
        restore_response = requests.put(
            f"{API}/rules/{rule_id}",
            json={"name": original_name}
        )
        assert restore_response.status_code == 200

    def test_put_rule_updates_rule_type(self):
        """Test PUT /api/rules/{id} updates rule_type (ALLOW, FORBID, PREFER)."""
        response = requests.get(f"{API}/rules")
        rules = response.json()
        
        if len(rules) == 0:
            pytest.skip("No rules to test")
        
        rule = rules[0]
        original_type = rule['rule_type']
        rule_id = rule['id']
        
        # Change to PREFER
        update_response = requests.put(
            f"{API}/rules/{rule_id}",
            json={"rule_type": "PREFER"}
        )
        assert update_response.status_code == 200
        assert update_response.json()['rule_type'] == 'PREFER'
        
        # Restore original type
        requests.put(f"{API}/rules/{rule_id}", json={"rule_type": original_type})

    def test_put_rule_updates_machine_id(self):
        """Test PUT /api/rules/{id} updates machine_id."""
        response = requests.get(f"{API}/rules")
        rules = response.json()
        
        if len(rules) == 0:
            pytest.skip("No rules to test")
        
        rule = rules[0]
        original_machine = rule['machine_id']
        rule_id = rule['id']
        
        # Get available machines
        machines_response = requests.get(f"{API}/machines")
        machines = machines_response.json()
        
        if len(machines) < 2:
            pytest.skip("Not enough machines to test")
        
        # Find a different machine
        new_machine = machines[1]['id'] if machines[0]['id'] == original_machine else machines[0]['id']
        
        # Update machine
        update_response = requests.put(
            f"{API}/rules/{rule_id}",
            json={"machine_id": new_machine}
        )
        assert update_response.status_code == 200
        assert update_response.json()['machine_id'] == new_machine
        
        # Restore original machine
        requests.put(f"{API}/rules/{rule_id}", json={"machine_id": original_machine})

    def test_put_rule_not_found(self):
        """Test PUT /api/rules/{id} returns 404 for non-existent rule."""
        fake_id = "non-existent-rule-id"
        response = requests.put(
            f"{API}/rules/{fake_id}",
            json={"name": "Test"}
        )
        assert response.status_code == 404

    def test_put_rule_empty_update(self):
        """Test PUT /api/rules/{id} returns 400 for empty update."""
        response = requests.get(f"{API}/rules")
        rules = response.json()
        
        if len(rules) == 0:
            pytest.skip("No rules to test")
        
        rule_id = rules[0]['id']
        
        # Try empty update
        response = requests.put(
            f"{API}/rules/{rule_id}",
            json={}
        )
        assert response.status_code == 400


class TestAPSKPIs:
    """Tests for GET /api/aps/kpis endpoint."""
    
    def test_get_kpis_returns_otd(self):
        """Test KPIs endpoint returns OTD data."""
        response = requests.get(f"{API}/aps/kpis")
        assert response.status_code == 200, f"GET /aps/kpis failed: {response.text}"
        
        data = response.json()
        assert 'otd' in data
        assert 'rate' in data['otd']
        assert 'on_time' in data['otd']
        assert 'total' in data['otd']
        
        # Rate should be between 0 and 100
        assert 0 <= data['otd']['rate'] <= 100

    def test_get_kpis_returns_late_orders(self):
        """Test KPIs endpoint returns late orders data."""
        response = requests.get(f"{API}/aps/kpis")
        assert response.status_code == 200
        
        data = response.json()
        assert 'late_orders' in data
        assert 'count' in data['late_orders']
        assert 'orders' in data['late_orders']
        assert isinstance(data['late_orders']['orders'], list)

    def test_get_kpis_returns_utilization(self):
        """Test KPIs endpoint returns machine utilization data."""
        response = requests.get(f"{API}/aps/kpis")
        assert response.status_code == 200
        
        data = response.json()
        assert 'utilization' in data
        assert 'overall_rate' in data['utilization']
        assert 'capacity_hours' in data['utilization']
        assert 'loaded_hours' in data['utilization']
        assert 'by_machine' in data['utilization']

    def test_get_kpis_returns_wip(self):
        """Test KPIs endpoint returns WIP (Work In Progress) data."""
        response = requests.get(f"{API}/aps/kpis")
        assert response.status_code == 200
        
        data = response.json()
        assert 'wip' in data
        assert 'orders_count' in data['wip']
        assert 'operations_scheduled' in data['wip']
        assert 'operations_total' in data['wip']

    def test_get_kpis_returns_timestamp(self):
        """Test KPIs endpoint returns timestamp."""
        response = requests.get(f"{API}/aps/kpis")
        assert response.status_code == 200
        
        data = response.json()
        assert 'timestamp' in data
        assert data['timestamp'] is not None


class TestAPSCapacity:
    """Tests for GET /api/aps/capacity endpoint."""
    
    def test_get_capacity_returns_slots(self):
        """Test capacity endpoint returns capacity slots."""
        response = requests.get(f"{API}/aps/capacity?horizon_days=7")
        assert response.status_code == 200, f"GET /aps/capacity failed: {response.text}"
        
        data = response.json()
        assert 'capacity_slots' in data
        assert isinstance(data['capacity_slots'], list)

    def test_get_capacity_slot_structure(self):
        """Test capacity slot has correct structure."""
        response = requests.get(f"{API}/aps/capacity?horizon_days=7")
        assert response.status_code == 200
        
        data = response.json()
        if len(data['capacity_slots']) > 0:
            slot = data['capacity_slots'][0]
            assert 'machine_id' in slot
            assert 'date' in slot
            assert 'capacity_minutes' in slot
            assert 'loaded_minutes' in slot
            assert 'available_minutes' in slot
            assert 'utilization_rate' in slot
            assert 'is_overloaded' in slot

    def test_get_capacity_summary_by_machine(self):
        """Test capacity endpoint returns summary by machine."""
        response = requests.get(f"{API}/aps/capacity?horizon_days=7")
        assert response.status_code == 200
        
        data = response.json()
        assert 'summary_by_machine' in data
        
        for machine_id, summary in data['summary_by_machine'].items():
            assert 'total_capacity_hours' in summary
            assert 'total_loaded_hours' in summary
            assert 'average_utilization' in summary
            assert 'overloaded_days' in summary

    def test_get_capacity_horizon_parameter(self):
        """Test capacity endpoint respects horizon_days parameter."""
        # Get with 3 days
        response_3 = requests.get(f"{API}/aps/capacity?horizon_days=3")
        assert response_3.status_code == 200
        data_3 = response_3.json()
        
        # Get with 7 days
        response_7 = requests.get(f"{API}/aps/capacity?horizon_days=7")
        assert response_7.status_code == 200
        data_7 = response_7.json()
        
        # 7 days should have more or equal slots than 3 days
        assert len(data_7['capacity_slots']) >= len(data_3['capacity_slots'])


class TestAPSBOM:
    """Tests for BOM (Bill of Materials) endpoints."""
    
    def test_get_bom_returns_list(self):
        """Test GET /api/aps/bom returns BOM list."""
        response = requests.get(f"{API}/aps/bom")
        assert response.status_code == 200, f"GET /aps/bom failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)

    def test_bom_line_structure(self):
        """Test BOM line has correct structure."""
        response = requests.get(f"{API}/aps/bom")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            bom_line = data[0]
            assert 'parent_article_id' in bom_line
            assert 'child_article_id' in bom_line
            assert 'quantity' in bom_line
            # Optional fields
            if 'level' in bom_line:
                assert isinstance(bom_line['level'], int)
            if 'scrap_rate' in bom_line:
                assert isinstance(bom_line['scrap_rate'], (int, float))

    def test_import_bom_csv(self):
        """Test POST /api/import/bom imports BOM from CSV."""
        # Create test CSV
        csv_content = """parent_article_id,child_article_id,quantity,level,unit,scrap_rate
TEST_PARENT_001,TEST_COMP_A,3,1,pièce,0.01
TEST_PARENT_001,TEST_COMP_B,2,1,pièce,0"""
        
        files = {'file': ('test_bom.csv', csv_content, 'text/csv')}
        response = requests.post(f"{API}/import/bom", files=files)
        
        assert response.status_code == 200, f"POST /import/bom failed: {response.text}"
        data = response.json()
        
        assert data['success'] is True
        assert data['records_imported'] == 2

    def test_bom_explode(self):
        """Test POST /api/aps/bom/explode explodes BOM."""
        # First ensure we have BOM data
        csv_content = """parent_article_id,child_article_id,quantity,level,unit,scrap_rate
EXPLODE_TEST,EXPLODE_COMP_A,2,1,pièce,0.02
EXPLODE_TEST,EXPLODE_COMP_B,4,1,pièce,0"""
        
        files = {'file': ('test_bom.csv', csv_content, 'text/csv')}
        requests.post(f"{API}/import/bom", files=files)
        
        # Now test explosion
        response = requests.post(f"{API}/aps/bom/explode?article_id=EXPLODE_TEST&quantity=1.0")
        assert response.status_code == 200, f"POST /aps/bom/explode failed: {response.text}"
        
        data = response.json()
        assert 'article_id' in data
        assert 'quantity' in data
        assert 'explosion_detail' in data
        assert 'components_total' in data

    def test_delete_all_bom(self):
        """Test DELETE /api/aps/bom deletes all BOM lines."""
        response = requests.delete(f"{API}/aps/bom")
        assert response.status_code == 200
        
        data = response.json()
        assert 'deleted' in data
        
        # Verify deletion
        get_response = requests.get(f"{API}/aps/bom")
        assert get_response.status_code == 200
        assert len(get_response.json()) == 0


class TestAPSMRP:
    """Tests for MRP (Material Requirements Planning) endpoint."""
    
    def test_get_mrp_returns_results(self):
        """Test GET /api/aps/mrp returns MRP results."""
        response = requests.get(f"{API}/aps/mrp")
        assert response.status_code == 200, f"GET /aps/mrp failed: {response.text}"
        
        data = response.json()
        assert 'mrp_results' in data
        assert 'summary' in data

    def test_get_mrp_summary_structure(self):
        """Test MRP summary has correct structure."""
        response = requests.get(f"{API}/aps/mrp")
        assert response.status_code == 200
        
        data = response.json()
        summary = data['summary']
        
        assert 'total_articles' in summary
        assert 'articles_with_shortage' in summary
        assert 'articles_ok' in summary
        assert 'total_orders' in summary


class TestIntegration:
    """Integration tests for APS features."""
    
    def test_full_aps_workflow(self):
        """Test complete APS workflow: BOM import -> Capacity -> KPIs."""
        # 1. Import BOM
        csv_content = """parent_article_id,child_article_id,quantity,level,unit,scrap_rate
INTEGRATION_TEST,COMP_INT_A,1,1,pièce,0"""
        files = {'file': ('test_bom.csv', csv_content, 'text/csv')}
        import_response = requests.post(f"{API}/import/bom", files=files)
        assert import_response.status_code == 200
        
        # 2. Get BOM
        bom_response = requests.get(f"{API}/aps/bom")
        assert bom_response.status_code == 200
        
        # 3. Get Capacity
        capacity_response = requests.get(f"{API}/aps/capacity?horizon_days=7")
        assert capacity_response.status_code == 200
        
        # 4. Get KPIs
        kpis_response = requests.get(f"{API}/aps/kpis")
        assert kpis_response.status_code == 200
        
        # 5. Verify all returned valid data
        assert bom_response.json() is not None
        assert capacity_response.json().get('capacity_slots') is not None
        assert kpis_response.json().get('otd') is not None
