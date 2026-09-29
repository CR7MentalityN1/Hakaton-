from io import BytesIO
import json
import openpyxl
import xlrd

API = "/api/v1"


def test_auth_and_errors(client):
    assert client.get(API + "/universities").status_code == 401
    r = client.get(API + "/universities", headers={"Authorization": "Bearer invalid"})
    assert r.status_code == 401
    assert set(r.json()) == {"code", "message", "details"}
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/health").status_code == 200


def test_crud_and_roles(client, login):
    login(3)
    assert (
        client.post(
            API + "/universities", json={"name": "Denied", "city": "X"}
        ).status_code
        == 403
    )
    assert client.get(API + "/audit").status_code == 403
    assert client.get(API + "/universities/2").status_code == 404
    assert client.get(API + "/universities").json()["total"] == 3
    login(2)
    assert client.get(API + "/universities").json()["total"] == 15
    login(1)
    r = client.post(
        API + "/universities",
        json={
            "name": "Test university",
            "city": "Test",
            "short_name": "TU",
            "region": "Region",
        },
    )
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    assert (
        client.put(
            f"{API}/universities/{uid}",
            json={"name": "Renamed university", "city": "New City"},
        ).status_code
        == 200
    )
    assert (
        client.get(API + "/universities", params={"q": "Renamed"}).json()["total"] == 1
    )
    assert client.delete(f"{API}/universities/{uid}").status_code == 200
    assert client.get(f"{API}/universities/{uid}").status_code == 404


def new_interaction(client):
    r = client.post(
        API + "/interactions",
        json={
            "university_id": 1,
            "program_id": 1,
            "product_id": 1,
            "workflow_id": 1,
            "responsible_employee_id": 3,
            "contract_number": "TEST-42",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_interaction_workflow_comments_files(client, login):
    login(3)
    item = new_interaction(client)
    path = f"{API}/interactions/{item['id']}"
    assert (
        client.post(
            path + "/transition", json={"to_stage_id": 14, "version": item["version"]}
        ).status_code
        == 403
    )
    target = client.get(path + "/allowed-stages").json()[0]["id"]
    r = client.post(
        path + "/transition",
        json={"to_stage_id": target, "version": item["version"], "comment": "Done"},
    )
    assert r.status_code == 200, r.text
    assert (
        client.post(
            path + "/transition", json={"to_stage_id": 3, "version": item["version"]}
        ).status_code
        == 409
    )
    assert (
        client.post(
            path + "/comments", json={"stage_id": target, "text": "Hello"}
        ).status_code
        == 201
    )
    assert client.get(path + "/comments").json()[0]["text"] == "Hello"
    timeline = client.get(path + "/timeline").json()
    assert any(t["comment"] == "Done" and t["changed_by"] == 3 for t in timeline)
    content = b"%PDF-1.4\nDemo file\n%%EOF"
    r = client.post(
        path + "/attachments",
        data={"stage_id": target},
        files={"file": ("test.pdf", content, "application/pdf")},
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    assert client.get(f"{API}/attachments/{aid}/download").content == content
    assert (
        client.post(
            path + "/attachments",
            data={"stage_id": target},
            files={"file": ("bad.pdf", b"executable", "application/pdf")},
        ).status_code
        == 415
    )
    login(4)
    assert client.get(path).status_code == 404
    assert client.get(f"{API}/attachments/{aid}/download").status_code == 404


def test_reports_filters_dashboard(client, login):
    login(1)
    r = client.get(API + "/interactions", params={"university_id": 2, "page_size": 1})
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1 and r.json()["total"] == 3
    d = client.get(API + "/dashboard", params={"university_id": 2})
    assert d.status_code == 200, d.text
    assert d.json()["interactions"] == 3
    assert sum(i["value"] for i in d.json()["by_product"]) == 3
    assert (
        client.get(
            API + "/interactions", params={"start": "2026-12-31", "end": "2026-01-01"}
        ).status_code
        == 422
    )
    payload = {
        "university_id": 2,
        "columns": ["university", "program", "contract_number"],
    }
    p = client.post(API + "/reports/preview", json=payload)
    assert p.status_code == 200, p.text
    assert p.json()["total"] == 3
    for fmt in ["xlsx", "xls", "pdf", "json"]:
        r = client.post(API + "/reports/export", json={**payload, "format": fmt})
        assert r.status_code == 200, r.text
        if fmt == "xlsx":
            assert openpyxl.load_workbook(BytesIO(r.content)).active.max_row == 4
        elif fmt == "xls":
            assert (
                xlrd.open_workbook(file_contents=r.content).sheet_by_index(0).nrows == 4
            )
        elif fmt == "pdf":
            assert r.content.startswith(b"%PDF")
        else:
            assert len(r.json()) == 3


def test_import_and_idempotent_integration(client, login):
    login(1)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["University", "Product", "Program", "Contract"])
    ws.append(["Import University", "Test product", "Test program", "IMPORT-1"])
    buffer = BytesIO()
    wb.save(buffer)
    file = (
        "input.xlsx",
        buffer.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    p = client.post(API + "/import/preview", files={"file": file})
    assert p.status_code == 200, p.text
    assert p.json()["headers"] == ["University", "Product", "Program", "Contract"]
    data = {
        "mapping": json.dumps(
            {
                "university": "University",
                "product": "Product",
                "program": "Program",
                "contract_number": "Contract",
            }
        ),
        "workflow_id": 1,
    }
    r = client.post(API + "/import/commit", data=data, files={"file": file})
    assert r.status_code == 200, r.text
    assert r.json()["created"] == 1, r.text
    again = client.post(API + "/import/commit", data=data, files={"file": file})
    assert again.json()["skipped"] == 1, again.text
    for source in ["lms", "website"]:
        r = client.post(f"{API}/integrations/{source}/sync")
        assert r.status_code == 200 and r.json()["created"] == 1, r.text
        r = client.post(f"{API}/integrations/{source}/sync")
        assert r.json()["skipped"] == 1, r.text


def test_workflow_editor_and_audit(client, login):
    login(1)
    payload = {
        "name": "Custom workflow",
        "stages": [
            {"name": "First", "order_index": 0},
            {"name": "Second", "order_index": 1},
        ],
    }
    r = client.post(API + "/workflows", json=payload)
    assert r.status_code == 201, r.text
    w = r.json()
    payload = {k: w[k] for k in ["name", "description", "active", "version", "stages"]}
    for stage in payload["stages"]:
        stage.pop("workflow_id")
    payload["stages"][0]["name"] = "Renamed"
    r = client.put(f"{API}/workflows/{w['id']}", json=payload)
    assert r.status_code == 200, r.text
    assert client.put(f"{API}/workflows/{w['id']}", json=payload).status_code == 409
    assert client.get(API + "/audit").json()["total"] > 0
