import pytest


@pytest.mark.django_db
def test_profiles_requires_auth(api):
    resp = api.get("/users/profiles/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_single_profile_requires_auth(api):
    resp = api.get("/users/profile/1/")
    assert resp.status_code in (401, 403)
