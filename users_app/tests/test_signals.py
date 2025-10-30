import pytest
from rest_framework.authtoken.models import Token


@pytest.mark.django_db
def test_token_created_by_signal(User):
    u = User.objects.create_user(
        username="x@e.com", email="x@e.com", password="pass1234")
    assert Token.objects.filter(user=u).exists()
