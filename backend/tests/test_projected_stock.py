"""
Tests for Projected Stock API endpoint - P0 Bug Fix
Tests the /api/projected-stock/{scenario_id} endpoint which should:
1. Return PRODUCTION_RECEIPT events with correct datetime (including transfer time)
2. Distinguish between supplier receipts (RECEIPT) and production receipts (PRODUCTION_RECEIPT)
3. Show proper timeline with chronological events
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SCENARIO_ID = "281f2ed1-b444-4c7b-bc94-34cdd7e2f84f"


class TestProjectedStockEndpoint:
    """Tests for the /api/projected-stock/{scenario_id} endpoint"""
    
    def test_endpoint_returns_200(self):
        """Test that the endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/{SCENARIO_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Endpoint returns 200 OK")
    
    def test_scenario_info_present(self):
        """Test that scenario info is in the response"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/{SCENARIO_ID}")
        data = response.json()
        
        assert 'scenario_id' in data, "Missing scenario_id"
        assert 'scenario_name' in data, "Missing scenario_name"
        assert 'scenario_status' in data, "Missing scenario_status"
        assert 'projected_stock' in data, "Missing projected_stock array"
        assert 'summary' in data, "Missing summary"
        
        print(f"✓ Scenario: {data['scenario_name']} ({data['scenario_status']})")
    
    def test_projected_stock_structure(self):
        """Test that projected_stock items have required fields"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/{SCENARIO_ID}")
        data = response.json()
        
        assert len(data['projected_stock']) > 0, "No projected stock items"
        
        for item in data['projected_stock']:
            assert 'article_id' in item, "Missing article_id"
            assert 'initial_stock' in item, "Missing initial_stock"
            assert 'total_receipts' in item, "Missing total_receipts"
            assert 'total_receipts_supplier' in item, "Missing total_receipts_supplier"
            assert 'total_receipts_production' in item, "Missing total_receipts_production"
            assert 'total_consumptions' in item, "Missing total_consumptions"
            assert 'final_stock' in item, "Missing final_stock"
            assert 'timeline' in item, "Missing timeline"
        
        print(f"✓ All {len(data['projected_stock'])} articles have correct structure")
    
    def test_production_receipt_events_present(self):
        """Test that PRODUCTION_RECEIPT events are in the timeline"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/{SCENARIO_ID}")
        data = response.json()
        
        production_receipts_found = 0
        for item in data['projected_stock']:
            for event in item.get('timeline', []):
                if event.get('type') == 'PRODUCTION_RECEIPT':
                    production_receipts_found += 1
                    # Validate PRODUCTION_RECEIPT event structure
                    assert 'datetime' in event, f"PRODUCTION_RECEIPT missing datetime for {item['article_id']}"
                    assert 'quantity_change' in event, f"PRODUCTION_RECEIPT missing quantity_change"
                    assert 'reference' in event, f"PRODUCTION_RECEIPT missing reference"
                    assert event['quantity_change'] > 0, "PRODUCTION_RECEIPT should have positive quantity"
                    assert 'Fabrication' in event['reference'], f"Reference should mention 'Fabrication', got: {event['reference']}"
        
        assert production_receipts_found > 0, "No PRODUCTION_RECEIPT events found"
        print(f"✓ Found {production_receipts_found} PRODUCTION_RECEIPT events")
    
    def test_art1_has_production_receipt(self):
        """Test that ART1 specifically has a PRODUCTION_RECEIPT event"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/{SCENARIO_ID}")
        data = response.json()
        
        art1 = next((item for item in data['projected_stock'] if item['article_id'] == 'ART1'), None)
        assert art1 is not None, "ART1 not found in projected stock"
        
        # ART1 should have production receipts (from main agent context: 3 productions)
        assert art1['total_receipts_production'] > 0, f"ART1 should have production receipts, got {art1['total_receipts_production']}"
        
        # Check timeline has PRODUCTION_RECEIPT
        production_events = [e for e in art1['timeline'] if e['type'] == 'PRODUCTION_RECEIPT']
        assert len(production_events) > 0, "ART1 should have PRODUCTION_RECEIPT events in timeline"
        
        # Validate the datetime includes transfer time (should be after operation end)
        for event in production_events:
            assert event['datetime'] is not None, "PRODUCTION_RECEIPT datetime should not be None"
            assert 'Fabrication OF' in event['reference'], f"Reference should be 'Fabrication OF xxx', got: {event['reference']}"
        
        print(f"✓ ART1 has {len(production_events)} PRODUCTION_RECEIPT events with correct dates")
    
    def test_summary_fields(self):
        """Test that summary has the required fields"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/{SCENARIO_ID}")
        data = response.json()
        
        summary = data['summary']
        assert 'total_articles' in summary, "Missing total_articles in summary"
        assert 'articles_with_shortage' in summary, "Missing articles_with_shortage"
        assert 'articles_ok' in summary, "Missing articles_ok"
        assert 'total_events' in summary, "Missing total_events"
        
        # Verify totals match
        assert summary['total_articles'] == len(data['projected_stock']), "Total articles mismatch"
        assert summary['articles_ok'] + summary['articles_with_shortage'] == summary['total_articles'], "OK + shortage should equal total"
        
        print(f"✓ Summary: {summary['total_articles']} articles, {summary['articles_ok']} OK, {summary['articles_with_shortage']} with shortage")
    
    def test_receipts_breakdown(self):
        """Test that receipt types are properly separated"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/{SCENARIO_ID}")
        data = response.json()
        
        for item in data['projected_stock']:
            total_receipts = item['total_receipts']
            supplier_receipts = item['total_receipts_supplier']
            production_receipts = item['total_receipts_production']
            
            # Total should be sum of supplier + production
            expected_total = supplier_receipts + production_receipts
            assert abs(total_receipts - expected_total) < 0.01, \
                f"Receipt mismatch for {item['article_id']}: total={total_receipts}, supplier={supplier_receipts}, production={production_receipts}"
        
        print("✓ All receipt breakdowns are correct (supplier + production = total)")
    
    def test_timeline_chronological_order(self):
        """Test that timeline events are in chronological order"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/{SCENARIO_ID}")
        data = response.json()
        
        for item in data['projected_stock']:
            timeline = item.get('timeline', [])
            dated_events = [e for e in timeline if e.get('datetime')]
            
            for i in range(len(dated_events) - 1):
                curr_dt = dated_events[i]['datetime']
                next_dt = dated_events[i + 1]['datetime']
                assert curr_dt <= next_dt, \
                    f"Timeline not chronological for {item['article_id']}: {curr_dt} > {next_dt}"
        
        print("✓ All timelines are in chronological order")
    
    def test_event_types_correct(self):
        """Test that event types are properly categorized"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/{SCENARIO_ID}")
        data = response.json()
        
        valid_types = {'RECEIPT', 'PRODUCTION_RECEIPT', 'CONSUMPTION'}
        
        for item in data['projected_stock']:
            for event in item.get('timeline', []):
                event_type = event.get('type')
                assert event_type in valid_types, f"Invalid event type: {event_type}"
                
                # Verify quantity sign matches event type
                qty = event.get('quantity_change', 0)
                if event_type in ['RECEIPT', 'PRODUCTION_RECEIPT']:
                    assert qty > 0, f"{event_type} should have positive quantity, got {qty}"
                elif event_type == 'CONSUMPTION':
                    assert qty < 0, f"CONSUMPTION should have negative quantity, got {qty}"
        
        print("✓ All event types are valid and have correct quantity signs")
    
    def test_invalid_scenario_returns_404(self):
        """Test that invalid scenario ID returns 404"""
        response = requests.get(f"{BASE_URL}/api/projected-stock/invalid-scenario-id-12345")
        assert response.status_code == 404, f"Expected 404 for invalid scenario, got {response.status_code}"
        print("✓ Invalid scenario returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
