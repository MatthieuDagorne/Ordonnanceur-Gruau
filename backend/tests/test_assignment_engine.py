"""
Backend API tests for Machine Assignment Engine with French terminology.
Tests: order_id jointure, date_besoin sorting, FORBID/PREFER rules, enriched operations.

Features tested:
- POST /api/reset-all - Reset all database collections
- POST /api/demo/load - Load demo data with French terminology
- GET /api/operations-enrichies - Join operations + orders via order_id
- GET /api/diagnostic/assignment - Complete machine assignment diagnostic
- FORBID rule: OF003_10 (ART003 + PLIAGE) must NOT be assigned to PLIEUSE_01
- PREFER rule: USINAGE operations must prefer TOUR_CNC_01
- Sorting by date_besoin: OF003 (2026-03-10) must be first (most urgent)
"""
import pytest
import requests
import os

# Use environment variable for base URL (from frontend/.env)
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://shop-scheduler-9.preview.emergentagent.com').rstrip('/')
API_URL = f"{BASE_URL}/api"

class TestResetAll:
    """POST /api/reset-all - Reset all database collections"""
    
    def test_reset_all_endpoint_available(self):
        """Verify reset-all endpoint is available"""
        response = requests.post(f"{API_URL}/reset-all", timeout=15)
        assert response.status_code == 200, f"Reset-all failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert 'success' in data, "Response missing 'success' field"
        assert data['success'] == True, f"Reset-all returned success=False: {data}"
        assert 'deleted' in data, "Response missing 'deleted' field"
        
        print(f"✓ POST /api/reset-all successful: {data.get('message')}")
        print(f"  Deleted counts: {data.get('deleted')}")


class TestDemoLoad:
    """POST /api/demo/load - Load demo data with French terminology"""
    
    def test_demo_load_endpoint_available(self):
        """Verify demo load endpoint is available"""
        response = requests.post(f"{API_URL}/demo/load", timeout=15)
        assert response.status_code == 200, f"Demo load failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert 'success' in data, "Response missing 'success' field"
        assert data['success'] == True, f"Demo load returned success=False: {data}"
        
        print(f"✓ POST /api/demo/load successful")
    
    def test_demo_data_counts(self):
        """Verify demo data loaded with correct counts"""
        # First reset and load demo data
        requests.post(f"{API_URL}/reset-all", timeout=15)
        response = requests.post(f"{API_URL}/demo/load", timeout=15)
        assert response.status_code == 200
        
        data = response.json()
        counts = data.get('counts', {})
        
        # Verify expected counts from demo_data.py
        assert counts.get('centres_de_charge') == 3, f"Expected 3 centres_de_charge, got {counts.get('centres_de_charge')}"
        assert counts.get('machines') == 7, f"Expected 7 machines, got {counts.get('machines')}"
        assert counts.get('manufacturing_orders') == 3, f"Expected 3 orders, got {counts.get('manufacturing_orders')}"
        assert counts.get('operations') == 7, f"Expected 7 operations, got {counts.get('operations')}"
        assert counts.get('rules') == 3, f"Expected 3 rules, got {counts.get('rules')}"
        
        print(f"✓ Demo data counts correct: {counts}")
    
    def test_demo_data_french_terminology(self):
        """Verify demo data uses French terminology (centres_de_charge, tache_id, etc.)"""
        # Verify centres_de_charge exists
        response = requests.get(f"{API_URL}/centres-de-charge", timeout=10)
        assert response.status_code == 200
        centres = response.json()
        
        centre_ids = [c.get('id') for c in centres]
        assert 'PLI01' in centre_ids, f"Missing PLI01 in centres: {centre_ids}"
        assert 'USI01' in centre_ids, f"Missing USI01 in centres: {centre_ids}"
        assert 'ASS01' in centre_ids, f"Missing ASS01 in centres: {centre_ids}"
        
        print(f"✓ Centres de charge with French terminology: {centre_ids}")
    
    def test_demo_machines_linked_to_centres(self):
        """Verify machines are linked to centres_de_charge"""
        response = requests.get(f"{API_URL}/machines", timeout=10)
        assert response.status_code == 200
        machines = response.json()
        
        # Check PLI01 centre has PLIEUSE machines
        pli_machines = [m for m in machines if m.get('centre_de_charge_id') == 'PLI01']
        assert len(pli_machines) >= 2, f"Expected 2+ machines in PLI01, got {len(pli_machines)}"
        
        machine_ids = [m.get('id') for m in pli_machines]
        assert 'PLIEUSE_01' in machine_ids, f"Missing PLIEUSE_01 in PLI01 machines: {machine_ids}"
        assert 'PLIEUSE_02' in machine_ids, f"Missing PLIEUSE_02 in PLI01 machines: {machine_ids}"
        
        print(f"✓ Machines linked to centres: PLI01 -> {machine_ids}")


