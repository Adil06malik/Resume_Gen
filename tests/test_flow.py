import pytest
from httpx import AsyncClient


async def register_and_login(client):
    await client.post("/api/auth/register", json={
        "email": "flow@test.com", "password": "test123", "full_name": "Flow Test",
    })
    login = await client.post("/api/auth/login", data={
        "username": "flow@test.com", "password": "test123",
    })
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_full_auth_flow(client):
    token = await register_and_login(client)
    h = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/auth/me", headers=h)
    assert me.status_code == 200
    assert me.json()["email"] == "flow@test.com"


@pytest.mark.asyncio
async def test_resume_upload_flow(client):
    token = await register_and_login(client)
    h = {"Authorization": f"Bearer {token}"}

    import tempfile, os
    txt_path = tempfile.mktemp(suffix=".txt")
    with open(txt_path, "w") as f:
        f.write("Jane Smith\njane@test.com\nPython, FastAPI\n")

    with open(txt_path, "rb") as f:
        resp = await client.post("/api/resumes/upload", files={"file": ("resume.txt", f, "text/plain")}, headers=h)
    os.remove(txt_path)

    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "resume.txt"
    resume_id = data["id"]

    list_resp = await client.get("/api/resumes/", headers=h)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    detail = await client.get(f"/api/resumes/{resume_id}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["filename"] == "resume.txt"

    del_resp = await client.delete(f"/api/resumes/{resume_id}", headers=h)
    assert del_resp.status_code == 200

    list_after = await client.get("/api/resumes/", headers=h)
    assert len(list_after.json()) == 0


@pytest.mark.asyncio
async def test_job_crud_flow(client):
    token = await register_and_login(client)
    h = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/jobs/", json={
        "title": "Backend Developer",
        "company": "TestCorp",
        "description": "We need a Python developer with FastAPI experience.",
    }, headers=h)
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    list_resp = await client.get("/api/jobs/", headers=h)
    assert len(list_resp.json()) == 1

    detail = await client.get(f"/api/jobs/{job_id}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["title"] == "Backend Developer"

    del_resp = await client.delete(f"/api/jobs/{job_id}", headers=h)
    assert del_resp.status_code == 200

    list_after = await client.get("/api/jobs/", headers=h)
    assert len(list_after.json()) == 0


@pytest.mark.asyncio
async def test_application_create_and_list(client):
    token = await register_and_login(client)
    h = {"Authorization": f"Bearer {token}"}

    import tempfile, os
    txt_path = tempfile.mktemp(suffix=".txt")
    with open(txt_path, "w") as f:
        f.write("Test User\ntest@test.com\nPython\n")
    with open(txt_path, "rb") as f:
        r_resp = await client.post("/api/resumes/upload", files={"file": ("r.txt", f, "text/plain")}, headers=h)
    os.remove(txt_path)
    resume_id = r_resp.json()["id"]

    j_resp = await client.post("/api/jobs/", json={
        "title": "Dev", "company": "Co", "description": "Python dev needed.",
    }, headers=h)
    job_id = j_resp.json()["id"]

    a_resp = await client.post("/api/applications/", json={
        "resume_id": resume_id, "job_id": job_id,
    }, headers=h)
    assert a_resp.status_code == 201
    app_id = a_resp.json()["id"]

    list_resp = await client.get("/api/applications/", headers=h)
    assert len(list_resp.json()) == 1

    detail = await client.get(f"/api/applications/{app_id}", headers=h)
    assert detail.status_code == 200

    status_resp = await client.put(f"/api/applications/{app_id}/status", json={
        "status": "Applied",
    }, headers=h)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "Applied"


@pytest.mark.asyncio
async def test_application_not_own(client):
    token = await register_and_login(client)
    h = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/applications/999", headers=h)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resume_upload_invalid_format(client):
    token = await register_and_login(client)
    h = {"Authorization": f"Bearer {token}"}

    import tempfile, os
    bad_path = tempfile.mktemp(suffix=".xyz")
    with open(bad_path, "wb") as f:
        f.write(b"test content")
    with open(bad_path, "rb") as f:
        resp = await client.post("/api/resumes/upload", files={"file": ("bad.xyz", f, "application/octet-stream")}, headers=h)
    os.remove(bad_path)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_job_delete_nonexistent(client):
    token = await register_and_login(client)
    h = {"Authorization": f"Bearer {token}"}
    resp = await client.delete("/api/jobs/999", headers=h)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resume_delete_nonexistent(client):
    token = await register_and_login(client)
    h = {"Authorization": f"Bearer {token}"}
    resp = await client.delete("/api/resumes/999", headers=h)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_application_history_flow(client):
    token = await register_and_login(client)
    h = {"Authorization": f"Bearer {token}"}

    import tempfile, os
    txt_path = tempfile.mktemp(suffix=".txt")
    with open(txt_path, "w") as f:
        f.write("User\ntest@test.com\nPython\n")
    with open(txt_path, "rb") as f:
        r_resp = await client.post("/api/resumes/upload", files={"file": ("r.txt", f, "text/plain")}, headers=h)
    os.remove(txt_path)
    resume_id = r_resp.json()["id"]

    j_resp = await client.post("/api/jobs/", json={
        "title": "Dev", "company": "Corp", "description": "Python dev.",
    }, headers=h)
    job_id = j_resp.json()["id"]

    await client.post("/api/applications/", json={
        "resume_id": resume_id, "job_id": job_id,
    }, headers=h)

    history = await client.get("/api/applications/history", headers=h)
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["company"] == "Corp"
    assert history.json()[0]["job_title"] == "Dev"
