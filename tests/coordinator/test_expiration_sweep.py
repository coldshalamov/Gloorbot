from __future__ import annotations

import importlib
import sys
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


MODULE_NAMES = [
    "apps.coordinator.coordinator_app.web",
    "apps.coordinator.coordinator_app.seed",
    "apps.coordinator.coordinator_app.models",
    "apps.coordinator.coordinator_app.db",
]


def _reload_coordinator_modules() -> SimpleNamespace:
    for name in MODULE_NAMES:
        sys.modules.pop(name, None)

    db = importlib.import_module("apps.coordinator.coordinator_app.db")
    models = importlib.import_module("apps.coordinator.coordinator_app.models")
    seed = importlib.import_module("apps.coordinator.coordinator_app.seed")
    web = importlib.import_module("apps.coordinator.coordinator_app.web")

    return SimpleNamespace(
        db=importlib.reload(db),
        models=importlib.reload(models),
        seed=importlib.reload(seed),
        web=importlib.reload(web),
    )


@pytest.fixture
def coordinator_env(tmp_path, monkeypatch):
    urls_path = tmp_path / "urls.txt"
    urls_path.write_text(
        "\n".join(
            [
                "https://www.lowes.com/store/WA-smoke-point/0001",
                "https://www.lowes.com/pl/Washers-Appliances/4294857972",
            ]
        ),
        encoding="utf-8",
    )

    db_path = tmp_path / "coordinator.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("LOCAL_URLS_PATH", str(urls_path))
    monkeypatch.setenv(
        "CHEAPSKATER_INGEST_URL",
        "https://cheapskater.example/api/ingest/deals",
    )
    monkeypatch.setenv("CHEAPSKATER_INGEST_API_KEY", "test-api-key")

    env = _reload_coordinator_modules()
    app = env.web.create_app()

    with TestClient(app) as client:
        yield SimpleNamespace(client=client, db=env.db, models=env.models, web=env.web)


def _register_and_lease(env) -> tuple[str, dict]:
    register_resp = env.client.post(
        "/api/v1/client/register",
        json={"hostname": "worker-1", "version": "test"},
    )
    assert register_resp.status_code == 200
    client_id = register_resp.json()["client_id"]

    lease_resp = env.client.post(
        "/api/v1/lease/next",
        json={"client_id": client_id, "preferred_store_id": "0001"},
    )
    assert lease_resp.status_code == 200
    lease_data = lease_resp.json()
    assert lease_data["task_id"]
    return client_id, lease_data


def _task_started_at(env, task_id: int):
    with env.db.db_session() as db:
        task = db.get(env.models.Task, task_id)
        assert task is not None
        assert task.last_started_at is not None
        return task.last_started_at


def _insert_existing_deal(
    env,
    *,
    store_id: str,
    store_name: str,
    category_url: str,
    product_url: str,
    title: str,
    last_seen_at,
) -> None:
    with env.db.db_session() as db:
        db.add(
            env.models.Deal(
                store_id=store_id,
                store_name=store_name,
                category_url=category_url,
                category_name="Washers Appliances",
                product_url=product_url,
                title=title,
                image_url="https://example.com/image.jpg",
                price=90.0,
                was_price=120.0,
                pct_off=0.25,
                first_seen_at=last_seen_at - timedelta(hours=1),
                last_seen_at=last_seen_at,
                seen_count=2,
                last_client_id="seed-client",
            )
        )
        db.add(
            env.models.DealSource(
                store_id=store_id,
                product_url=product_url,
                category_url=category_url,
                first_seen_at=last_seen_at - timedelta(hours=1),
                last_seen_at=last_seen_at,
                seen_count=2,
                last_client_id="seed-client",
                last_batch_id="seed-batch",
                last_task_id=None,
            )
        )
        db.commit()


def _deal_urls(env) -> set[str]:
    with env.db.db_session() as db:
        return {
            row[0]
            for row in db.query(env.models.Deal.product_url).order_by(
                env.models.Deal.product_url
            )
        }


def _deal_source_urls(env) -> set[str]:
    with env.db.db_session() as db:
        return {
            row[0]
            for row in db.query(env.models.DealSource.product_url).order_by(
                env.models.DealSource.product_url
            )
        }