class TestOperationsEnrichies:
    """GET /api/operations-enrichies - Join operations + orders via order_id"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure demo data is loaded"""
        requests.post(f"{API_URL}/reset-all", timeout=15)
        response = requests.post(f"{API_URL}/demo/load", timeout=15)
        assert response.status_code == 200, "Failed to load demo data"
    
    def test_operations_enrichies_endpoint_available(self):
        """Verify operations-enrichies endpoint is available"""
        response = requests.get(f"{API_URL}/operations-enrichies", timeout=10)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of enriched operations"
        assert len(data) == 7, f"Expected 7 operations, got {len(data)}"
        
        print(f"✓ GET /api/operations-enrichies returns {len(data)} operations")
    
    def test_operations_enrichies_has_order_data(self):
        """Verify enriched operations have article_id and date_besoin from joined order"""
        response = requests.get(f"{API_URL}/operations-enrichies", timeout=10)
        operations = response.json()
        
        # Check OF001_10 operation has correct article_id from OF001 order
        op_001_10 = next((op for op in operations if op.get('id') == 'OF001_10'), None)
        assert op_001_10 is not None, "OF001_10 operation not found"
        
        # Verify join data
        assert op_001_10.get('order_id') == 'OF001', f"Wrong order_id: {op_001_10.get('order_id')}"
        assert op_001_10.get('article_id') == 'ART001', f"Wrong article_id: {op_001_10.get('article_id')}"
        assert op_001_10.get('date_besoin') == '2026-03-18', f"Wrong date_besoin: {op_001_10.get('date_besoin')}"
        assert op_001_10.get('ordre_trouve') == True, "ordre_trouve should be True"
        
        print(f"✓ Operation OF001_10 enriched with order data: article={op_001_10.get('article_id')}, date={op_001_10.get('date_besoin')}")
    
    def test_operations_enrichies_of003_has_correct_data(self):
        """Verify OF003 operations have ART003 and date 2026-03-10"""
        response = requests.get(f"{API_URL}/operations-enrichies", timeout=10)
        operations = response.json()
        
        # Find OF003_10 (the PLIAGE operation for late order)
        op_003_10 = next((op for op in operations if op.get('id') == 'OF003_10'), None)
        assert op_003_10 is not None, "OF003_10 operation not found"
        
        # Verify enriched data
        assert op_003_10.get('order_id') == 'OF003', f"Wrong order_id: {op_003_10.get('order_id')}"
        assert op_003_10.get('article_id') == 'ART003', f"Wrong article_id: {op_003_10.get('article_id')}"
        assert op_003_10.get('date_besoin') == '2026-03-10', f"Wrong date_besoin: {op_003_10.get('date_besoin')}"
        assert op_003_10.get('tache_id') == 'PLIAGE', f"Wrong tache_id: {op_003_10.get('tache_id')}"
        assert op_003_10.get('centre_de_charge_id') == 'PLI01', f"Wrong centre: {op_003_10.get('centre_de_charge_id')}"
        
        print(f"✓ OF003_10: article={op_003_10.get('article_id')}, tache={op_003_10.get('tache_id')}, date={op_003_10.get('date_besoin')}")
    
    def test_operations_enrichies_sorted_by_date_besoin(self):
        """Verify operations are sorted by date_besoin (most urgent first)"""
        response = requests.get(f"{API_URL}/operations-enrichies", timeout=10)
        operations = response.json()
        
        # OF003 (date 2026-03-10) should be FIRST (most urgent)
        first_op = operations[0]
        assert first_op.get('order_id') == 'OF003', f"First operation should be OF003, got {first_op.get('order_id')}"
        assert first_op.get('date_besoin') == '2026-03-10', f"First date_besoin should be 2026-03-10"
        
        # Verify all OF003 operations come first (sorted by date)
        of003_ops = [op for op in operations if op.get('order_id') == 'OF003']
        assert len(of003_ops) == 2, f"Expected 2 OF003 operations, got {len(of003_ops)}"
        
        # Get positions of OF003 operations
        of003_positions = [i for i, op in enumerate(operations) if op.get('order_id') == 'OF003']
        assert all(pos < 3 for pos in of003_positions), f"OF003 ops should be in first 2 positions: {of003_positions}"
        
        print(f"✓ Operations sorted by date_besoin: first={first_op.get('order_id')}, date={first_op.get('date_besoin')}")


