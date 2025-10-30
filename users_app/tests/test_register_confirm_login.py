import pytest
from django.utils.http import int_to_base36
from rest_framework.authtoken.models import Token

# --- helpers ---


def mock_queue(monkeypatch):
    class Q:
        def __init__(self): self.calls = []
        def enqueue(self, fn, *args, **
                    kwargs): self.calls.append((fn.__name__, args, kwargs))
    q = Q()
    monkeypatch.setattr("users_app.api.views.get_queue", lambda *a, **k: q)
    return q


@pytest.mark.django_db
def test_register_creates_inactive_user_and_enqueues_email(api, User, monkeypatch, settings):
    q = mock_queue(monkeypatch)
    settings.BACKEND_URL = "https://api.example.com"

    payload = {
        "email": "new@example.com",
        "password": "pass1234",
        "confirm_password": "pass1234"
    }
    resp = api.post("/users/register/", payload, format="json")
    assert resp.status_code == 201
    u = User.objects.get(email="new@example.com")
    assert u.is_active is False
    assert Token.objects.filter(user=u).exists()
    # имейл се enqueue-ва
    assert any(call[0] == "send_email_task" for call in q.calls)


@pytest.mark.django_db
def test_confirm_valid_token_activates_and_redirects(api, User, settings):
    settings.FRONTEND_LOGIN_URL = "https://frontend/login"
    u = User.objects.create_user(
        username="c@e.com", email="c@e.com", password="pass1234", is_active=False)
    t = Token.objects.get(user=u)
    uid = int_to_base36(u.id)

    resp = api.get(f"/users/confirm/?uid={uid}&token={t.key}")
    assert resp.status_code in (301, 302)
    u.refresh_from_db()
    assert u.is_active is True
    # нов токен е създаден (старият изтрит)
    assert Token.objects.filter(user=u).exists()


@pytest.mark.django_db
def test_confirm_invalid_token_returns_400(api):
    resp = api.get("/users/confirm/?uid=zzz&token=bad")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_login_success_for_active_user(api, user_active):
    resp = api.post(
        "/users/login/", {"email": "active@example.com", "password": "pass1234"}, format="json")
    assert resp.status_code == 200
    assert "token" in resp.data


@pytest.mark.django_db
def test_login_fails_for_inactive(api, user_inactive):
    resp = api.post(
        "/users/login/", {"email": "inactive@example.com", "password": "pass1234"}, format="json")
    assert resp.status_code == 400
