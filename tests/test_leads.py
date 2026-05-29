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


def test_bulk_create_success_and_failures(client):
    # Prepare payload with a mix of:
    # 0. Successful lead
    # 1. Invalid email format
    # 2. Missing name
    # 3. Another successful lead
    payload = [
        {
            "name": "Bulk Lead A",
            "email": "bulka@example.com",
            "phone": "12345",
            "source": "bulk_import"
        },
        {
            "name": "Invalid Email Lead",
            "email": "not-an-email",
            "phone": "54321"
        },
        {
            "email": "missingname@example.com"
        },
        {
            "name": "Bulk Lead B",
            "email": "bulkb@example.com"
        }
    ]
    response = client.post("/leads/bulk", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 4
    assert data["successful"] == 2
    assert data["failed"] == 2
    
    results = data["results"]
    assert len(results) == 4
    
    # 0. Bulk Lead A (Success)
    assert results[0]["index"] == 0
    assert results[0]["success"] is True
    assert results[0]["lead"]["name"] == "Bulk Lead A"
    assert results[0]["lead"]["email"] == "bulka@example.com"
    assert "id" in results[0]["lead"]
    
    # 1. Invalid Email Lead (Failure)
    assert results[1]["index"] == 1
    assert results[1]["success"] is False
    assert "email" in results[1]["error"]
    
    # 2. Missing name (Failure)
    assert results[2]["index"] == 2
    assert results[2]["success"] is False
    assert "name is required" in results[2]["error"]
    
    # 3. Bulk Lead B (Success)
    assert results[3]["index"] == 3
    assert results[3]["success"] is True
    assert results[3]["lead"]["name"] == "Bulk Lead B"
    assert results[3]["lead"]["email"] == "bulkb@example.com"

    # Test duplicate email in subsequent bulk request
    payload_dup = [
        {
            "name": "Duplicate Email Lead",
            "email": "bulka@example.com"
        }
    ]
    response_dup = client.post("/leads/bulk", json=payload_dup)
    assert response_dup.status_code == 200
    data_dup = response_dup.json()
    assert data_dup["total"] == 1
    assert data_dup["successful"] == 0
    assert data_dup["failed"] == 1
    assert data_dup["results"][0]["success"] is False
    assert data_dup["results"][0]["error"] == "Email already exists"


def test_bulk_update_success_and_failures(client):
    # First, create a couple of leads to update
    c1 = client.post("/leads", json={"name": "Orig A", "email": "origa@example.com"})
    c2 = client.post("/leads", json={"name": "Orig B", "email": "origb@example.com"})
    id_a = c1.json()["id"]
    id_b = c2.json()["id"]
    
    # Prepare payload with a mix of:
    # 0. Successful partial update of Lead A
    # 1. Update with duplicate email constraint violation (using Lead B's email on Lead A)
    # 2. Update of non-existent lead ID
    # 3. Update with validation error (invalid email format)
    # 4. Update with missing id
    payload = [
        {
            "id": id_a,
            "name": "Updated A",
            "phone": "99999"
        },
        {
            "id": id_a,
            "email": "origb@example.com"
        },
        {
            "id": "nonexistent123",
            "name": "No Body"
        },
        {
            "id": id_b,
            "email": "bad-email-format"
        },
        {
            "name": "Missing ID Lead"
        }
    ]
    response = client.put("/leads/bulk", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 5
    assert data["successful"] == 1
    assert data["failed"] == 4
    
    results = data["results"]
    
    # 0. Successful update of Lead A
    assert results[0]["index"] == 0
    assert results[0]["success"] is True
    assert results[0]["lead"]["name"] == "Updated A"
    assert results[0]["lead"]["phone"] == "99999"
    assert results[0]["lead"]["email"] == "origa@example.com"  # Unchanged
    
    # 1. Duplicate email conflict
    assert results[1]["index"] == 1
    assert results[1]["success"] is False
    assert results[1]["error"] == "Email already exists"
    
    # 2. Non-existent lead ID
    assert results[2]["index"] == 2
    assert results[2]["success"] is False
    assert "not found" in results[2]["error"]
    
    # 3. Validation error (bad email)
    assert results[3]["index"] == 3
    assert results[3]["success"] is False
    assert "email" in results[3]["error"]
    
    # 4. Missing id
    assert results[4]["index"] == 4
    assert results[4]["success"] is False
    assert "id is required" in results[4]["error"]