class TestDiagnosticAssignment:
    """GET /api/diagnostic/assignment - Complete machine assignment diagnostic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure demo data is loaded"""
        requests.post(f"{API_URL}/reset-all", timeout=15)
        response = requests.post(f"{API_URL}/demo/load", timeout=15)
        assert response.status_code == 200, "Failed to load demo data"
    
    def test_diagnostic_endpoint_available(self):
        """Verify diagnostic/assignment endpoint is available"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert 'summary' in data, "Response missing 'summary'"
        assert 'diagnostics_table' in data, "Response missing 'diagnostics_table'"
        
        print(f"✓ GET /api/diagnostic/assignment available")
        print(f"  Summary: {data.get('summary')}")
    
    def test_diagnostic_summary_all_operations_assigned(self):
        """Verify summary shows all operations assigned"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        data = response.json()
        
        summary = data.get('summary', {})
        assert summary.get('total_operations') == 7, f"Expected 7 total operations, got {summary.get('total_operations')}"
        assert summary.get('assigned') == 7, f"Expected 7 assigned, got {summary.get('assigned')}"
        assert summary.get('unassigned') == 0, f"Expected 0 unassigned, got {summary.get('unassigned')}"
        
        print(f"✓ All {summary.get('total_operations')} operations assigned")
    
    def test_diagnostic_has_enriched_fields(self):
        """Verify diagnostic table has article_id, date_besoin, urgency"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        data = response.json()
        
        diag_table = data.get('diagnostics_table', [])
        assert len(diag_table) > 0, "diagnostics_table is empty"
        
        # Check first operation has required fields
        first_diag = diag_table[0]
        required_fields = ['operation_id', 'order_id', 'article_id', 'date_besoin', 'urgency', 
                          'tache_id', 'centre_de_charge_id', 'machine_choisie', 'is_assigned']
        
        for field in required_fields:
            assert field in first_diag, f"Missing field '{field}' in diagnostic"
        
        print(f"✓ Diagnostic table has enriched fields: {list(first_diag.keys())}")
    
    def test_diagnostic_rules_loaded(self):
        """Verify business rules are loaded in diagnostic"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        data = response.json()
        
        rules = data.get('regles_chargees', [])
        assert len(rules) == 3, f"Expected 3 rules, got {len(rules)}"
        
        rule_names = [r.get('name') for r in rules]
        print(f"✓ Rules loaded: {rule_names}")
    
    def test_diagnostic_machines_by_centre(self):
        """Verify machines are indexed by centre_de_charge"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        data = response.json()
        
        machines_par_centre = data.get('machines_par_centre', {})
        
        # Verify PLI01 has PLIEUSE machines
        assert 'PLI01' in machines_par_centre, f"Missing PLI01 in machines index: {machines_par_centre.keys()}"
        pli_machines = [m.get('id') for m in machines_par_centre.get('PLI01', [])]
        assert 'PLIEUSE_01' in pli_machines, f"Missing PLIEUSE_01 in PLI01"
        assert 'PLIEUSE_02' in pli_machines, f"Missing PLIEUSE_02 in PLI01"
        
        print(f"✓ Machines by centre: {dict((k, [m.get('id') for m in v]) for k, v in machines_par_centre.items())}")


class TestForbidRule:
    """
    CRITICAL: FORBID rule test
    OF003_10 (article ART003, tache PLIAGE) must NOT be assigned to PLIEUSE_01
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure demo data is loaded"""
        requests.post(f"{API_URL}/reset-all", timeout=15)
        response = requests.post(f"{API_URL}/demo/load", timeout=15)
        assert response.status_code == 200, "Failed to load demo data"
    
    def test_forbid_rule_exists_in_demo_data(self):
        """Verify FORBID rule for ART003/PLIEUSE_01 exists"""
        response = requests.get(f"{API_URL}/rules", timeout=10)
        rules = response.json()
        
        forbid_rule = next((r for r in rules if r.get('rule_type') == 'FORBID' 
                           and r.get('article_id') == 'ART003' 
                           and r.get('machine_id') == 'PLIEUSE_01'), None)
        
        assert forbid_rule is not None, f"FORBID rule for ART003/PLIEUSE_01 not found in {rules}"
        assert forbid_rule.get('tache_id') == 'PLIAGE', f"Wrong tache_id: {forbid_rule.get('tache_id')}"
        
        print(f"✓ FORBID rule found: {forbid_rule.get('name')}")
        print(f"  article_id={forbid_rule.get('article_id')}, tache_id={forbid_rule.get('tache_id')}, machine_id={forbid_rule.get('machine_id')}")
    
    def test_of003_10_not_assigned_to_plieuse_01(self):
        """CRITICAL: OF003_10 must NOT be assigned to PLIEUSE_01"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        data = response.json()
        
        diag_table = data.get('diagnostics_table', [])
        
        # Find OF003_10 in diagnostic table
        of003_10_diag = next((d for d in diag_table if d.get('operation_id') == 'OF003_10'), None)
        assert of003_10_diag is not None, "OF003_10 not found in diagnostic table"
        
        # Verify it's assigned but NOT to PLIEUSE_01
        assert of003_10_diag.get('is_assigned') == True, "OF003_10 should be assigned"
        machine_choisie = of003_10_diag.get('machine_choisie')
        
        assert machine_choisie != 'PLIEUSE_01', \
            f"CRITICAL FAILURE: OF003_10 assigned to PLIEUSE_01 but FORBID rule should prevent this!"
        
        # Should be assigned to PLIEUSE_02 (alternative machine in PLI01)
        assert machine_choisie == 'PLIEUSE_02', \
            f"OF003_10 should be assigned to PLIEUSE_02, got {machine_choisie}"
        
        # Verify PLIEUSE_01 is in forbidden list
        machines_interdites = of003_10_diag.get('machines_interdites', [])
        assert 'PLIEUSE_01' in machines_interdites, \
            f"PLIEUSE_01 should be in machines_interdites: {machines_interdites}"
        
        print(f"✓ FORBID rule applied correctly:")
        print(f"  OF003_10 (ART003/PLIAGE) assigned to: {machine_choisie}")
        print(f"  Machines interdites: {machines_interdites}")
    
    def test_of003_10_diagnostic_shows_forbid_rule_applied(self):
        """Verify diagnostic shows FORBID rule was applied to OF003_10"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        data = response.json()
        
        diag_table = data.get('diagnostics_table', [])
        of003_10_diag = next((d for d in diag_table if d.get('operation_id') == 'OF003_10'), None)
        
        # Check rule was applied
        regles_applicables = of003_10_diag.get('regles_applicables', [])
        assert any('FORBID' in str(r) for r in regles_applicables), \
            f"No FORBID rule in regles_applicables: {regles_applicables}"
        
        print(f"✓ OF003_10 diagnostic - regles_applicables: {regles_applicables}")


class TestPreferRule:
    """
    PREFER rule test
    USINAGE operations must prefer TOUR_CNC_01
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure demo data is loaded"""
        requests.post(f"{API_URL}/reset-all", timeout=15)
        response = requests.post(f"{API_URL}/demo/load", timeout=15)
        assert response.status_code == 200, "Failed to load demo data"
    
    def test_prefer_rule_exists_for_usinage(self):
        """Verify PREFER rule for USINAGE/TOUR_CNC_01 exists"""
        response = requests.get(f"{API_URL}/rules", timeout=10)
        rules = response.json()
        
        prefer_rule = next((r for r in rules if r.get('rule_type') == 'PREFER' 
                           and r.get('tache_id') == 'USINAGE' 
                           and r.get('machine_id') == 'TOUR_CNC_01'), None)
        
        assert prefer_rule is not None, f"PREFER rule for USINAGE/TOUR_CNC_01 not found in {rules}"
        
        print(f"✓ PREFER rule found: {prefer_rule.get('name')}")
    
    def test_usinage_operations_assigned_to_tour_cnc_01(self):
        """USINAGE operations should be assigned to TOUR_CNC_01 (preferred)"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        data = response.json()
        
        diag_table = data.get('diagnostics_table', [])
        
        # Find all USINAGE operations
        usinage_ops = [d for d in diag_table if d.get('tache_id') == 'USINAGE']
        assert len(usinage_ops) >= 2, f"Expected at least 2 USINAGE operations, got {len(usinage_ops)}"
        
        # All should be assigned to TOUR_CNC_01 (preferred machine)
        for op in usinage_ops:
            machine_choisie = op.get('machine_choisie')
            assert machine_choisie == 'TOUR_CNC_01', \
                f"USINAGE operation {op.get('operation_id')} should prefer TOUR_CNC_01, got {machine_choisie}"
            
            # Verify it's in preferred machines list
            machines_preferees = op.get('machines_preferees', [])
            assert 'TOUR_CNC_01' in machines_preferees, \
                f"TOUR_CNC_01 should be in machines_preferees: {machines_preferees}"
        
        print(f"✓ PREFER rule applied correctly:")
        for op in usinage_ops:
            print(f"  {op.get('operation_id')} -> {op.get('machine_choisie')} (preferred: {op.get('machines_preferees')})")
    
    def test_diagnostic_shows_preferred_count(self):
        """Verify summary shows preferred count > 0"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        data = response.json()
        
        summary = data.get('summary', {})
        preferred_count = summary.get('preferred', 0)
        
        assert preferred_count >= 2, f"Expected at least 2 preferred assignments, got {preferred_count}"
        print(f"✓ Preferred assignments count: {preferred_count}")


class TestDateBesoinSorting:
    """
    Sorting by date_besoin test
    OF003 (date 2026-03-10) must be processed first (most urgent)
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure demo data is loaded"""
        requests.post(f"{API_URL}/reset-all", timeout=15)
        response = requests.post(f"{API_URL}/demo/load", timeout=15)
        assert response.status_code == 200, "Failed to load demo data"
    
    def test_diagnostic_table_sorted_by_date_besoin(self):
        """Verify diagnostic table is sorted by date_besoin (OF003 first)"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        data = response.json()
        
        diag_table = data.get('diagnostics_table', [])
        assert len(diag_table) == 7, f"Expected 7 operations, got {len(diag_table)}"
        
        # First operations should be from OF003 (date 2026-03-10)
        first_op = diag_table[0]
        assert first_op.get('order_id') == 'OF003', \
            f"First operation should be from OF003 (most urgent), got {first_op.get('order_id')}"
        assert first_op.get('date_besoin') == '2026-03-10', \
            f"First date_besoin should be 2026-03-10, got {first_op.get('date_besoin')}"
        
        # Verify order: OF003 -> OF001 -> OF002
        order_sequence = []
        for op in diag_table:
            order_id = op.get('order_id')
            if order_id not in order_sequence:
                order_sequence.append(order_id)
        
        assert order_sequence == ['OF003', 'OF001', 'OF002'], \
            f"Expected order sequence [OF003, OF001, OF002], got {order_sequence}"
        
        print(f"✓ Operations sorted by date_besoin:")
        for op in diag_table[:4]:
            print(f"  {op.get('operation_id')} - order={op.get('order_id')}, date={op.get('date_besoin')}")
    
    def test_of003_marked_as_late_with_high_urgency(self):
        """OF003 operations should have high urgency (en_retard)"""
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        data = response.json()
        
        diag_table = data.get('diagnostics_table', [])
        summary = data.get('summary', {})
        
        # Find OF003 operations
        of003_ops = [d for d in diag_table if d.get('order_id') == 'OF003']
        
        # All OF003 operations should have high urgency (>= 1000 = en retard)
        for op in of003_ops:
            urgency = op.get('urgency', 0)
            assert urgency >= 1000, \
                f"OF003 operation {op.get('operation_id')} should have urgency >= 1000 (en retard), got {urgency}"
        
        # Summary should show en_retard count
        en_retard_count = summary.get('en_retard', 0)
        assert en_retard_count >= 2, \
            f"Expected at least 2 operations en_retard (OF003), got {en_retard_count}"
        
        print(f"✓ OF003 operations marked as late (urgency >= 1000):")
        for op in of003_ops:
            print(f"  {op.get('operation_id')} - urgency={op.get('urgency')}")
        print(f"  Total en_retard: {en_retard_count}")


