from django.urls import path
from .views import GetContentItemsView, GetSingleContentItemView

urlpatterns = [
    path('', GetContentItemsView.as_view(), name='content'),
    path('<int:pk>/', GetSingleContentItemView.as_view(), name='content-item'),
]
