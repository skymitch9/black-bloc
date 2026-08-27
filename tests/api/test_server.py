from fastapi.testclient import TestClient

from black_bloc.api.server import create_app


class _FakeBot:
    guilds: list = []
    latency = 0.042

    def is_ready(self):
        return True


def test_health():
    client = TestClient(create_app(_FakeBot()))
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["ready"] is True
    assert body["latency_ms"] == 42
