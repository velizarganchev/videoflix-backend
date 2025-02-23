import debug_toolbar
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('django-rq/', include('django_rq.urls')),
    path('api/users/', include('users_app.api.urls')),
    path('api/content/', include('content_app.api.urls')),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
