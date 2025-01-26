# Generated by Django 5.1.4 on 2025-01-26 10:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content_app', '0006_alter_video_options_alter_video_category_and_more'),
        ('users_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='favorite_videos',
            field=models.ManyToManyField(blank=True, null=True, related_name='users', to='content_app.video'),
        ),
    ]
