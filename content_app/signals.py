"""
Video signals — automatic background processing for Videoflix.

This module connects Django signals to RQ tasks for:
- transcoding videos to multiple resolutions,
- generating thumbnails,
- cleaning up files when videos are replaced or deleted.

Signals included:
- post_save     → enqueue conversions + thumbnail generation
- post_delete   → remove original + all renditions + thumbnail
- pre_save      → cleanup old files when video/thumbnail is replaced
"""

import os
import logging

from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
import django_rq

from .models import Video
from .tasks import (
    remove_file_task,
    convert_to_120p,
    convert_to_360p,
    convert_to_720p,
    convert_to_1080p,
    generate_thumbnail_task,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Video)
def video_post_save(sender, instance: Video, created, **kwargs):
    """
    Handle processing after a Video is saved.

    Behavior:
    - If the video is newly created:
        → mark processing_state as "processing"
        → enqueue transcoding tasks for all resolutions.
    - If the video has no thumbnail:
        → enqueue thumbnail generation.

    Notes:
    - Tasks are pushed to the "default" RQ queue.
    - No action is taken if video_file is missing.
    """
    if not instance.video_file:
        return

    try:
        q = django_rq.get_queue("default")
        key = instance.video_file.name

        if created:
            instance.processing_state = Video.STATUS_PROCESSING
            instance.processing_error = ""
            instance.save(
                update_fields=["processing_state", "processing_error"])

            q.enqueue(convert_to_120p, key)
            q.enqueue(convert_to_360p, key)
            q.enqueue(convert_to_720p, key)
            q.enqueue(convert_to_1080p, key)

        if not instance.image_file:
            q.enqueue(generate_thumbnail_task, key)

    except Exception as e:
        logger.exception("post_save enqueue failed: %s", e)


@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance: Video, **kwargs):
    """
    Cleanup tasks after a Video is deleted.

    Actions:
    - Remove original video file.
    - Remove all converted renditions (120p, 360p, 720p, 1080p).
    - Remove thumbnail if it exists.

    All removals are done via RQ tasks (asynchronous).
    """
    try:
        q = django_rq.get_queue("default")

        if instance.video_file:
            base, ext = os.path.splitext(instance.video_file.name)

            q.enqueue(remove_file_task, instance.video_file.name)

            for s in ("120p", "360p", "720p", "1080p"):
                q.enqueue(remove_file_task, f"{base}_{s}{ext}")

        if instance.image_file:
            q.enqueue(remove_file_task, instance.image_file.name)

    except Exception as e:
        logger.exception("post_delete cleanup failed: %s", e)


@receiver(pre_save, sender=Video)
def video_pre_save(sender, instance: Video, **kwargs):
    """
    Cleanup tasks before a Video is saved (update case).

    Behavior:
    - If video_file is changed:
        → delete old original file and all renditions.
    - If image_file (thumbnail) is changed:
        → delete old thumbnail.

    Only runs for existing objects (instance.pk must exist).
    """
    if not instance.pk:
        return

    try:
        old = Video.objects.get(pk=instance.pk)
    except Video.DoesNotExist:
        return

    q = django_rq.get_queue("default")

    if old.video_file and old.video_file != instance.video_file:
        base, ext = os.path.splitext(old.video_file.name)
        q.enqueue(remove_file_task, old.video_file.name)

        for s in ("120p", "360p", "720p", "1080p"):
            q.enqueue(remove_file_task, f"{base}_{s}{ext}")

    if old.image_file and old.image_file != instance.image_file:
        q.enqueue(remove_file_task, old.image_file.name)
