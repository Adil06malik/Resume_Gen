import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_register_user(client):
    resp = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
        "full_name": "Test User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    resp = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    resp = await client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "secret123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    resp = await client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    login_resp = await client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "secret123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_me_no_token(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_resumes_empty(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    login_resp = await client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "secret123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/resumes/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_jobs_empty(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    login_resp = await client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "secret123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/jobs/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_applications_empty(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    login_resp = await client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "secret123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/applications/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_application_no_resume(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    login_resp = await client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "secret123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.post("/api/applications/", json={
        "resume_id": 999,
        "job_id": 999,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_endpoints(client):
    for path in ["/api/resumes/", "/api/jobs/", "/api/applications/"]:
        resp = await client.get(path)
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_download_resume_pdf_no_docs(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com", "password": "secret123",
    })
    login = await client.post("/api/auth/login", data={
        "username": "test@example.com", "password": "secret123",
    })
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/applications/999/resume/pdf", headers=h)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_resume_docx_no_docs(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com", "password": "secret123",
    })
    login = await client.post("/api/auth/login", data={
        "username": "test@example.com", "password": "secret123",
    })
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/applications/999/resume/docx", headers=h)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_cover_letter_pdf_no_docs(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com", "password": "secret123",
    })
    login = await client.post("/api/auth/login", data={
        "username": "test@example.com", "password": "secret123",
    })
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/applications/999/cover-letter/pdf", headers=h)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_documents_no_tailored_resume(client):
    await client.post("/api/auth/register", json={
        "email": "test@example.com", "password": "secret123",
    })
    login = await client.post("/api/auth/login", data={
        "username": "test@example.com", "password": "secret123",
    })
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/applications/999/generate-documents", headers=h)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_endpoints_unauthorized(client):
    for path in [
        "/api/applications/1/resume/pdf",
        "/api/applications/1/resume/docx",
        "/api/applications/1/cover-letter/pdf",
    ]:
        resp = await client.get(path)
        assert resp.status_code == 401
