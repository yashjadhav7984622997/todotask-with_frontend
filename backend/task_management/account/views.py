from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from .models import Task, TaskAction, Location, CustomUser

# @login_required
# def dashboard(request):
#     context = {
#         'total_tasks': Task.objects.count(),
#         'in_progress_tasks': Task.objects.filter(status='IN_PROGRESS').count(),
#         'completed_tasks': Task.objects.filter(status='COMPLETED').count(),
#         'recent_tasks': Task.objects.all()[:5],
#         'recent_actions': TaskAction.objects.all()[:5],
#     }
#     return render(request, 'account/dashboard.html', context)

@login_required
def task_list(request):
    if request.user.user_type.can_assign_task:
        tasks = Task.objects.all()
    else:
        tasks = Task.objects.filter(assigned_to=request.user)
    return render(request, 'account/task_list.html', {'tasks': tasks})

@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    return render(request, 'account/task_detail.html', {'task': task})

@login_required
def task_create(request):
    if not request.user.user_type.can_assign_task:
        messages.error(request, 'You do not have permission to create tasks.')
        return redirect('task_list')

    if request.method == 'POST':
        # Handle form submission
        try:
            task = Task.objects.create(
                title=request.POST['title'],
                description=request.POST['description'],
                assigned_to_id=request.POST['assigned_to'],
                assigned_by=request.user,
                deadline=request.POST['deadline'],
                priority=request.POST['priority'],
                location_id=request.POST.get('location'),
            )
            messages.success(request, 'Task created successfully.')
            return redirect('task_detail', pk=task.pk)
        except Exception as e:
            messages.error(request, f'Error creating task: {str(e)}')
    
    context = {
        'employees': CustomUser.objects.filter(user_type__is_empolyee=True),
        'locations': Location.objects.all(),
    }
    return render(request, 'account/task_form.html', context)

@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    if not request.user.user_type.can_assign_task:
        messages.error(request, 'You do not have permission to edit tasks.')
        return redirect('task_detail', pk=pk)

    if request.method == 'POST':
        try:
            task.title = request.POST['title']
            task.description = request.POST['description']
            task.assigned_to_id = request.POST['assigned_to']
            task.deadline = request.POST['deadline']
            task.priority = request.POST['priority']
            task.location_id = request.POST.get('location')
            task.save()
            
            messages.success(request, 'Task updated successfully.')
            return redirect('task_detail', pk=task.pk)
        except Exception as e:
            messages.error(request, f'Error updating task: {str(e)}')
    
    context = {
        'task': task,
        'employees': CustomUser.objects.filter(user_type__is_empolyee=True),
        'locations': Location.objects.all(),
    }
    return render(request, 'account/task_form.html', context)

@login_required
def profile(request):
    context = {
        'total_tasks': Task.objects.filter(assigned_to=request.user).count(),
        'pending_tasks': Task.objects.filter(
            assigned_to=request.user,
            status__in=['PENDING', 'IN_PROGRESS']
        ).count(),
        'completed_tasks': Task.objects.filter(
            assigned_to=request.user,
            status='COMPLETED'
        ).count(),
        'recent_actions': TaskAction.objects.filter(
            performed_by=request.user
        ).order_by('-timestamp')[:5],
    }
    return render(request, 'account/profile.html', context)

@login_required
def task_action_create(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    
    # Check if user is assigned to this task or is a manager
    if not (request.user == task.assigned_to or request.user.user_type.can_assign_task):
        messages.error(request, 'You do not have permission to add actions to this task.')
        return redirect('task_detail', pk=task_id)

    if request.method == 'POST':
        try:
            action = TaskAction.objects.create(
                task=task,
                performed_by=request.user,
                action_description=request.POST['action_description'],
                materials_required=request.POST.get('materials_required', '')
            )
            messages.success(request, 'Action added successfully.')
            return redirect('task_detail', pk=task_id)
        except Exception as e:
            messages.error(request, f'Error adding action: {str(e)}')
    
    return render(request, 'account/task_action_form.html', {'task': task})
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

@login_required
def search(request):
    query = request.GET.get('q', '')
    if query:
        tasks = Task.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(assigned_to__first_name__icontains=query) |
            Q(assigned_to__last_name__icontains=query)
        )
        actions = TaskAction.objects.filter(
            Q(action_description__icontains=query) |
            Q(task__title__icontains=query)
        )
    else:
        tasks = Task.objects.none()
        actions = TaskAction.objects.none()

    context = {
        'query': query,
        'tasks': tasks,
        'actions': actions,
    }
    return render(request, 'account/search_results.html', context)

