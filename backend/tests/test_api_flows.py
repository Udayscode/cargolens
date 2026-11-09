import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import Base, engine, SessionLocal
from app.models.entities import User, Shipment, Document, ExtractedField, LineItem
from app.core.security import hash_password, create_token

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    # Ensure test users exist
    if not db.query(User).filter_by(email="test_manager@cargolens.demo").first():
        db.add_all([
            User(id="mgr-1", email="test_manager@cargolens.demo", password_hash=hash_password("test-pass"), role="manager"),
            User(id="exec-1", email="test_exec@cargolens.demo", password_hash=hash_password("test-pass"), role="executive")
        ])
        db.commit()
    db.close()


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_auth_login():
    res = client.post("/api/auth/login", json={"email": "test_manager@cargolens.demo", "password": "test-pass"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "manager"


def test_rbac_manager_required_for_approval():
    # Executive token
    exec_token = create_token("exec-1", "executive")
    mgr_token = create_token("mgr-1", "manager")

    db = SessionLocal()
    test_shp = Shipment(reference="SHP-TEST-RBAC", supplier_name="Test Supplier")
    db.add(test_shp)
    db.commit()
    shp_id = test_shp.id
    db.close()

    # Executive attempts to approve -> 403 Forbidden
    res = client.post(f"/api/shipments/{shp_id}/approve", headers={"Authorization": f"Bearer {exec_token}"})
    assert res.status_code == 403

    # Manager attempts to approve -> 200 OK
    res_mgr = client.post(f"/api/shipments/{shp_id}/approve", headers={"Authorization": f"Bearer {mgr_token}"})
    assert res_mgr.status_code == 200
    assert res_mgr.json()["status"] == "approved"


def test_accuracy_report_endpoint():
    mgr_token = create_token("mgr-1", "manager")
    res = client.get("/api/reports/accuracy", headers={"Authorization": f"Bearer {mgr_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "overall_accuracy_percent" in data
    assert "by_field" in data
    assert "by_supplier" in data
