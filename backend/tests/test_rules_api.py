"""
Backend API tests for Business Rules module (ALLOW, FORBID, PREFER)
Tests: GET /api/rules, POST /api/rules, DELETE /api/rules/{id}
"""
import pytest
import requests
import os
import uuid

# Use environment variable for base URL
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://shop-scheduler-9.preview.emergentagent.com').rstrip('/')
API_URL = f"{BASE_URL}/api"


class TestHealthCheck:
    """Basic health check to verify API is accessible"""
    
    def test_api_is_accessible(self):
        response = requests.get(f"{API_URL}/rules", timeout=10)
        assert response.status_code == 200, f"API not accessible: {response.status_code}"
        print(f"✓ API is accessible at {API_URL}")

    def test_machines_endpoint(self):
        """Verify machines endpoint works - needed for rules"""
        response = requests.get(f"{API_URL}/machines", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Expected list of machines"
        print(f"✓ Found {len(data)} machines available")
        return data


class TestGetRules:
    """GET /api/rules - list rules in simplified format"""
    
    def test_get_rules_returns_list(self):
        response = requests.get(f"{API_URL}/rules", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Expected list of rules"
        print(f"✓ GET /api/rules returned {len(data)} rules")
    
    def test_rules_have_correct_format(self):
        """Verify each rule has simplified POC format fields"""
        response = requests.get(f"{API_URL}/rules", timeout=10)
        assert response.status_code == 200
        rules = response.json()
        
        if len(rules) == 0:
            pytest.skip("No rules to verify format")
        
        for rule in rules:
            # Required fields
            assert 'id' in rule, f"Rule missing 'id': {rule}"
            assert 'name' in rule, f"Rule missing 'name': {rule}"
            assert 'rule_type' in rule, f"Rule missing 'rule_type': {rule}"
            assert 'machine_id' in rule, f"Rule missing 'machine_id': {rule}"
            assert 'active' in rule, f"Rule missing 'active': {rule}"
            
            # rule_type must be ALLOW, FORBID, or PREFER
            assert rule['rule_type'] in ['ALLOW', 'FORBID', 'PREFER'], \
                f"Invalid rule_type: {rule['rule_type']}"
            
            # Optional fields (should exist but can be null)
            assert 'task_id' in rule, f"Rule missing 'task_id': {rule}"
            assert 'work_center_id' in rule, f"Rule missing 'work_center_id': {rule}"
            assert 'article_id' in rule, f"Rule missing 'article_id': {rule}"
        
        print(f"✓ All {len(rules)} rules have correct simplified format")


class TestCreateRule:
    """POST /api/rules - create rules with different types"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get a valid machine_id for creating rules"""
        response = requests.get(f"{API_URL}/machines", timeout=10)
        machines = response.json()
        if not machines:
            pytest.skip("No machines available for testing")
        self.machine_id = machines[0]['id']
        self.machine_name = machines[0]['name']
        self.created_rule_ids = []
        yield
        # Cleanup: delete test-created rules
        for rule_id in self.created_rule_ids:
            try:
                requests.delete(f"{API_URL}/rules/{rule_id}", timeout=10)
            except:
                pass
    
    def test_create_forbid_rule_with_task_id(self):
        """Create FORBID rule with task_id and machine_id"""
        test_name = f"TEST_FORBID_task_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "task_id": "USINAGE",
            "rule_type": "FORBID",
            "machine_id": self.machine_id,
            "active": True
        }
        
        response = requests.post(f"{API_URL}/rules", json=payload, timeout=10)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        rule = response.json()
        self.created_rule_ids.append(rule['id'])
        
        # Validate created rule
        assert rule['name'] == test_name
        assert rule['task_id'] == "USINAGE"
        assert rule['rule_type'] == "FORBID"
        assert rule['machine_id'] == self.machine_id
        assert rule['active'] == True
        
        # Verify persistence with GET
        get_response = requests.get(f"{API_URL}/rules", timeout=10)
        rules = get_response.json()
        created_rule = next((r for r in rules if r['id'] == rule['id']), None)
        assert created_rule is not None, "Created rule not found in list"
        assert created_rule['rule_type'] == "FORBID"
        
        print(f"✓ Created FORBID rule: {test_name}")
    
    def test_create_prefer_rule_with_task_and_workcenter(self):
        """Create PREFER rule with task_id + work_center_id"""
        test_name = f"TEST_PREFER_combo_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "task_id": "ASSEMBLAGE",
            "work_center_id": "WC001",
            "rule_type": "PREFER",
            "machine_id": self.machine_id,
            "active": True
        }
        
        response = requests.post(f"{API_URL}/rules", json=payload, timeout=10)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        rule = response.json()
        self.created_rule_ids.append(rule['id'])
        
        # Validate created rule
        assert rule['name'] == test_name
        assert rule['task_id'] == "ASSEMBLAGE"
        assert rule['work_center_id'] == "WC001"
        assert rule['rule_type'] == "PREFER"
        assert rule['machine_id'] == self.machine_id
        
        # Verify persistence
        get_response = requests.get(f"{API_URL}/rules", timeout=10)
        rules = get_response.json()
        created_rule = next((r for r in rules if r['id'] == rule['id']), None)
        assert created_rule is not None
        assert created_rule['task_id'] == "ASSEMBLAGE"
        assert created_rule['work_center_id'] == "WC001"
        
        print(f"✓ Created PREFER rule with task+workcenter: {test_name}")
    
    def test_create_allow_rule_with_workcenter_only(self):
        """Create ALLOW rule with only work_center_id"""
        test_name = f"TEST_ALLOW_wc_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "work_center_id": "WC_TEST",
            "rule_type": "ALLOW",
            "machine_id": self.machine_id,
            "active": True
        }
        
        response = requests.post(f"{API_URL}/rules", json=payload, timeout=10)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        rule = response.json()
        self.created_rule_ids.append(rule['id'])
        
        assert rule['rule_type'] == "ALLOW"
        assert rule['work_center_id'] == "WC_TEST"
        
        print(f"✓ Created ALLOW rule with work_center_id only: {test_name}")
    
    def test_create_rule_with_article_id(self):
        """Create rule with article_id (combined with task_id)"""
        test_name = f"TEST_FORBID_article_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "task_id": "USINAGE",
            "article_id": "ART001",
            "rule_type": "FORBID",
            "machine_id": self.machine_id,
            "active": True
        }
        
        response = requests.post(f"{API_URL}/rules", json=payload, timeout=10)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        rule = response.json()
        self.created_rule_ids.append(rule['id'])
        
        assert rule['article_id'] == "ART001"
        assert rule['task_id'] == "USINAGE"
        
        print(f"✓ Created rule with article_id: {test_name}")
    
    def test_create_inactive_rule(self):
        """Create an inactive rule"""
        test_name = f"TEST_INACTIVE_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "task_id": "TEST",
            "rule_type": "FORBID",
            "machine_id": self.machine_id,
            "active": False
        }
        
        response = requests.post(f"{API_URL}/rules", json=payload, timeout=10)
        assert response.status_code == 200
        
        rule = response.json()
        self.created_rule_ids.append(rule['id'])
        
        assert rule['active'] == False
        print(f"✓ Created inactive rule: {test_name}")