@login_required
def calendar(request):
    # Get upcoming tasks for the next 7 days
    upcoming_tasks = Task.objects.filter(
        deadline__gte=timezone.now(),
        deadline__lte=timezone.now() + timedelta(days=7)
    ).order_by('deadline')

    context = {
        'upcoming_tasks': upcoming_tasks,
    }
    return render(request, 'account/calendar.html', context)

# API endpoint for calendar events
@login_required
def calendar_events(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    tasks = Task.objects.filter(
        deadline__range=[start, end]
    )
    
    events = []
    for task in tasks:
        events.append({
            'id': task.id,
            'title': task.title,
            'start': task.deadline.isoformat(),
            'end': task.deadline.isoformat(),
            'priority': task.priority,
            'status': task.status,
            'className': f'priority-{task.priority}',
        })
    
    return JsonResponse(events, safe=False)

from django.db.models import Count, Avg, F, ExpressionWrapper, fields
from django.db.models.functions import ExtractDay
from datetime import datetime, timedelta

@login_required
def analytics(request):
    today = timezone.now()
    thirty_days_ago = today - timedelta(days=30)
    
    # Basic statistics
    total_tasks = Task.objects.count()
    tasks_this_month = Task.objects.filter(created_at__month=today.month).count()
    
    completed_tasks = Task.objects.filter(
        status='COMPLETED',
        created_at__gte=thirty_days_ago
    ).count()
    
    total_tasks_period = Task.objects.filter(created_at__gte=thirty_days_ago).count()
    completion_rate = round((completed_tasks / total_tasks_period * 100) if total_tasks_period > 0 else 0)
    
    # Average completion time
    completed_tasks = Task.objects.filter(status='COMPLETED')
    completion_time = completed_tasks.annotate(
        duration=ExpressionWrapper(
            F('updated_at') - F('created_at'),
            output_field=fields.DurationField()
        )
    ).aggregate(avg_duration=Avg('duration'))
    
    avg_completion_days = round(completion_time['avg_duration'].days if completion_time['avg_duration'] else 0)
    
    # Active users
    active_users = CustomUser.objects.filter(
        assigned_tasks__created_at__month=today.month
    ).distinct().count()
    
    # Status distribution
    status_distribution = Task.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    status_labels = [item['status'] for item in status_distribution]
    status_data = [item['count'] for item in status_distribution]
    
    # Priority distribution
    priority_distribution = Task.objects.values('priority').annotate(
        count=Count('id')
    ).order_by('priority')
    
    priority_labels = [item['priority'] for item in priority_distribution]
    priority_data = [item['count'] for item in priority_distribution]
    
    # Trend data (last 7 days)
    trend_data = []
    trend_labels = []
    for i in range(7):
        date = today - timedelta(days=i)
        count = Task.objects.filter(
            status='COMPLETED',
            updated_at__date=date.date()
        ).count()
        trend_data.append(count)
        trend_labels.append(date.strftime('%b %d'))
    
    trend_data.reverse()
    trend_labels.reverse()
    
    # Top performers
    top_performers = CustomUser.objects.annotate(
        completed_tasks=Count('assigned_tasks', filter=Q(
            assigned_tasks__status='COMPLETED',
            assigned_tasks__updated_at__gte=thirty_days_ago
        )),
        total_tasks=Count('assigned_tasks', filter=Q(
            assigned_tasks__created_at__gte=thirty_days_ago
        ))
    ).filter(total_tasks__gt=0).annotate(
        completion_rate=ExpressionWrapper(
            F('completed_tasks') * 100.0 / F('total_tasks'),
            output_field=fields.FloatField()
        )
    ).order_by('-completion_rate')[:5]
    
    # Recent completions
    recent_completions = Task.objects.filter(
        status='COMPLETED'
    ).annotate(
        duration_days=ExtractDay(F('updated_at') - F('created_at'))
    ).order_by('-updated_at')[:10]
    
    context = {
        'total_tasks': total_tasks,
        'tasks_this_month': tasks_this_month,
        'completion_rate': completion_rate,
        'avg_completion_days': avg_completion_days,
        'active_users': active_users,
        'status_labels': status_labels,
        'status_data': status_data,
        'priority_labels': priority_labels,
        'priority_data': priority_data,
        'trend_labels': trend_labels,
        'trend_data': trend_data,
        'top_performers': top_performers,
        'recent_completions': recent_completions,
    }
    
    return render(request, 'account/analytics.html', context)


from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import CustomUser, UserType
from .serializers import UserSerializer

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied

def can_manage_users(user):
    """Check if user has permission to manage users"""
    return user.is_authenticated and (user.is_superuser or (user.user_type and user.user_type.can_create_user))

@login_required
def user_management(request):
    # Debug information
    print(f"User: {request.user.email}")
    print(f"User Type: {request.user.user_type}")
    print(f"Is Superuser: {request.user.is_superuser}")
    print(f"Can Create User: {request.user.user_type.can_create_user if request.user.user_type else False}")
    
    if not can_manage_users(request.user):
        messages.error(request, "You don't have permission to access user management.")
        return redirect('dashboard')
    
    users_list = CustomUser.objects.filter(is_deleted=False).select_related('user_type')
    user_types = UserType.objects.all()
    
    context = {
        'users': users_list,
        'user_types': user_types,
        'can_create_user': True if request.user.is_superuser else request.user.user_type.can_create_user
    }
    return render(request, 'account/user_management.html', context)

@login_required
@user_passes_test(can_manage_users, login_url='dashboard')
def user_create(request):
    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            password = request.POST.get('password')
            user_type_id = request.POST.get('user_type')
            
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return redirect('user_management')
            
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                user_type_id=user_type_id,
                is_active=True
            )
            
            messages.success(request, 'User created successfully')
            return redirect('user_management')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('user_management')
    
    return redirect('user_management')

