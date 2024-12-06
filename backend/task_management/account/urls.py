# from django.urls import path
# from .views import (
#     InviteUserView,
#     CreateRoleView,
#     Login_api,
#     UserListView,
#     ForgotPasswordView,
#     ResetPasswordView,
#     TaskListCreateView,
#     TaskDetailView,
#     TaskStatusUpdateView,
#     TaskActionListCreateView,
#     TaskActionDeleteView,
#     TaskActionUpdateView
# )

# urlpatterns = [
#     path('invite/', InviteUserView.as_view(), name='invite-user'),
#     path('role/create/', CreateRoleView.as_view(), name='create-role'),
#     path('login/', Login_api.as_view(), name='login'),
#     path('users/', UserListView.as_view(), name='user-list'),
#     path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
#     path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
#     path('tasks/', TaskListCreateView.as_view(), name='task-list-create'),
#     path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
#     path('tasks/<int:pk>/status/', TaskStatusUpdateView.as_view(), name='task-status-update'),
#     path('tasks/<int:pk>/actions/', TaskActionListCreateView.as_view(), name='task-actions'),
#     path('tasks/<int:pk>/actions/<int:action_id>/update/', TaskActionUpdateView.as_view(), name='task-action-update'),
#     path('tasks/<int:pk>/actions/<int:action_id>/delete/', TaskActionDeleteView.as_view(), name='task-action-delete'),
# ]

from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('profile/', views.profile, name='profile'),
    path('tasks/<int:task_id>/actions/add/', views.task_action_create, name='task_action_create'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('search/', views.search, name='search'),
    path('calendar/', views.calendar, name='calendar'),
    path('api/tasks/calendar/', views.calendar_events, name='calendar_events'),
    path('analytics/', views.analytics, name='analytics'),
    # User Management URLs
    path('users/', views.user_management, name='user_management'),
    
    # API endpoints
    path('api/users/', views.user_api, name='user_api'),
    path('api/users/<int:user_id>/', views.user_detail_api, name='user_detail_api'),
    
    path('tasks/<int:pk>/update-status/', views.task_status_update, name='task_status_update'),
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # User management URLs
    path('users/', views.user_management, name='user_management'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/view/', views.user_edit_view, name='user_edit_view'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/view/', views.user_delete_view, name='user_delete_view'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    # Task deletion URLs
    path('users/<int:user_id>/update/', views.update_user, name='update_user'),

    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    # path('api/tasks/<int:task_id>/delete/', views.TaskDeleteAPI.as_view(), name='task_delete_api'),

    # ... your existing API URLs ...
]