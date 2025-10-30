"""
content_app.signals — Video model signal handlers for Videoflix

Purpose:
--------
- On create: enqueue background conversions to multiple resolutions.
- On delete: enqueue removal of the source file and all derived renditions.
- On update (video_file changed): enqueue cleanup of old source and renditions.

Notes:
- Uses django-rq to offload heavy work (transcode / delete) to background workers.
- All storage paths refer to the storage key (S3 key or FileSystem key), not local paths.
"""

import os
import logging
from django.db import transaction
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
import django_rq

from .models import Video
from .tasks import (
    remove_file_task,
    convert_to_120p,
    convert_to_360p,
    convert_to_720p,
    convert_to_1080p,
    # optional task to remove the original source after renditions
    delete_original_video_task,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    """
    After a new Video is created, enqueue transcoding tasks for all target qualities.

    Enqueues:
        convert_to_120p / 360p / 720p / 1080p with the storage key.

    Guard:
        Runs only on initial create and if video_file is present.
    """
    if not (created and instance.video_file):
        return
    try:
        queue = django_rq.get_queue("default")
        # storage key (e.g., S3 key), not a local .path
        key = instance.video_file.name
        queue.enqueue(convert_to_120p, key)
        queue.enqueue(convert_to_360p, key)
        queue.enqueue(convert_to_720p, key)
        queue.enqueue(convert_to_1080p, key)
        # Optional: remove the original after all conversions are available
        # queue.enqueue(delete_original_video_task, key)
    except Exception as e:
        logger.exception("post_save enqueue failed: %s", e)


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    When a Video is deleted, enqueue deletion of the source and all rendition keys.
    """
    if instance.video_file:
        base, ext = os.path.splitext(instance.video_file.name)
        q = django_rq.get_queue("default")
        # Remove the original
        q.enqueue(remove_file_task, instance.video_file.name)
        # Remove derived resolutions
        for s in ("120p", "360p", "720p", "1080p"):
            q.enqueue(remove_file_task, f"{base}_{s}{ext}")


@receiver(pre_save, sender=Video)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Before saving updates, if video_file is being replaced, enqueue cleanup
    for the old source and all of its renditions.
    """
    if not instance.pk:
        return
    try:
        old = Video.objects.get(pk=instance.pk)
    except Video.DoesNotExist:
        return

    if old.video_file and old.video_file != instance.video_file:
        base, ext = os.path.splitext(old.video_file.name)
        q = django_rq.get_queue("default")
        # Remove old original
        q.enqueue(remove_file_task, old.video_file.name)
        # Remove old derived resolutions
        for s in ("120p", "360p", "720p", "1080p"):
            q.enqueue(remove_file_task, f"{base}_{s}{ext}")