@login_required
@user_passes_test(can_manage_users, login_url='dashboard')
def user_edit(request, user_id):
    try:
        user_to_edit = CustomUser.objects.get(id=user_id, is_deleted=False)
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found')
        return redirect('user_management')
    
    if request.method == 'GET':
        # Return user data as JSON for GET request
        return JsonResponse({
            'email': user_to_edit.email,
            'first_name': user_to_edit.first_name,
            'last_name': user_to_edit.last_name,
            'user_type': user_to_edit.user_type.id if user_to_edit.user_type else None,
            'is_active': user_to_edit.is_active,
        })
    
    elif request.method == 'POST':
        try:
            # Don't allow editing superuser status through this interface
            if user_to_edit.is_superuser and not request.user.is_superuser:
                messages.error(request, "You don't have permission to edit a superuser")
                return redirect('user_management')
            
            user_to_edit.email = request.POST.get('email', user_to_edit.email)
            user_to_edit.first_name = request.POST.get('first_name', user_to_edit.first_name)
            user_to_edit.last_name = request.POST.get('last_name', user_to_edit.last_name)
            
            # Only update user_type if not a superuser
            if not user_to_edit.is_superuser:
                user_to_edit.user_type_id = request.POST.get('user_type', user_to_edit.user_type_id)
            
            # Handle active status
            is_active = request.POST.get('is_active') == 'true'
            if user_to_edit.is_active != is_active:
                if user_to_edit.is_superuser and not request.user.is_superuser:
                    messages.error(request, "You don't have permission to change a superuser's status")
                    return redirect('user_management')
                user_to_edit.is_active = is_active
            
            # Handle password change
            if request.POST.get('password'):
                user_to_edit.set_password(request.POST.get('password'))
            
            user_to_edit.save()
            messages.success(request, 'User updated successfully')
            
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    return redirect('user_management')

