from __future__ import annotations


def test_auth_login_success(client):
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "admin"
    assert isinstance(body.get("token"), str) and body["token"]


def test_auth_login_rate_limit_blocks_after_five_failures(client):
    for _ in range(4):
        r = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )
        assert r.status_code == 401

    fifth = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    assert fifth.status_code == 429

    blocked_even_with_correct_password = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert blocked_even_with_correct_password.status_code == 429


def _create_teacher(client, headers, *, merge_policy="fill_missing", **payload):
    data = {
        "name": "测试教师",
        "id_card": "110101199001011237",
        "mobile": "13800000001",
        "education": "",
        "extra_fields": {},
    }
    data.update(payload)
    return client.post(
        f"/api/teachers/questionnaire?merge_policy={merge_policy}",
        headers=headers,
        json=data,
    )


def test_teachers_crud_merge_and_tags_flow(client, admin_headers):
    # Create
    created = _create_teacher(client, admin_headers)
    assert created.status_code == 200, created.text
    created_body = created.json()
    assert created_body["action"] == "created"
    teacher_id = created_body["teacher_id"]

    # Read detail
    detail = client.get(f"/api/teachers/{teacher_id}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "测试教师"

    # List
    listed = client.get(
        "/api/teachers/?keyword=测试教师&page=1&page_size=10",
        headers=admin_headers,
    )
    assert listed.status_code == 200
    list_body = listed.json()
    assert list_body["total"] >= 1
    assert any(item["id"] == teacher_id for item in list_body["data"])

    # Update
    updated = client.put(
        f"/api/teachers/{teacher_id}",
        headers=admin_headers,
        json={"mobile": "13800009999", "extra_fields": {"荣誉": "市级优秀教师"}},
    )
    assert updated.status_code == 200
    updated_body = updated.json()
    assert updated_body["mobile"] == "13800009999"
    assert updated_body["extra_fields"].get("荣誉") == "市级优秀教师"

    # Dynamic tag add/remove
    tag_added = client.post(
        f"/api/teachers/{teacher_id}/tags?tag=骨干教师",
        headers=admin_headers,
    )
    assert tag_added.status_code == 200
    assert "骨干教师" in tag_added.json()["tags"]

    tag_removed = client.delete(
        f"/api/teachers/{teacher_id}/tags?tag=骨干教师",
        headers=admin_headers,
    )
    assert tag_removed.status_code == 200
    assert "骨干教师" not in tag_removed.json()["tags"]

    # Merge: fill_missing 不覆盖非空 mobile，只补 education
    fill_missing = _create_teacher(
        client,
        admin_headers,
        merge_policy="fill_missing",
        name="测试教师",
        id_card="110101199001011237",
        mobile="13999999999",
        education="本科",
    )
    assert fill_missing.status_code == 200
    assert fill_missing.json()["action"] == "updated"

    after_fill = client.get(f"/api/teachers/{teacher_id}", headers=admin_headers).json()
    assert after_fill["mobile"] == "13800009999"
    assert after_fill["education"] == "本科"

    # Merge: overwrite 覆盖已有 mobile
    overwrite = _create_teacher(
        client,
        admin_headers,
        merge_policy="overwrite",
        name="测试教师",
        id_card="110101199001011237",
        mobile="13712345678",
    )
    assert overwrite.status_code == 200
    assert overwrite.json()["action"] == "updated"

    after_overwrite = client.get(f"/api/teachers/{teacher_id}", headers=admin_headers).json()
    assert after_overwrite["mobile"] == "13712345678"

    # Merge: skip_existing 命中后不改动
    skipped = _create_teacher(
        client,
        admin_headers,
        merge_policy="skip_existing",
        name="测试教师",
        id_card="110101199001011237",
        mobile="13600000000",
    )
    assert skipped.status_code == 200
    assert skipped.json()["action"] == "skipped"

    after_skip = client.get(f"/api/teachers/{teacher_id}", headers=admin_headers).json()
    assert after_skip["mobile"] == "13712345678"

    # Delete
    deleted = client.delete(f"/api/teachers/{teacher_id}", headers=admin_headers)
    assert deleted.status_code == 200
    not_found = client.get(f"/api/teachers/{teacher_id}", headers=admin_headers)
    assert not_found.status_code == 404
