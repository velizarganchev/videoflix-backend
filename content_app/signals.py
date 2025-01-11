import os
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Video
from django.conf import settings
from .tasks import convert_to_120p, convert_to_360p, convert_to_720p, convert_to_1080p


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    if created:
        # Get the base name of the video file
        video_file_name = os.path.basename(instance.video_file.name)
        base_name = os.path.splitext(video_file_name)[0]

        # Define relative paths for the converted files
        relative_paths = [
            f'media/videos/{base_name}_120p.mp4',
            f'media/videos/{base_name}_360p.mp4',
            f'media/videos/{base_name}_720p.mp4',
            f'media/videos/{base_name}_1080p.mp4'
        ]

        # Perform conversion and save converted files
        for path in relative_paths:
            resolution = os.path.splitext(path)[0].split('_')[-1]
            if resolution == '120p':
                convert_to_120p(instance.video_file.path)
            elif resolution == '360p':
                convert_to_360p(instance.video_file.path)
            elif resolution == '720p':
                convert_to_720p(instance.video_file.path)
            elif resolution == '1080p':
                convert_to_1080p(instance.video_file.path)

        # Save the relative paths to the model
        instance.converted_files = relative_paths
        instance.save()

        # Remove the original file if necessary
        try:
            if instance.video_file and os.path.isfile(instance.video_file.path):
                os.remove(instance.video_file.path)
        except Exception as e:
            print(f"Error deleting original file: {e}")


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes all associated files from the filesystem
    when the corresponding `Video` object is deleted.
    """
    # Helper function to remove a file safely
    def remove_file(file_path):
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

    # Remove the original video file
    if instance.video_file:
        remove_file(instance.video_file.path)

    # Remove the converted video files
    if instance.video_file:
        base_path_videos, ext = os.path.splitext(instance.video_file.path)
        converted_video_files = [
            f"{base_path_videos}_120p{ext}",
            f"{base_path_videos}_360p{ext}",
            f"{base_path_videos}_720p{ext}",
            f"{base_path_videos}_1080p{ext}",
        ]
        for file_path in converted_video_files:
            remove_file(file_path)

    # Remove the associated image file and its variants if applicable
    if instance.image_file:
        remove_file(instance.image_file.path)


@receiver(pre_save, sender=Video)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes old file from filesystem
    when corresponding `Video` object is updated
    with new file.
    """
    if not instance.pk:
        return

    try:
        old_file = Video.objects.get(pk=instance.pk).video_file
    except Video.DoesNotExist:
        return

    new_file = instance.video_file
    if old_file and old_file != new_file:
        try:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)
        except Exception as e:
            print(f"Error deleting old file: {e}")