@login_required
@user_passes_test(can_manage_users, login_url='dashboard')
def user_delete(request, user_id):
    try:
        user_to_delete = CustomUser.objects.get(id=user_id, is_deleted=False)
        
        # Don't allow deleting superusers unless you're a superuser
        if user_to_delete.is_superuser and not request.user.is_superuser:
            messages.error(request, "You don't have permission to delete a superuser")
            return redirect('user_management')
        
        # Soft delete the user
        user_to_delete.is_deleted = True
        user_to_delete.is_active = False
        user_to_delete.save()
        
        messages.success(request, 'User deleted successfully')
        
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found')
    except Exception as e:
        messages.error(request, f'Error deleting user: {str(e)}')
    
    return redirect('user_management')

from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification

@login_required
def notifications_view(request):
    notifications_list = request.user.notifications.all()
    paginator = Paginator(notifications_list, 10)  # Show 10 notifications per page
    
    page = request.GET.get('page')
    notifications = paginator.get_page(page)
    
    return render(request, 'account/notifications.html', {
        'notifications': notifications
    })

@login_required
def mark_notification_read(request, notification_id):
    try:
        notification = request.user.notifications.get(id=notification_id)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False}, status=404)

@login_required
def mark_all_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})

@login_required
def notification_count(request):
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})

# Utility function to create notifications
def create_notification(user, title, message, notification_type, task=None):
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        task=task
    )
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from .models import CustomUser, UserType
from .serializers import UserSerializer
import json

def can_manage_users(user):
    return user.is_authenticated and (user.is_superuser or (user.user_type and user.user_type.can_create_user))

@login_required
@user_passes_test(can_manage_users)
def user_management(request):
    # Get filters from request
    user_type_id = request.GET.get('user_type')
    status = request.GET.get('status')
    search = request.GET.get('search', '').strip()
    
    # Base queryset
    users = CustomUser.objects.filter(is_deleted=False).select_related('user_type')
    
    # Apply filters
    if user_type_id:
        users = users.filter(user_type_id=user_type_id)
    
    if status:
        is_active = status == 'active'
        users = users.filter(is_active=is_active)
    
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(users.order_by('-created_at'), 10)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)
    
    context = {
        'users': users_page,
        'user_types': UserType.objects.all(),
        'selected_type': user_type_id,
        'status': status,
        'search': search,
    }
    return render(request, 'account/user_management.html', context)

