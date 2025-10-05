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
    delete_original_video_task,  # 👈 neue Task
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    if not (created and instance.video_file):
        return
    try:
        queue = django_rq.get_queue('default')
        key = instance.video_file.name  # << С3 KEY, не .path
        queue.enqueue(convert_to_120p, key)
        queue.enqueue(convert_to_360p, key)
        queue.enqueue(convert_to_720p,  key)
        queue.enqueue(convert_to_1080p, key)
        # по избор:
        # queue.enqueue(delete_original_video_task, key)
    except Exception as e:
        logger.exception("post_save enqueue failed: %s", e)


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.video_file:
        base, ext = os.path.splitext(instance.video_file.name)
        q = django_rq.get_queue('default')
        # трием всички версии в S3
        q.enqueue(remove_file_task, instance.video_file.name)
        for s in ("120p", "360p", "720p", "1080p"):
            q.enqueue(remove_file_task, f"{base}_{s}{ext}")


@receiver(pre_save, sender=Video)
def auto_delete_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Video.objects.get(pk=instance.pk)
    except Video.DoesNotExist:
        return
    if old.video_file and old.video_file != instance.video_file:
        base, ext = os.path.splitext(old.video_file.name)
        q = django_rq.get_queue('default')
        q.enqueue(remove_file_task, old.video_file.name)
        for s in ("120p", "360p", "720p", "1080p"):
            q.enqueue(remove_file_task, f"{base}_{s}{ext}")
