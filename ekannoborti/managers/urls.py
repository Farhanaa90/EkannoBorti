from django.urls import path
from . import views

urlpatterns = [
    path('managers/dashboard/', views.dashboard, name='manager_dashboard'),
    path('managers/create-mess/', views.create_mess, name='create_mess'),
    path('managers/members/', views.manage_members, name='manage_members'),
    path('managers/members/<int:member_id>/remove/', views.remove_member, name='remove_member'),
    path('managers/members/<int:member_id>/profile/', views.view_member_profile, name='view_member_profile'),
    path('managers/meal-rate/', views.set_meal_rate, name='set_meal_rate'),
    path('managers/expense/', views.add_expense, name='add_expense'),
    path('managers/deposit/', views.record_deposit, name='record_deposit'),
    path('managers/post-room/', views.post_room, name='post_room'),
    path('managers/post-room/<int:room_id>/delete/', views.delete_room, name='delete_room'),
    path('managers/post-room/<int:room_id>/toggle/', views.toggle_room, name='toggle_room'),
    path('managers/room-requests/', views.room_requests, name='room_requests'),
    path('managers/room-requests/<int:req_id>/respond/', views.respond_request, name='respond_request'),
    path('managers/log-meal/', views.manager_log_meal, name='manager_log_meal'),
     path('managers/notifications/', views.notifications, name='notifications'),
 path('managers/complaints/', views.view_complaints, name='view_complaints'),
 path('managers/complaints/<int:complaint_id>/read/', views.mark_complaint_read, name='mark_complaint_read'),
 path('managers/rotation/', views.manager_rotation, name='manager_rotation'),
]