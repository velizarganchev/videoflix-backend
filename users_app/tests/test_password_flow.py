import pytest
from django.utils.http import int_to_base36
from rest_framework.authtoken.models import Token


def mock_queue(monkeypatch):
    class Q:
        def __init__(self): self.calls = []
        def enqueue(self, fn, *args, **
                    kwargs): self.calls.append((fn.__name__, args, kwargs))
    q = Q()
    monkeypatch.setattr("users_app.api.views.get_queue", lambda *a, **k: q)
    return q


@pytest.mark.django_db
def test_forgot_password_always_200_and_enqueues_when_user_exists(api, user_active, monkeypatch, settings):
    q = mock_queue(monkeypatch)
    settings.FRONTEND_RESET_PASSWORD_URL = "https://frontend/reset"
    resp = api.post("/users/forgot-password/",
                    {"email": user_active.email}, format="json")
    assert resp.status_code == 200
    assert any(call[0] == "send_email_task" for call in q.calls)


@pytest.mark.django_db
def test_forgot_password_unknown_email_still_200_no_queue(api, monkeypatch):
    q = mock_queue(monkeypatch)
    resp = api.post("/users/forgot-password/",
                    {"email": "nope@example.com"}, format="json")
    assert resp.status_code == 200
    assert len(q.calls) == 0


@pytest.mark.django_db
def test_reset_password_with_valid_token_rotates_token(api, user_active):
    old_token = Token.objects.get(user=user_active).key
    uid = int_to_base36(user_active.id)
    resp = api.post("/users/reset-password/",
                    {"uid": uid, "token": old_token, "new_password": "newpass123"}, format="json")
    assert resp.status_code == 200
    # старият токен е изтрит/ротиран
    assert Token.objects.filter(user=user_active).exists()
    assert Token.objects.get(user=user_active).key != old_token
    # новата парола работи
    login = api.post(
        "/users/login/", {"email": user_active.email, "password": "newpass123"}, format="json")
    assert login.status_code == 200
