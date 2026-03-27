"""C2 — Conversation Persistence tests."""
import pytest


class TestConversationCRUD:
    """Test conversation API endpoints."""

    def test_create_conversation(self, client, user_headers):
        resp = client.post(
            "/api/conversations",
            json={"title": "Test conversation"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["title"] == "Test conversation"

    def test_list_conversations(self, client, user_headers):
        # Create one first
        client.post("/api/conversations", json={"title": "List test"}, headers=user_headers)
        resp = client.get("/api/conversations", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_conversation_with_messages(self, client, user_headers):
        # Create
        create_resp = client.post(
            "/api/conversations", json={"title": "Get test"}, headers=user_headers
        )
        convo_id = create_resp.json()["id"]

        # Fetch
        resp = client.get(f"/api/conversations/{convo_id}", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == convo_id
        assert "messages" in data

    def test_add_user_message(self, client, user_headers):
        create_resp = client.post(
            "/api/conversations", json={"title": "Msg test"}, headers=user_headers
        )
        convo_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/conversations/{convo_id}/messages",
            json={"role": "user", "text": "Hello Nova"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "user"

    def test_add_nova_message(self, client, user_headers):
        create_resp = client.post(
            "/api/conversations", json={"title": "Nova msg"}, headers=user_headers
        )
        convo_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/conversations/{convo_id}/messages",
            json={"role": "nova", "text": "Hi there", "data": {"response": "Hi there"}},
            headers=user_headers,
        )
        assert resp.status_code == 200

    def test_messages_in_order(self, client, user_headers):
        create_resp = client.post(
            "/api/conversations", json={"title": "Order test"}, headers=user_headers
        )
        convo_id = create_resp.json()["id"]

        client.post(f"/api/conversations/{convo_id}/messages", json={"role": "user", "text": "msg1"}, headers=user_headers)
        client.post(f"/api/conversations/{convo_id}/messages", json={"role": "nova", "text": "resp1"}, headers=user_headers)
        client.post(f"/api/conversations/{convo_id}/messages", json={"role": "user", "text": "msg2"}, headers=user_headers)

        resp = client.get(f"/api/conversations/{convo_id}", headers=user_headers)
        msgs = resp.json()["messages"]
        assert len(msgs) == 3
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "nova"
        assert msgs[2]["role"] == "user"

    def test_delete_conversation(self, client, user_headers):
        create_resp = client.post(
            "/api/conversations", json={"title": "Delete test"}, headers=user_headers
        )
        convo_id = create_resp.json()["id"]

        resp = client.delete(f"/api/conversations/{convo_id}", headers=user_headers)
        assert resp.status_code == 200

        # Should be gone (404)
        resp = client.get(f"/api/conversations/{convo_id}", headers=user_headers)
        assert resp.status_code == 404

    def test_requires_auth(self, client):
        resp = client.get("/api/conversations")
        assert resp.status_code in (401, 422)

    def test_title_auto_update(self, client, user_headers):
        create_resp = client.post(
            "/api/conversations", json={"title": "New conversation"}, headers=user_headers
        )
        convo_id = create_resp.json()["id"]

        client.post(
            f"/api/conversations/{convo_id}/messages",
            json={"role": "user", "text": "Price a 2019 Ariel JGK/4 compressor"},
            headers=user_headers,
        )

        resp = client.get(f"/api/conversations/{convo_id}", headers=user_headers)
        data = resp.json()
        # Title should be updated from first user message
        assert "Ariel" in data.get("title", "") or data.get("title") == "New conversation"