class TestOrderIdJointure:
    """
    Test that order_id is the join key between operations and orders
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure demo data is loaded"""
        requests.post(f"{API_URL}/reset-all", timeout=15)
        response = requests.post(f"{API_URL}/demo/load", timeout=15)
        assert response.status_code == 200, "Failed to load demo data"
    
    def test_all_operations_have_ordre_trouve(self):
        """All operations should have ordre_trouve=True (join successful)"""
        response = requests.get(f"{API_URL}/operations-enrichies", timeout=10)
        operations = response.json()
        
        for op in operations:
            assert op.get('ordre_trouve') == True, \
                f"Operation {op.get('id')} has ordre_trouve=False - join failed!"
        
        print(f"✓ All {len(operations)} operations have ordre_trouve=True (join successful)")
    
    def test_join_data_propagated_correctly(self):
        """Verify article_id from order is propagated to operation"""
        response = requests.get(f"{API_URL}/operations-enrichies", timeout=10)
        operations = response.json()
        
        # Expected mappings from demo_data.py
        expected_mappings = {
            'OF001': {'article_id': 'ART001', 'date_besoin': '2026-03-18'},
            'OF002': {'article_id': 'ART002', 'date_besoin': '2026-03-25'},
            'OF003': {'article_id': 'ART003', 'date_besoin': '2026-03-10'}
        }
        
        for op in operations:
            order_id = op.get('order_id')
            expected = expected_mappings.get(order_id)
            
            assert expected is not None, f"Unknown order_id: {order_id}"
            assert op.get('article_id') == expected['article_id'], \
                f"Operation {op.get('id')}: expected article_id={expected['article_id']}, got {op.get('article_id')}"
            assert op.get('date_besoin') == expected['date_besoin'], \
                f"Operation {op.get('id')}: expected date_besoin={expected['date_besoin']}, got {op.get('date_besoin')}"
        
        print(f"✓ Join data propagated correctly for all operations")


