"""
Test CRUD Edit (PUT) endpoints for Machines, Centres de Charge, and Indisponibilités.
Iteration 11: Testing P1 feature - Edit functionality on all 3 pages
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMachinesEdit:
    """Test PUT /api/machines/{machine_id} endpoint"""
    
    def test_get_machines_list(self):
        """Verify machines can be listed"""
        response = requests.get(f"{BASE_URL}/api/machines")
        assert response.status_code == 200
        machines = response.json()
        assert isinstance(machines, list)
        print(f"Found {len(machines)} machines")
        return machines
    
    def test_create_machine_for_edit(self):
        """Create a test machine to edit"""
        test_id = f"TEST_MACHINE_{uuid.uuid4().hex[:6].upper()}"
        
        # First get a centre de charge to link to
        centres_response = requests.get(f"{BASE_URL}/api/centres-de-charge")
        assert centres_response.status_code == 200
        centres = centres_response.json()
        
        if len(centres) == 0:
            pytest.skip("No centres de charge available for test")
        
        centre_id = centres[0]['id']
        
        # Create machine
        payload = {
            "id": test_id,
            "nom": "Test Machine Original",
            "centre_de_charge_id": centre_id,
            "description": "Original description"
        }
        response = requests.post(f"{BASE_URL}/api/machines", json=payload)
        assert response.status_code == 200
        machine = response.json()
        assert machine['id'] == test_id
        print(f"Created test machine: {test_id}")
        return test_id, centre_id
    
    def test_edit_machine_put(self):
        """Test editing a machine via PUT endpoint"""
        # Create machine first
        test_id, centre_id = self.test_create_machine_for_edit()
        
        # Edit via PUT
        update_payload = {
            "nom": "Test Machine Edited",
            "centre_de_charge_id": centre_id,
            "description": "Edited description"
        }
        response = requests.put(f"{BASE_URL}/api/machines/{test_id}", json=update_payload)
        assert response.status_code == 200, f"PUT failed: {response.text}"
        updated = response.json()
        
        # Verify changes
        assert updated.get('nom') == "Test Machine Edited" or updated.get('name') == "Test Machine Edited"
        assert updated.get('description') == "Edited description"
        print(f"Successfully edited machine: {test_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/machines/{test_id}")
    
    def test_edit_nonexistent_machine(self):
        """Test editing a machine that doesn't exist"""
        response = requests.put(f"{BASE_URL}/api/machines/NONEXISTENT_MACHINE", json={"nom": "Test"})
        assert response.status_code == 404
        print("Correctly returned 404 for nonexistent machine")
    
    def test_edit_machine_empty_payload(self):
        """Test editing with empty payload should return 400"""
        # Get an existing machine
        machines = self.test_get_machines_list()
        if len(machines) == 0:
            pytest.skip("No machines to test")
        
        machine_id = machines[0]['id']
        response = requests.put(f"{BASE_URL}/api/machines/{machine_id}", json={})
        assert response.status_code == 400
        print("Correctly returned 400 for empty payload")


class TestCentresDeChargeEdit:
    """Test PUT /api/centres-de-charge/{centre_id} endpoint"""
    
    def test_get_centres_list(self):
        """Verify centres can be listed"""
        response = requests.get(f"{BASE_URL}/api/centres-de-charge")
        assert response.status_code == 200
        centres = response.json()
        assert isinstance(centres, list)
        print(f"Found {len(centres)} centres de charge")
        return centres
    
    def test_create_centre_for_edit(self):
        """Create a test centre to edit"""
        test_id = f"TEST_CDC_{uuid.uuid4().hex[:4].upper()}"
        
        payload = {
            "id": test_id,
            "nom": "Test Centre Original",
            "description": "Original description",
            "calendar_id": None
        }
        response = requests.post(f"{BASE_URL}/api/centres-de-charge", json=payload)
        assert response.status_code == 200
        centre = response.json()
        assert centre['id'] == test_id
        print(f"Created test centre: {test_id}")
        return test_id
    
    def test_edit_centre_put(self):
        """Test editing a centre via PUT endpoint"""
        # Create centre first
        test_id = self.test_create_centre_for_edit()
        
        # Edit via PUT
        update_payload = {
            "nom": "Test Centre Edited",
            "description": "Edited description"
        }
        response = requests.put(f"{BASE_URL}/api/centres-de-charge/{test_id}", json=update_payload)
        assert response.status_code == 200, f"PUT failed: {response.text}"
        result = response.json()
        assert 'message' in result or 'updated' in result
        print(f"Successfully edited centre: {test_id}")
        
        # Verify changes by GET
        get_response = requests.get(f"{BASE_URL}/api/centres-de-charge")
        centres = get_response.json()
        updated_centre = next((c for c in centres if c['id'] == test_id), None)
        assert updated_centre is not None
        assert updated_centre.get('nom') == "Test Centre Edited" or updated_centre.get('name') == "Test Centre Edited"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/centres-de-charge/{test_id}")
    
    def test_edit_centre_calendar_assignment(self):
        """Test assigning a calendar to a centre via PUT"""
        centres = self.test_get_centres_list()
        if len(centres) == 0:
            pytest.skip("No centres available")
        
        # Get calendars
        cal_response = requests.get(f"{BASE_URL}/api/calendars")
        calendars = cal_response.json()
        
        if len(calendars) == 0:
            pytest.skip("No calendars available")
        
        centre_id = centres[0]['id']
        calendar_id = calendars[0]['id']
        
        # Assign calendar
        response = requests.put(
            f"{BASE_URL}/api/centres-de-charge/{centre_id}", 
            json={"calendar_id": calendar_id}
        )
        assert response.status_code == 200
        print(f"Successfully assigned calendar {calendar_id} to centre {centre_id}")
    
    def test_edit_nonexistent_centre(self):
        """Test editing a centre that doesn't exist"""
        response = requests.put(
            f"{BASE_URL}/api/centres-de-charge/NONEXISTENT_CENTRE", 
            json={"nom": "Test"}
        )
        assert response.status_code == 404
        print("Correctly returned 404 for nonexistent centre")