# API Views
@login_required
@user_passes_test(can_manage_users)
def user_api(request):
    if request.method == 'GET':
        users = CustomUser.objects.filter(is_deleted=False)
        serializer = UserSerializer(users, many=True)
        return JsonResponse({'success': True, 'users': serializer.data})
    
    elif request.method == 'POST':
        try:
            email = request.POST.get('email')
            password = request.POST.get('password')
            user_type_id = request.POST.get('user_type')
            
            if not all([email, password, user_type_id]):
                return JsonResponse({
                    'success': False,
                    'error': 'Missing required fields'
                }, status=400)
            
            # Check if email already exists
            if CustomUser.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Email already exists'
                }, status=400)
            
            # Create user
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                user_type_id=user_type_id,
                is_active=True
            )
            
            return JsonResponse({
                'success': True,
                'user': UserSerializer(user).data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

@login_required
@user_passes_test(can_manage_users)
def user_detail_api(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id, is_deleted=False)
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'user': UserSerializer(user).data
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body) if request.body else request.POST
            
            # Update basic info
            user.email = data.get('email', user.email)
            user.first_name = data.get('first_name', user.first_name)
            user.last_name = data.get('last_name', user.last_name)
            user.is_active = data.get('is_active', user.is_active)
            
            # Update user type if provided
            user_type_id = data.get('user_type')
            if user_type_id:
                user.user_type_id = user_type_id
            
            # Update password if provided
            password = data.get('password')
            if password:
                user.set_password(password)
                user.is_password_created = True
            
            user.save()
            
            return JsonResponse({
                'success': True,
                'user': UserSerializer(user).data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    elif request.method == 'DELETE':
        try:
            user.is_deleted = True
            user.is_active = False
            user.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'account/login.html')

from django.contrib.auth import login, authenticate,logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Task  # Import the Task model if you have it

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Task, CustomUser

@login_required
def dashboard(request):
    user = request.user
    print(f"Dashboard - User: {request.user.email}")
    print(f"Dashboard - User Type: {request.user.user_type}")
    
    # Base queryset for tasks
    if user.user_type and user.user_type.can_assign_task:
        # For admin/manager: show all tasks
        base_tasks = Task.objects.select_related('assigned_to', 'assigned_by', 'location')
    else:
        # For regular employees: show only their assigned tasks
        base_tasks = Task.objects.select_related('assigned_to', 'assigned_by', 'location').filter(assigned_to=user)

    # Task counts by status
    task_counts = {
        'total_tasks': base_tasks.count(),
        'pending_tasks': base_tasks.filter(status='PENDING').count(),
        'in_progress_tasks': base_tasks.filter(status='IN_PROGRESS').count(),
        'completed_tasks': base_tasks.filter(status='COMPLETED').count(),
    }

    # Task counts by priority
    priority_counts = base_tasks.values('priority').annotate(
        count=Count('id')
    ).order_by('priority')

    # Recent tasks
    recent_tasks = base_tasks.order_by('-created_at')[:5]

    # Tasks due soon (next 7 days)
    upcoming_deadline = timezone.now() + timedelta(days=7)
    tasks_due_soon = base_tasks.filter(
        deadline__lte=upcoming_deadline,
        deadline__gte=timezone.now(),
        status__in=['PENDING', 'IN_PROGRESS']
    ).order_by('deadline')[:5]

    # Overdue tasks
    overdue_tasks = base_tasks.filter(
        deadline__lt=timezone.now(),
        status__in=['PENDING', 'IN_PROGRESS']
    ).order_by('deadline')

    # Tasks by location
    tasks_by_location = base_tasks.values(
        'location__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')

    # Additional data for managers/admins
    if user.user_type and user.user_type.can_assign_task:
        # Tasks assigned by current user
        assigned_by_me = Task.objects.filter(
            assigned_by=user
        ).select_related('assigned_to').order_by('-created_at')[:5]

        # User task distribution
        user_task_counts = CustomUser.objects.annotate(
            total_tasks=Count('assigned_tasks'),
            pending_tasks=Count('assigned_tasks', 
                filter=Q(assigned_tasks__status='PENDING')),
            in_progress_tasks=Count('assigned_tasks', 
                filter=Q(assigned_tasks__status='IN_PROGRESS')),
            completed_tasks=Count('assigned_tasks', 
                filter=Q(assigned_tasks__status='COMPLETED')),
            high_priority_tasks=Count('assigned_tasks', 
                filter=Q(assigned_tasks__priority='high'))
        ).filter(total_tasks__gt=0)

        # High priority pending tasks
        high_priority_pending = base_tasks.filter(
            priority='high',
            status__in=['PENDING', 'IN_PROGRESS']
        ).order_by('deadline')[:5]
    else:
        assigned_by_me = None
        user_task_counts = None
        high_priority_pending = None

    # Calculate completion rate
    if task_counts['total_tasks'] > 0:
        completion_rate = (task_counts['completed_tasks'] / task_counts['total_tasks']) * 100
    else:
        completion_rate = 0

    context = {
        # Basic counts
        **task_counts,
        'completion_rate': round(completion_rate, 1),
        
        # Priority distribution
        'priority_counts': priority_counts,
        
        # Task lists
        'recent_tasks': recent_tasks,
        'tasks_due_soon': tasks_due_soon,
        'overdue_tasks': overdue_tasks,
        'high_priority_pending': high_priority_pending,
        
        # Location data
        'tasks_by_location': tasks_by_location,
        
        # Manager/Admin specific data
        'assigned_by_me': assigned_by_me,
        'user_task_counts': user_task_counts,
        
        # User permissions
        'can_assign_task': user.user_type.can_assign_task if user.user_type else False,
    }
    
    return render(request, 'account/dashboard.html', context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'account/login.html')


def logout_view(request):
    if request.user:
   
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return redirect('login')
    else:
       messages.error(request, 'already logged out.') 


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Task

@login_required
def task_status_update(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Task.STATUS_CHOICES):
            task.status = new_status
            task.save()
            messages.success(request, 'Task status updated successfully.')
        else:
            messages.error(request, 'Invalid status selected.')
    
    return redirect('task_detail', pk=pk)



@login_required
def task_form(request, task_id=None):
    if task_id:
        task = get_object_or_404(Task, id=task_id)
    else:
        task = None
    
    # Get all employees (users with employee user type)
    employees = CustomUser.objects.filter(
        is_active=True,
        user_type__is_empolyee=True  # Note the double underscore
    ).select_related('user_type')
    
    locations = Location.objects.all()
    
    context = {
        'task': task,
        'employees': employees,
        'locations': locations,
    }
    
    print("Debug - Number of employees:", employees.count())  # Debug print
    for emp in employees:
        print(f"Debug - Employee: {emp.email}, Type: {emp.user_type}")  # Debug print
    
    return render(request, 'account/task_form.html', context)

@login_required
def task_delete(request, pk):
    try:
        task = get_object_or_404(Task, pk=pk)
        
        # Check if user has permission to delete the task
        if not request.user.is_superuser and task.created_by != request.user:
            messages.error(request, "You don't have permission to delete this task")
            return redirect('dashboard')
        
        task_name = task.title
        task.delete()
        
        messages.success(request, f'Task "{task_name}" has been deleted successfully')
        return redirect('task_list')
        
    except Exception as e:
        messages.error(request, f'Error deleting task: {str(e)}')
        return redirect('task_list')

@login_required
@user_passes_test(can_manage_users, login_url='dashboard')
def user_edit_view(request, user_id):
    """View function for getting user data for editing"""
    try:
        user_to_edit = CustomUser.objects.get(id=user_id, is_deleted=False)
        return JsonResponse({
            'email': user_to_edit.email,
            'first_name': user_to_edit.first_name,
            'last_name': user_to_edit.last_name,
            'user_type': user_to_edit.user_type.id if user_to_edit.user_type else None,
            'is_active': user_to_edit.is_active,
        })
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@user_passes_test(can_manage_users, login_url='dashboard')
def user_delete_view(request, user_id):
    """View function for confirming user deletion"""
    try:
        user_to_delete = CustomUser.objects.get(id=user_id, is_deleted=False)
        return JsonResponse({
            'user_id': user_to_delete.id,
            'email': user_to_delete.email,
            'name': f"{user_to_delete.first_name} {user_to_delete.last_name}".strip(),
        })
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import CustomUser, UserType

@login_required
def update_user(request, user_id):
    # Get the user to update
    user_to_update = get_object_or_404(CustomUser, id=user_id)
    
    # Check if the current user has permission to update users
    if not request.user.user_type.can_create_user:
        messages.error(request, "You don't have permission to update users.")
        return redirect('user_management')

    if request.method == 'POST':
        # Get form data
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        user_type_id = request.POST.get('user_type')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        is_active = request.POST.get('is_active') == 'on'

        try:
            # Validate email uniqueness (excluding current user)
            if CustomUser.objects.exclude(id=user_id).filter(email=email).exists():
                messages.error(request, 'This email is already in use.')
                return redirect('user_management')

            # Update user fields
            user_to_update.email = email
            user_to_update.first_name = first_name
            user_to_update.last_name = last_name
            user_to_update.is_active = is_active

            # Update user type if changed
            if user_type_id:
                user_type = get_object_or_404(UserType, id=user_type_id)
                user_to_update.user_type = user_type

            # Update password if provided
            if password:
                if password != confirm_password:
                    messages.error(request, "Passwords don't match.")
                    return redirect('user_management')
                user_to_update.set_password(password)

            user_to_update.save()
            messages.success(request, 'User updated successfully.')
            return redirect('user_management')

        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
            return redirect('user_management')

    return redirect('user_management')