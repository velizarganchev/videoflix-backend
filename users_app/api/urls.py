from django.urls import path
from .views import GetUserProfilesView, GetSingleUserProfileView, UserRegisterView, UserConfirmationView, UserLoginView, UserLogoutView, UserForgotPasswordView, UserResetPasswordView, UserResetPasswordView

urlpatterns = [
    path('profiles/', GetUserProfilesView.as_view(), name='profiles'),
    path('profile/<int:pk>/', GetSingleUserProfileView.as_view(), name='profile'),
    path('register/', UserRegisterView.as_view(), name='register'),
    path('confirm/<str:uid>/<str:token>/',
         UserConfirmationView.as_view(), name='user-confirmation'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('forgot-password/', UserForgotPasswordView.as_view(),
         name='forgot-password'),
    path('reset-password/<str:uid>/<str:token>/',
         UserResetPasswordView.as_view(), name='reset-password'),
]