class TestUnavailabilityEdit:
    """Test PUT /api/unavailability/{unavailability_id} endpoint"""
    
    def test_get_unavailability_list(self):
        """Verify unavailabilities can be listed"""
        response = requests.get(f"{BASE_URL}/api/unavailability")
        assert response.status_code == 200
        unavailabilities = response.json()
        assert isinstance(unavailabilities, list)
        print(f"Found {len(unavailabilities)} unavailabilities")
        return unavailabilities
    
    def test_create_unavailability_for_edit(self):
        """Create a test unavailability to edit"""
        # Get a machine first
        machines_response = requests.get(f"{BASE_URL}/api/machines")
        machines = machines_response.json()
        
        if len(machines) == 0:
            pytest.skip("No machines available")
        
        machine_id = machines[0]['id']
        
        payload = {
            "machine_id": machine_id,
            "start_date": "2026-04-01T08:00",
            "end_date": "2026-04-01T17:00",
            "reason": "Test Unavailability Original"
        }
        response = requests.post(f"{BASE_URL}/api/unavailability", json=payload)
        assert response.status_code == 200
        unavail = response.json()
        unavail_id = unavail['id']
        print(f"Created test unavailability: {unavail_id}")
        return unavail_id, machine_id
    
    def test_edit_unavailability_put(self):
        """Test editing an unavailability via PUT endpoint"""
        # Create unavailability first
        unavail_id, machine_id = self.test_create_unavailability_for_edit()
        
        # Edit via PUT
        update_payload = {
            "machine_id": machine_id,
            "start_date": "2026-04-02T09:00",
            "end_date": "2026-04-02T18:00",
            "reason": "Test Unavailability Edited"
        }
        response = requests.put(f"{BASE_URL}/api/unavailability/{unavail_id}", json=update_payload)
        assert response.status_code == 200, f"PUT failed: {response.text}"
        updated = response.json()
        
        # Verify changes
        assert updated.get('reason') == "Test Unavailability Edited"
        assert "2026-04-02" in updated.get('start_date', '')
        print(f"Successfully edited unavailability: {unavail_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/unavailability/{unavail_id}")
    
    def test_edit_unavailability_reason_only(self):
        """Test editing only the reason field"""
        unavail_id, machine_id = self.test_create_unavailability_for_edit()
        
        # Edit only reason
        update_payload = {"reason": "Only Reason Changed"}
        response = requests.put(f"{BASE_URL}/api/unavailability/{unavail_id}", json=update_payload)
        assert response.status_code == 200
        updated = response.json()
        assert updated.get('reason') == "Only Reason Changed"
        print(f"Successfully edited reason only for: {unavail_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/unavailability/{unavail_id}")
    
    def test_edit_nonexistent_unavailability(self):
        """Test editing an unavailability that doesn't exist"""
        response = requests.put(
            f"{BASE_URL}/api/unavailability/nonexistent-id-12345", 
            json={"reason": "Test"}
        )
        assert response.status_code == 404
        print("Correctly returned 404 for nonexistent unavailability")


class TestExistingDataEdit:
    """Test editing existing data without creating new records"""
    
    def test_edit_existing_machine(self):
        """Test editing one of the existing machines if available"""
        response = requests.get(f"{BASE_URL}/api/machines")
        machines = response.json()
        
        if len(machines) == 0:
            pytest.skip("No existing machines")
        
        # Find ROBOT3 or any machine
        machine = next((m for m in machines if m['id'] == 'ROBOT3'), machines[0])
        original_name = machine.get('nom') or machine.get('name')
        
        # Edit with same name (no change check)
        response = requests.put(
            f"{BASE_URL}/api/machines/{machine['id']}", 
            json={"nom": original_name, "description": "Updated via test"}
        )
        assert response.status_code == 200
        print(f"Successfully updated machine {machine['id']}")
    
    def test_edit_existing_centre(self):
        """Test editing one of the existing centres if available"""
        response = requests.get(f"{BASE_URL}/api/centres-de-charge")
        centres = response.json()
        
        if len(centres) == 0:
            pytest.skip("No existing centres")
        
        centre = centres[0]
        
        # Edit description only
        response = requests.put(
            f"{BASE_URL}/api/centres-de-charge/{centre['id']}", 
            json={"description": "Updated description via test"}
        )
        assert response.status_code == 200
        print(f"Successfully updated centre {centre['id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
