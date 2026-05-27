from app.models import LeadStatus


def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "docs_url" in response.json()


def test_create_lead_success(client):
    payload = {
        "name": "Aman Gupta",
        "email": "aman@example.com",
        "phone": "+91-9876543210",
        "source": "website",
    }
    response = client.post("/leads", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert "id" in data
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert data["phone"] == payload["phone"]
    assert data["status"] == "NEW"  # Default status must be NEW
    assert data["source"] == payload["source"]
    assert "created_at" in data
    assert "updated_at" in data


def test_create_lead_validation_errors(client):
    # Missing required name and email
    response = client.post("/leads", json={})
    assert response.status_code == 422
    
    # Missing name
    response = client.post("/leads", json={"email": "test@example.com"})
    assert response.status_code == 422
    
    # Invalid email format
    response = client.post("/leads", json={"name": "Test", "email": "not-an-email"})
    assert response.status_code == 422


def test_get_all_leads_and_filtering(client):
    # Create a couple of leads
    client.post("/leads", json={"name": "Lead One", "email": "one@example.com"})
    client.post("/leads", json={"name": "Lead Two", "email": "two@example.com"})
    
    # Get all
    response = client.get("/leads")
    assert response.status_code == 200
    leads = response.json()
    assert len(leads) >= 2
    
    # Filter by NEW
    response = client.get("/leads?status=NEW")
    assert response.status_code == 200
    leads_new = response.json()
    assert all(lead["status"] == "NEW" for lead in leads_new)
    
    # Filter by CONVERTED (none should be converted yet)
    response = client.get("/leads?status=CONVERTED")
    assert response.status_code == 200
    leads_converted = response.json()
    assert len(leads_converted) == 0
    
    # Filter by invalid status enum
    response = client.get("/leads?status=INVALID_STATUS")
    assert response.status_code == 422


def test_get_lead_by_id(client):
    # Create a lead
    create_response = client.post("/leads", json={"name": "John Doe", "email": "john@example.com"})
    lead_id = create_response.json()["id"]
    
    # Get by ID
    response = client.get(f"/leads/{lead_id}")
    assert response.status_code == 200
    assert response.json()["id"] == lead_id
    assert response.json()["name"] == "John Doe"
    
    # Non-existent ID
    response = client.get("/leads/nonexistent123")
    assert response.status_code == 404


def test_update_lead_put(client):
    # Create a lead
    create_response = client.post("/leads", json={"name": "John Doe", "email": "john@example.com"})
    lead_id = create_response.json()["id"]
    
    # Update lead
    update_payload = {
        "name": "Johnathan Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-0199",
        "source": "referral",
        "status": "CONVERTED"  # This status field should be ignored in PUT schema or not impact status
    }
    response = client.put(f"/leads/{lead_id}", json=update_payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "Johnathan Doe"
    assert data["email"] == "john.doe@example.com"
    assert data["phone"] == "+1-555-0199"
    assert data["source"] == "referral"
    # Crucial rule: status changes must happen only via PATCH, PUT must not modify it
    assert data["status"] == "NEW"
    
    # Non-existent ID update
    response = client.put("/leads/nonexistent123", json=update_payload)
    assert response.status_code == 404


def test_delete_lead(client):
    # Create a lead
    create_response = client.post("/leads", json={"name": "To Delete", "email": "delete@example.com"})
    lead_id = create_response.json()["id"]
    
    # Delete lead
    response = client.delete(f"/leads/{lead_id}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    
    # Confirm deletion (should return 404 now)
    response = client.get(f"/leads/{lead_id}")
    assert response.status_code == 404
    
    # Deleting non-existent ID
    response = client.delete("/leads/nonexistent123")
    assert response.status_code == 404


def test_valid_status_transitions(client):
    # Create lead (starts at NEW)
    create_response = client.post("/leads", json={"name": "Sales Target", "email": "target@example.com"})
    lead_id = create_response.json()["id"]
    
    # NEW -> CONTACTED
    response = client.patch(f"/leads/{lead_id}/status", json={"status": "CONTACTED"})
    assert response.status_code == 200
    assert response.json()["status"] == "CONTACTED"
    
    # CONTACTED -> QUALIFIED
    response = client.patch(f"/leads/{lead_id}/status", json={"status": "QUALIFIED"})
    assert response.status_code == 200
    assert response.json()["status"] == "QUALIFIED"
    
    # QUALIFIED -> CONVERTED (Terminal)
    response = client.patch(f"/leads/{lead_id}/status", json={"status": "CONVERTED"})
    assert response.status_code == 200
    assert response.json()["status"] == "CONVERTED"


def test_transition_to_lost_and_terminal_states(client):
    # Create a lead (starts at NEW)
    create_response = client.post("/leads", json={"name": "Sales Target 2", "email": "target2@example.com"})
    lead_id = create_response.json()["id"]
    
    # NEW -> LOST
    response = client.patch(f"/leads/{lead_id}/status", json={"status": "LOST"})
    assert response.status_code == 200
    assert response.json()["status"] == "LOST"
    
    # LOST is terminal, cannot transition to NEW (HTTP 400)
    response = client.patch(f"/leads/{lead_id}/status", json={"status": "NEW"})
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid status transition from LOST to NEW"


def test_invalid_status_transitions(client):
    # Create lead (starts at NEW)
    create_response = client.post("/leads", json={"name": "Sales Target 3", "email": "target3@example.com"})
    lead_id = create_response.json()["id"]
    
    # NEW -> CONVERTED (Invalid, can only move forward one step at a time)
    response = client.patch(f"/leads/{lead_id}/status", json={"status": "CONVERTED"})
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid status transition from NEW to CONVERTED"
    
    # NEW -> CONTACTED (Valid)
    client.patch(f"/leads/{lead_id}/status", json={"status": "CONTACTED"})
    
    # CONTACTED -> CONVERTED (Invalid, can only move forward one step at a time)
    response = client.patch(f"/leads/{lead_id}/status", json={"status": "CONVERTED"})
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid status transition from CONTACTED to CONVERTED"
    
    # CONTACTED -> QUALIFIED (Valid)
    client.patch(f"/leads/{lead_id}/status", json={"status": "QUALIFIED"})
    
    # QUALIFIED -> CONVERTED (Valid)
    client.patch(f"/leads/{lead_id}/status", json={"status": "CONVERTED"})
    
    # CONVERTED -> LOST (Invalid, CONVERTED is terminal)
    response = client.patch(f"/leads/{lead_id}/status", json={"status": "LOST"})
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid status transition from CONVERTED to LOST"