class TestEndToEndFlow:
    """End-to-end test: reset -> load demo -> assign -> verify"""
    
    def test_complete_flow(self):
        """Test complete flow: reset -> load -> diagnostic"""
        # Step 1: Reset all
        print("\n=== Step 1: Reset all ===")
        response = requests.post(f"{API_URL}/reset-all", timeout=15)
        assert response.status_code == 200, f"Reset failed: {response.text}"
        print(f"  Reset: {response.json().get('message')}")
        
        # Step 2: Load demo data
        print("\n=== Step 2: Load demo data ===")
        response = requests.post(f"{API_URL}/demo/load", timeout=15)
        assert response.status_code == 200, f"Demo load failed: {response.text}"
        print(f"  Demo loaded: {response.json().get('counts')}")
        
        # Step 3: Get diagnostic
        print("\n=== Step 3: Get assignment diagnostic ===")
        response = requests.get(f"{API_URL}/diagnostic/assignment", timeout=15)
        assert response.status_code == 200, f"Diagnostic failed: {response.text}"
        
        data = response.json()
        summary = data.get('summary', {})
        
        print(f"  Total operations: {summary.get('total_operations')}")
        print(f"  Assigned: {summary.get('assigned')}")
        print(f"  Preferred: {summary.get('preferred')}")
        print(f"  En retard: {summary.get('en_retard')}")
        
        # Verify critical business rules
        diag_table = data.get('diagnostics_table', [])
        
        # Verify OF003_10 FORBID rule
        of003_10 = next((d for d in diag_table if d.get('operation_id') == 'OF003_10'), None)
        assert of003_10.get('machine_choisie') == 'PLIEUSE_02', \
            f"FORBID rule failed: OF003_10 assigned to {of003_10.get('machine_choisie')}"
        print(f"\n  ✓ FORBID rule: OF003_10 -> PLIEUSE_02 (not PLIEUSE_01)")
        
        # Verify USINAGE PREFER rule
        usinage_ops = [d for d in diag_table if d.get('tache_id') == 'USINAGE']
        for op in usinage_ops:
            assert op.get('machine_choisie') == 'TOUR_CNC_01', \
                f"PREFER rule failed: {op.get('operation_id')} assigned to {op.get('machine_choisie')}"
        print(f"  ✓ PREFER rule: All USINAGE -> TOUR_CNC_01")
        
        # Verify sorting by date_besoin
        first_order = diag_table[0].get('order_id')
        assert first_order == 'OF003', f"Sorting failed: first should be OF003, got {first_order}"
        print(f"  ✓ Sorting: OF003 (2026-03-10) processed first")
        
        print("\n=== End-to-end test PASSED ===")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
