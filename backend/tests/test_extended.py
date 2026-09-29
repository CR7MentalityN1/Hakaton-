from io import BytesIO
import xlwt
from fastapi import HTTPException
import pytest
from app.services.storage import storage, validate_file
from app.core.config import settings


@pytest.mark.parametrize(
    "kind,payload",
    [
        ("directions", {"name": "Extra direction", "description": "test"}),
        (
            "programs",
            {"name": "Extra program", "direction_id": 1, "description": "test"},
        ),
        (
            "products",
            {"name": "Extra product", "vendor": "Demo", "description": "test"},
        ),
    ],
)
def test_catalog_crud(client, login, kind, payload):
    login(1)
    r = client.post("/api/v1/" + kind, json=payload)
    assert r.status_code == 201, r.text
    path = f"/api/v1/{kind}/{r.json()['id']}"
    assert (
        client.put(
            path, json={**payload, "name": "Changed " + payload["name"]}
        ).status_code
        == 200
    )
    assert client.get(path).json()["name"].startswith("Changed")
    assert client.delete(path).status_code == 200


def test_xls_preview_and_row_rollback(client, login):
    login(1)
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Data")
    for i, row in enumerate(
        [
            ["University", "Product", "Count"],
            ["Good Import", "Good Software", 42],
            ["Bad Import", "Bad Software", -4],
        ]
    ):
        for j, value in enumerate(row):
            ws.write(i, j, value)
    stream = BytesIO()
    wb.save(stream)
    file = ("legacy.xls", stream.getvalue(), "application/vnd.ms-excel")
    assert (
        client.post("/api/v1/import/preview", files={"file": file}).json()["total"] == 2
    )
    result = client.post(
        "/api/v1/import/commit",
        files={"file": file},
        data={
            "mapping": '{"university":"University","product":"Product","students":"Count"}',
            "default_program_id": 1,
            "workflow_id": 1,
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["created"] == 1 and result.json()["skipped"] == 1
    assert (
        client.get("/api/v1/universities", params={"q": "Bad Import"}).json()["total"]
        == 0
    )


def test_cache_invalidation_and_scope(client, login):
    login(1)
    before = client.get("/api/v1/dashboard").json()["interactions"]
    r = client.post(
        "/api/v1/interactions",
        json={
            "university_id": 1,
            "program_id": 1,
            "product_id": 1,
            "workflow_id": 1,
            "responsible_employee_id": 3,
        },
    )
    assert r.status_code == 201, r.text
    assert client.get("/api/v1/dashboard").json()["interactions"] == before + 1
    login(4)
    scoped = client.get("/api/v1/dashboard").json()["interactions"]
    assert scoped < before
    login(1)
    assert client.delete(f"/api/v1/interactions/{r.json()['id']}").status_code == 200


def test_file_size_traversal_and_mime(monkeypatch):
    with pytest.raises(HTTPException):
        storage.path("../../outside.pdf")
    with pytest.raises(HTTPException):
        validate_file(b"%PDF-1.4", "a.pdf", "image/png")
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    with pytest.raises(HTTPException) as exc:
        validate_file(b"%PDF-1.4", "a.pdf", "application/pdf")
    assert exc.value.status_code == 413


def test_unified_404(client):
    response = client.get("/api/v1/unknown-path")
    assert response.status_code == 404
    assert set(response.json()) == {"code", "message", "details"}
