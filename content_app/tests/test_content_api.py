import pytest


@pytest.mark.django_db
def test_get_content_items(auth_api, sample_video):
    """List endpoint returns videos for authenticated users."""
    resp = auth_api.get("/content/")
    assert resp.status_code == 200
    data = resp.json()
    assert any(v["title"] == "Test Video" for v in data)


@pytest.mark.django_db
def test_get_single_content_item(auth_api, sample_video):
    """Detail endpoint returns a single video."""
    resp = auth_api.get(f"/content/{sample_video.id}/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == sample_video.id
    assert data["title"] == "Test Video"


@pytest.mark.django_db
def test_get_signed_video_url(auth_api, sample_video, settings):
    """
    Signed URL endpoint returns a mocked presigned S3 URL when S3 is enabled.
    """
    # Force S3 path with presigning
    settings.USE_S3_MEDIA = True
    settings.AWS_S3_QUERYSTRING_AUTH = True
    settings.AWS_STORAGE_BUCKET_NAME = "test-bucket"
    settings.AWS_S3_REGION_NAME = "eu-central-1"
    settings.MEDIA_URL = "/media/"

    resp = auth_api.get(f"/content/video-url/{sample_video.id}/")
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url.startswith("https://mocked-s3-url.com/")
    assert "X-Amz-Signature=fake" in url
