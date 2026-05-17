"""

from django.urls import path
from . import views

urlpatterns = [
    path('member/dashboard/', views.member_dashboard, name='member_dashboard'),
    path('member/log-meal/', views.log_meal, name='log_meal'),
    path('member/expenses/', views.view_expenses, name='view_expenses'),
    path('member/complaint/', views.file_complaint, name='file_complaint'),
    path('member/notifications/', views.member_notifications, name='member_notifications'),
    path('member/invitations/', views.view_invitations, name='view_invitations'),
    path('member/invitations/<int:invite_id>/respond/', views.respond_invitation, name='respond_invitation'),
]
"""