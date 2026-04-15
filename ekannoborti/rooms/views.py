from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Room, RoomRequest


def room_list(request):
    rooms = Room.objects.filter(is_available=True)
    return render(request, 'rooms/room_list.html', {'rooms': rooms})


def room_detail(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    return render(request, 'rooms/room_detail.html', {'room': room})


@login_required
def send_request(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    user_profile = request.user.userprofile

    already_sent = RoomRequest.objects.filter(
        room=room,
        seeker=user_profile
    ).exists()

    if already_sent:
        messages.error(request, 'You already sent a request for this room.')
        return redirect('room_detail', room_id=room.id)

    if request.method == 'POST':
        message_text = request.POST.get('message', '')

        RoomRequest.objects.create(
            room=room,
            seeker=user_profile,   # ✅ FIX এখানে
            message=message_text
        )

        messages.success(request, 'Request sent successfully!')
        return redirect('my_requests')

    return redirect('room_detail', room_id=room.id)


@login_required
def my_requests(request):
    user_profile = request.user.userprofile

    requests_list = RoomRequest.objects.filter(
        seeker=user_profile
    ).order_by('-requested_at')

    return render(request, 'rooms/my_requests.html', {
        'requests_list': requests_list
    })


@login_required
def seeker_dashboard(request):
    user_profile = request.user.userprofile

    my_requests = RoomRequest.objects.filter(
        seeker=user_profile
    ).order_by('-requested_at')

    total_requests = my_requests.count()
    pending_count = my_requests.filter(status='pending').count()
    accepted_count = my_requests.filter(status='accepted').count()
    rejected_count = my_requests.filter(status='rejected').count()

    available_rooms = Room.objects.filter(is_available=True).count()

    context = {
        'my_requests': my_requests,
        'total_requests': total_requests,
        'pending_count': pending_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
        'available_rooms': available_rooms,
    }

    return render(request, 'rooms/seeker_dashboard.html', context)