def test_lease_complete_expires_stale_deals_for_completed_task(coordinator_env, monkeypatch):
    env = coordinator_env
    client_id, lease_data = _register_and_lease(env)
    task_started_at = _task_started_at(env, lease_data["task_id"])

    stale_product_url = "https://www.lowes.com/pd/stale-deal/1"
    current_product_url = "https://www.lowes.com/pd/current-deal/2"
    _insert_existing_deal(
        env,
        store_id=lease_data["store_id"],
        store_name=lease_data["store_name"],
        category_url=lease_data["category_url"],
        product_url=stale_product_url,
        title="Stale deal",
        last_seen_at=task_started_at - timedelta(minutes=5),
    )

    monkeypatch.setattr(
        env.web,
        "_forward_deals_to_cheapskater",
        lambda deals, **kwargs: {
            "attempted": True,
            "status_code": 200,
            "accepted": len(deals),
            "error": None,
        },
    )

    expired_calls: list[tuple[list[dict], dict]] = []

    def _fake_expire(expired_deals, **kwargs):
        expired_calls.append((expired_deals, kwargs))
        return {
            "attempted": True,
            "status_code": 200,
            "processed": len(expired_deals),
            "error": None,
        }

    monkeypatch.setattr(env.web, "_forward_expired_deals_to_cheapskater", _fake_expire)

    deals_resp = env.client.post(
        "/api/v1/deals/bulk",
        json={
            "client_id": client_id,
            "batch_id": "batch-1",
            "task_id": lease_data["task_id"],
            "deals": [
                {
                    "store_id": lease_data["store_id"],
                    "store_name": lease_data["store_name"],
                    "category_url": lease_data["category_url"],
                    "product_url": current_product_url,
                    "title": "Current deal",
                    "image_url": "https://example.com/current.jpg",
                    "price": 80.0,
                    "was_price": 120.0,
                    "pct_off": 0.3333,
                    "clearance": False,
                }
            ],
        },
    )
    assert deals_resp.status_code == 200

    complete_resp = env.client.post(
        "/api/v1/lease/complete",
        json={
            "client_id": client_id,
            "task_id": lease_data["task_id"],
            "duration_sec": 12.5,
            "products_seen": 4,
            "deals_sent": 1,
            "scan_status": "complete",
        },
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json() == {"ok": True}

    assert expired_calls == [
        (
            [{"store_id": lease_data["store_id"], "product_url": stale_product_url}],
            {
                "task_id": lease_data["task_id"],
                "client_id": client_id,
                "store_id": lease_data["store_id"],
                "category_url": lease_data["category_url"],
            },
        )
    ]
    assert _deal_urls(env) == {current_product_url}
    assert _deal_source_urls(env) == {current_product_url}


def test_lease_complete_expires_stale_deals_when_empty_scan_is_complete(
    coordinator_env, monkeypatch
):
    env = coordinator_env
    client_id, lease_data = _register_and_lease(env)
    task_started_at = _task_started_at(env, lease_data["task_id"])

    stale_product_url = "https://www.lowes.com/pd/stale-deal/zero-products"
    _insert_existing_deal(
        env,
        store_id=lease_data["store_id"],
        store_name=lease_data["store_name"],
        category_url=lease_data["category_url"],
        product_url=stale_product_url,
        title="Should stay because scrape failed",
        last_seen_at=task_started_at - timedelta(minutes=5),
    )

    expired_calls: list[list[dict]] = []

    def _fake_expire(expired_deals, **kwargs):
        expired_calls.append(expired_deals)
        return {
            "attempted": True,
            "status_code": 200,
            "processed": len(expired_deals),
            "error": None,
        }

    monkeypatch.setattr(env.web, "_forward_expired_deals_to_cheapskater", _fake_expire)

    complete_resp = env.client.post(
        "/api/v1/lease/complete",
        json={
            "client_id": client_id,
            "task_id": lease_data["task_id"],
            "duration_sec": 8.0,
            "products_seen": 0,
            "deals_sent": 0,
            "scan_status": "empty_complete",
        },
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json() == {"ok": True}

    assert expired_calls == [
        [{"store_id": lease_data["store_id"], "product_url": stale_product_url}]
    ]
    assert _deal_urls(env) == set()
    assert _deal_source_urls(env) == set()


def test_lease_complete_skips_expiration_when_scan_is_incomplete(
    coordinator_env, monkeypatch
):
    env = coordinator_env
    client_id, lease_data = _register_and_lease(env)
    task_started_at = _task_started_at(env, lease_data["task_id"])

    stale_product_url = "https://www.lowes.com/pd/stale-deal/incomplete"
    _insert_existing_deal(
        env,
        store_id=lease_data["store_id"],
        store_name=lease_data["store_name"],
        category_url=lease_data["category_url"],
        product_url=stale_product_url,
        title="Should stay because scrape was incomplete",
        last_seen_at=task_started_at - timedelta(minutes=5),
    )

    expire_attempted = False

    def _fake_expire(expired_deals, **kwargs):
        nonlocal expire_attempted
        expire_attempted = True
        return {
            "attempted": True,
            "status_code": 200,
            "processed": len(expired_deals),
            "error": None,
        }

    monkeypatch.setattr(env.web, "_forward_expired_deals_to_cheapskater", _fake_expire)

    complete_resp = env.client.post(
        "/api/v1/lease/complete",
        json={
            "client_id": client_id,
            "task_id": lease_data["task_id"],
            "duration_sec": 8.0,
            "products_seen": 2,
            "deals_sent": 0,
            "scan_status": "incomplete",
        },
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json() == {"ok": True}

    assert expire_attempted is False
    assert _deal_urls(env) == {stale_product_url}
    assert _deal_source_urls(env) == {stale_product_url}


def test_lease_complete_keeps_stale_deals_when_expire_forward_fails(
    coordinator_env, monkeypatch
):
    env = coordinator_env
    client_id, lease_data = _register_and_lease(env)
    task_started_at = _task_started_at(env, lease_data["task_id"])

    stale_product_url = "https://www.lowes.com/pd/stale-deal/forward-fail"
    _insert_existing_deal(
        env,
        store_id=lease_data["store_id"],
        store_name=lease_data["store_name"],
        category_url=lease_data["category_url"],
        product_url=stale_product_url,
        title="Should stay because expire failed",
        last_seen_at=task_started_at - timedelta(minutes=10),
    )

    monkeypatch.setattr(
        env.web,
        "_forward_expired_deals_to_cheapskater",
        lambda expired_deals, **kwargs: {
            "attempted": True,
            "status_code": 502,
            "processed": 0,
            "error": "bad gateway",
        },
    )

    complete_resp = env.client.post(
        "/api/v1/lease/complete",
        json={
            "client_id": client_id,
            "task_id": lease_data["task_id"],
            "duration_sec": 8.0,
            "products_seen": 2,
            "deals_sent": 0,
            "scan_status": "complete",
        },
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json() == {"ok": True}

    assert _deal_urls(env) == {stale_product_url}
