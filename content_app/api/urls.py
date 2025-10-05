from django.urls import path
from .views import GetContentItemsView, GetSingleContentItemView, AddFavoriteVideoView, GetVideoSignedUrlView

urlpatterns = [
    path('', GetContentItemsView.as_view(), name='content'),
    path('<int:pk>/', GetSingleContentItemView.as_view(), name='content-item'),
    path('add-favorite/', AddFavoriteVideoView.as_view(), name='add-favorite'),
    path('video-url/<int:pk>/', GetVideoSignedUrlView.as_view(), name='video-url'),
]
