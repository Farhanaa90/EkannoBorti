from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile
from rooms.models import Room


def home(request):
    return render(request, 'home.html')


def register(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, 'register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return render(request, 'register.html')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name
        )

        UserProfile.objects.create(
            user=user,
            role=role
        )

        login(request, user)
        messages.success(request, 'Registration successful! Welcome to EkannoBorti.')

        if role == 'seeker':
            return redirect('seeker_dashboard')
        else:
            return redirect('member_dashboard')

    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            profile = user.userprofile

            if profile.role == 'manager':
                return redirect('manager_dashboard')
            elif profile.role == 'seeker':
                return redirect('seeker_dashboard')
            else:
                return redirect('member_dashboard')
        else:
            messages.error(request, 'Invalid username or password!')
            return render(request, 'login.html')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')


@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'users/profile.html', {'user_profile': user_profile})


@login_required
def edit_profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        request.user.first_name = request.POST.get('name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()

        user_profile.phone = request.POST.get('phone', '')
        user_profile.gender = request.POST.get('gender', '')
        user_profile.date_of_birth = request.POST.get('date_of_birth') or None
        user_profile.address = request.POST.get('address', '')
        user_profile.institution = request.POST.get('institution', '')
        user_profile.student_id = request.POST.get('student_id', '')

        if request.FILES.get('profile_picture'):
            user_profile.profile_picture = request.FILES['profile_picture']

        user_profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')

    return render(request, 'users/edit_profile.html', {'user_profile': user_profile})


@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(old_password):
            messages.error(request, 'Current password is incorrect!')
            return render(request, 'users/change_password.html')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match!')
            return render(request, 'users/change_password.html')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password changed successfully!')
        return redirect('profile')

    return render(request, 'users/change_password.html')

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Your account has been deleted.')
        return redirect('home')

    return render(request, 'users/delete_account.html')

@login_required
def seeker_dashboard(request):
    user_profile = UserProfile.objects.get(user=request.user)
    available_rooms = Room.objects.filter(is_available=True).order_by('-posted_at')

    context = {
        'user_profile': user_profile,
        'available_rooms': available_rooms,
    }
    return render(request, 'rooms/seeker_dashboard.html', context)