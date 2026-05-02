from django.urls import path
from . import views

urlpatterns = [
    path('manager/dashboard/',                          views.dashboard,            name='manager_dashboard'),
    path('manager/members/',                            views.manage_members,       name='manage_members'),
    path('manager/members/<int:member_id>/remove/',     views.remove_member,        name='remove_member'),
    path('manager/members/<int:member_id>/profile/',    views.view_member_profile,  name='view_member_profile'),
    path('manager/meal-rate/',                          views.set_meal_rate,        name='set_meal_rate'),
    path('manager/expense/',                            views.add_expense,          name='add_expense'),
    path('manager/deposit/',                            views.record_deposit,       name='record_deposit'),
    path('manager/post-room/',                          views.post_room,            name='post_room'),
    path('manager/post-room/<int:room_id>/delete/',     views.delete_room,          name='delete_room'),
    path('manager/post-room/<int:room_id>/toggle/',     views.toggle_room,          name='toggle_room'),
    path('manager/room-requests/',                      views.room_requests,        name='room_requests'),
    path('manager/room-requests/<int:req_id>/respond/', views.respond_request,      name='respond_request'),
]