class TestDeleteRule:
    """DELETE /api/rules/{id} - delete a rule"""
    
    @pytest.fixture
    def created_rule(self):
        """Create a test rule to delete"""
        # Get a machine
        response = requests.get(f"{API_URL}/machines", timeout=10)
        machines = response.json()
        if not machines:
            pytest.skip("No machines available")
        
        payload = {
            "name": f"TEST_DELETE_{uuid.uuid4().hex[:8]}",
            "task_id": "DELETE_TEST",
            "rule_type": "FORBID",
            "machine_id": machines[0]['id'],
            "active": True
        }
        
        response = requests.post(f"{API_URL}/rules", json=payload, timeout=10)
        assert response.status_code == 200
        return response.json()
    
    def test_delete_rule_success(self, created_rule):
        """Delete existing rule"""
        rule_id = created_rule['id']
        rule_name = created_rule['name']
        
        # Delete the rule
        response = requests.delete(f"{API_URL}/rules/{rule_id}", timeout=10)
        assert response.status_code == 200, f"Delete failed: {response.text}"
        
        result = response.json()
        assert result.get('message') == "Deleted successfully"
        
        # Verify deletion with GET
        get_response = requests.get(f"{API_URL}/rules", timeout=10)
        rules = get_response.json()
        deleted_rule = next((r for r in rules if r['id'] == rule_id), None)
        assert deleted_rule is None, "Deleted rule still exists"
        
        print(f"✓ Deleted rule: {rule_name}")
    
    def test_delete_nonexistent_rule(self):
        """Delete non-existent rule returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(f"{API_URL}/rules/{fake_id}", timeout=10)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ DELETE non-existent rule returns 404")


class TestValidationRules:
    """Test validation requirements for rules"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.get(f"{API_URL}/machines", timeout=10)
        machines = response.json()
        if not machines:
            pytest.skip("No machines available")
        self.machine_id = machines[0]['id']
        self.created_rule_ids = []
        yield
        for rule_id in self.created_rule_ids:
            try:
                requests.delete(f"{API_URL}/rules/{rule_id}", timeout=10)
            except:
                pass
    
    def test_rule_type_normalization(self):
        """Test that rule_type is normalized to uppercase"""
        test_name = f"TEST_lowercase_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "task_id": "TEST",
            "rule_type": "forbid",  # lowercase
            "machine_id": self.machine_id
        }
        
        response = requests.post(f"{API_URL}/rules", json=payload, timeout=10)
        assert response.status_code == 200
        
        rule = response.json()
        self.created_rule_ids.append(rule['id'])
        
        # Should be normalized to uppercase
        assert rule['rule_type'] == "FORBID"
        print("✓ Rule type normalized to uppercase")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
