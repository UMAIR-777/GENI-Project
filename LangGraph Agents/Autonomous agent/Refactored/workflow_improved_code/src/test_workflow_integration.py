import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app  # Your FastAPI app
from database import Base, get_db
from models import Workflow

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  # Use in-memory: "sqlite:///:memory:" for faster tests
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override FastAPI's db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Bind override
app.dependency_overrides[get_db] = override_get_db

# Recreate DB
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def test_generate_and_execute_workflow():
    # Step 1: Generate the workflow
    query = "Analyze customer churn for the last quarter"
    response = client.post("/generate_workflow", json={"query": query})

    assert response.status_code == 200
    resp_data = response.json()
    assert resp_data["status"] == "success"
    generated_workflow = resp_data["workflow"]

    # Step 2: Save workflow to the test DB
    db = TestingSessionLocal()
    try:
        new_workflow = Workflow(
            name="Test Workflow",
            description="Integration test workflow",
            json=json.dumps(generated_workflow)  # Save as JSON string
        )
        db.add(new_workflow)
        db.commit()
        db.refresh(new_workflow)
        workflow_id = new_workflow.id
    finally:
        db.close()

    # Step 3: Execute the workflow using the saved ID
    exec_response = client.post(f"/execute-workflow/{workflow_id}")
    assert exec_response.status_code == 200

    result = exec_response.json()
    assert result["workflow_id"] == workflow_id
    assert result["status"] in ["success", "failed"]
    assert "output" in result
