def _create(client, **overrides):
    payload = {"title": "buy milk", "description": "2 percent", "status": "pending"}
    payload.update(overrides)
    res = client.post("/tasks", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def test_create_task(client):
    body = _create(client)
    assert body["id"]
    assert body["title"] == "buy milk"
    assert body["status"] == "pending"
    assert body["attachment_key"] is None


def test_create_rejects_empty_title(client):
    res = client.post("/tasks", json={"title": "", "status": "pending"})
    assert res.status_code == 422


def test_list_tasks(client):
    _create(client, title="a")
    _create(client, title="b")
    res = client.get("/tasks")
    assert res.status_code == 200
    items = res.json()
    titles = {t["title"] for t in items}
    assert {"a", "b"}.issubset(titles)


def test_get_task(client):
    created = _create(client)
    res = client.get(f"/tasks/{created['id']}")
    assert res.status_code == 200
    assert res.json()["id"] == created["id"]


def test_get_task_not_found(client):
    res = client.get("/tasks/does-not-exist")
    assert res.status_code == 404


def test_update_task(client):
    created = _create(client)
    res = client.put(
        f"/tasks/{created['id']}",
        json={"status": "in_progress", "title": "new title"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "in_progress"
    assert body["title"] == "new title"


def test_update_task_partial(client):
    created = _create(client)
    res = client.put(f"/tasks/{created['id']}", json={"status": "done"})
    assert res.status_code == 200
    assert res.json()["status"] == "done"
    assert res.json()["title"] == created["title"]


def test_update_task_not_found(client):
    res = client.put("/tasks/missing", json={"status": "done"})
    assert res.status_code == 404


def test_delete_task(client):
    created = _create(client)
    res = client.delete(f"/tasks/{created['id']}")
    assert res.status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404


def test_delete_task_not_found(client):
    res = client.delete("/tasks/missing")
    assert res.status_code == 404


def test_attachment_disabled_returns_503(client):
    created = _create(client)
    res = client.post(
        f"/tasks/{created['id']}/attachment",
        files={"file": ("note.txt", b"hello world", "text/plain")},
    )
    assert res.status_code == 503
