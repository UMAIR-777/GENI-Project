import pytest
import httpx
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import status

# Load test environment variables
load_dotenv(".env.test")

GENERATOR_API_URL = os.getenv("GENERATOR_API_URL", "http://localhost:8000")
EXECUTOR_API_URL = os.getenv("EXECUTOR_API_URL", "http://localhost:8001")
TEST_TENANT_ID = os.getenv("TEST_TENANT_ID", "test-tenant-id")
TEST_AUTH_TOKEN = os.getenv("TEST_AUTH_TOKEN", "Bearer test-token")
DATABASE_URL = os.getenv("DATABASE_URL")

# Database fixture to reset state
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE workflows RESTART IDENTITY CASCADE"))
        db.execute(
            text("INSERT INTO tenants (id, tenant_nodes_bucket) VALUES (:id, :bucket) ON CONFLICT DO NOTHING"),
            {"id": TEST_TENANT_ID, "bucket": "test-bucket"}
        )
        db.commit()
        yield db
    finally:
        db.close()

@pytest.mark.asyncio
async def test_workflow_generator_to_executor(db_session):
    async with httpx.AsyncClient() as client:
        # Step 1: Generate workflow
        query = "Create a workflow to process customer data"
        generator_response = await client.post(
            f"{GENERATOR_API_URL}/generate_workflow",
            json={"query": query},
            timeout=30.0
        )
        assert generator_response.status_code == status.HTTP_200_OK, f"Generator failed: {generator_response.text}"
        generator_data = generator_response.json()
        assert generator_data["status"] == "success"
        workflow_json = generator_data["workflow"]

        # Step 2: Create workflow
        create_payload = {
            "name": "Test Workflow",
            "data": workflow_json,
            "tenant_id": TEST_TENANT_ID,
            "is_public": False,
            "version": 1
        }
        headers = {"Authorization": TEST_AUTH_TOKEN}
        create_response = await client.post(
            f"{EXECUTOR_API_URL}/",
            json=create_payload,
            headers=headers,
            timeout=30.0
        )
        assert create_response.status_code == status.HTTP_201_CREATED, f"Create failed: {create_response.text}"
        create_data = create_response.json()
        workflow_id = create_data["id"]

        # Step 3: Execute workflow
        execute_payload = {
            "input": {}  # Update with correct input if needed
        }
        execute_response = await client.post(
            f"{EXECUTOR_API_URL}/execute-workflow/{workflow_id}",
            json=execute_payload,
            headers=headers,
            timeout=30.0
        )
        assert execute_response.status_code == status.HTTP_200_OK, f"Execute failed: {execute_response.text}"
        execute_data = execute_response.json()
        assert execute_data["message"] == "Workflow executed successfully"