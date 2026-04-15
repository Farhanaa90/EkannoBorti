from django.urls import path
from . import views

urlpatterns = [
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/<int:room_id>/', views.room_detail, name='room_detail'),
    path('rooms/<int:room_id>/request/', views.send_request, name='send_request'),
    path('my_requests/', views.my_requests, name='my_requests'),
    path('seeker/dashboard/', views.seeker_dashboard, name='seeker_dashboard'),
]