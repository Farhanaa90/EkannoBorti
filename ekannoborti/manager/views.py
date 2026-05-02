from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
import datetime

from users.models import UserProfile
from rooms.models import Room, RoomRequest
from .models import Mess, MessMember, MealRate, Expense, Deposit, Complaint, ManagerRotation, Notification


def manager_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
            messages.error(request, 'Access denied.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def get_mess(request):
    return Mess.objects.filter(manager=request.user.userprofile).first()



@manager_required
def dashboard(request):
    mess = get_mess(request)
    if not mess:
        return render(request, 'manager/no_mess.html')

    today = timezone.now().date()

    total_members  = mess.members.count()
    active_members = mess.members.filter(is_active=True).count()

    month_expense = Expense.objects.filter(
        mess=mess,
        expense_month__year=today.year,
        expense_month__month=today.month,
    ).aggregate(t=Sum('total_amount'))['t'] or 0

    total_deposit = Deposit.objects.filter(mess=mess).aggregate(t=Sum('amount'))['t'] or 0

    pending_requests  = RoomRequest.objects.filter(room__posted_by=request.user.userprofile, status='pending').count()
    unread_complaints = mess.complaints.filter(is_read=False).count()
    unread_notifs     = mess.notifications.filter(is_read=False).count()

    return render(request, 'manager/dashboard.html', {
        'mess': mess,
        'total_members': total_members,
        'active_members': active_members,
        'month_expense': month_expense,
        'total_deposit': total_deposit,
        'pending_requests': pending_requests,
        'unread_complaints': unread_complaints,
        'unread_notifs': unread_notifs,
    })



@manager_required
def manage_members(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    if request.method == 'POST':
        username    = request.POST.get('username', '').strip()
        joined_date = request.POST.get('joined_date') or datetime.date.today().isoformat()

        try:
            target = UserProfile.objects.get(user__username=username)
        except UserProfile.DoesNotExist:
            messages.error(request, f"User '{username}' not found.")
            return redirect('manage_members')

        if MessMember.objects.filter(mess=mess, user=target).exists():
            messages.error(request, f"{username} is already a member.")
            return redirect('manage_members')

        MessMember.objects.create(mess=mess, user=target, joined_date=joined_date)
        target.role = 'member'
        target.save()
        Notification.objects.create(mess=mess, text=f"{username} was added as a member.")
        messages.success(request, f"{username} added successfully!")
        return redirect('manage_members')

    status_f = request.GET.get('status', 'all')
    search   = request.GET.get('search', '').strip()

    members = mess.members.all()
    if status_f == 'active':
        members = members.filter(is_active=True)
    elif status_f == 'inactive':
        members = members.filter(is_active=False)
    if search:
        members = members.filter(user__user__username__icontains=search)

    return render(request, 'manager/manage_members.html', {
        'mess': mess,
        'members': members,
        'total':    mess.members.count(),
        'active':   mess.members.filter(is_active=True).count(),
        'inactive': mess.members.filter(is_active=False).count(),
        'status_f': status_f,
        'search': search,
    })


@manager_required
def remove_member(request, member_id):
    mess   = get_mess(request)
    member = get_object_or_404(MessMember, id=member_id, mess=mess)
    if request.method == 'POST':
        name = member.user.user.username
        member.delete()
        messages.success(request, f"{name} removed from mess.")
    return redirect('manage_members')


@manager_required
def view_member_profile(request, member_id):
    mess   = get_mess(request)
    member = get_object_or_404(MessMember, id=member_id, mess=mess)
    return render(request, 'manager/view_profile.html', {'member': member, 'mess': mess})




@manager_required
def set_meal_rate(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    if request.method == 'POST':
        breakfast  = float(request.POST.get('breakfast', 0) or 0)
        lunch      = float(request.POST.get('lunch', 0) or 0)
        dinner     = float(request.POST.get('dinner', 0) or 0)
        start_date = request.POST.get('start_date')
        end_date   = request.POST.get('end_date') or None

        MealRate.objects.filter(mess=mess, is_active=True).update(is_active=False)
        MealRate.objects.create(
            mess=mess, breakfast=breakfast, lunch=lunch,
            dinner=dinner, start_date=start_date,
            end_date=end_date, is_active=True,
        )
        messages.success(request, 'Meal rate saved!')
        return redirect('set_meal_rate')

    current_rate = MealRate.objects.filter(mess=mess, is_active=True).first()
    rate_history = MealRate.objects.filter(mess=mess).order_by('-start_date')

    return render(request, 'manager/meal_rate.html', {
        'mess': mess,
        'current_rate': current_rate,
        'rate_history': rate_history,
    })




@manager_required
def add_expense(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    if request.method == 'POST':
        title         = request.POST.get('title', '').strip()
        description   = request.POST.get('description', '').strip()
        total_amount  = float(request.POST.get('total_amount', 0) or 0)
        expense_month = request.POST.get('expense_month', '')

        if not title or total_amount <= 0:
            messages.error(request, 'Please enter a title and valid amount.')
            return redirect('add_expense')

        month_date = datetime.datetime.strptime(expense_month + '-01', '%Y-%m-%d').date()
        Expense.objects.create(
            mess=mess, title=title, description=description,
            total_amount=total_amount, expense_month=month_date,
        )
        messages.success(request, f'Expense "{title}" added!')
        return redirect('add_expense')

    today = timezone.now().date()
    month_expenses   = Expense.objects.filter(mess=mess, expense_month__year=today.year, expense_month__month=today.month)
    total_this_month = month_expenses.aggregate(t=Sum('total_amount'))['t'] or 0
    active_count     = mess.members.filter(is_active=True).count()
    per_member       = round(total_this_month / active_count, 2) if active_count else 0

    return render(request, 'manager/add_expense.html', {
        'mess': mess,
        'month_expenses': month_expenses,
        'total_this_month': total_this_month,
        'per_member': per_member,
        'active_count': active_count,
    })



@manager_required
def record_deposit(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    if request.method == 'POST':
        member_id    = request.POST.get('member_id')
        amount       = float(request.POST.get('amount', 0) or 0)
        deposit_date = request.POST.get('deposit_date') or datetime.date.today().isoformat()
        note         = request.POST.get('note', '').strip()

        member = get_object_or_404(MessMember, id=member_id, mess=mess)
        Deposit.objects.create(mess=mess, member=member, amount=amount, deposit_date=deposit_date, note=note)
        messages.success(request, f'Deposit of {amount} recorded for {member.user.user.username}!')
        return redirect('record_deposit')

    today = timezone.now().date()
    members = mess.members.filter(is_active=True)

    total_deposited = Deposit.objects.filter(mess=mess).aggregate(t=Sum('amount'))['t'] or 0
    this_month      = Deposit.objects.filter(mess=mess, deposit_date__year=today.year, deposit_date__month=today.month).aggregate(t=Sum('amount'))['t'] or 0
    total_expense   = Expense.objects.filter(mess=mess).aggregate(t=Sum('total_amount'))['t'] or 0
    balance         = total_deposited - total_expense
    recent_deposits = Deposit.objects.filter(mess=mess).order_by('-deposit_date')[:10]

    return render(request, 'manager/record_deposit.html', {
        'mess': mess,
        'members': members,
        'total_deposited': total_deposited,
        'this_month': this_month,
        'total_expense': total_expense,
        'balance': balance,
        'recent_deposits': recent_deposits,
    })




@manager_required
def post_room(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    if request.method == 'POST':
        address = request.POST.get('address', '').strip()
        details = request.POST.get('details', '').strip()
        price   = float(request.POST.get('monthly_price', 0) or 0)
        photo   = request.FILES.get('photo')

        room = Room(posted_by=request.user.userprofile, address=address, details=details, monthly_price=price, is_available=True)
        if photo:
            room.photo = photo
        room.save()
        Notification.objects.create(mess=mess, text=f"New room posted: {address}")
        messages.success(request, 'Room posted successfully!')
        return redirect('post_room')

    my_rooms = Room.objects.filter(posted_by=request.user.userprofile).order_by('-posted_at')
    return render(request, 'manager/post_room.html', {'mess': mess, 'my_rooms': my_rooms})


@manager_required
def delete_room(request, room_id):
    room = get_object_or_404(Room, id=room_id, posted_by=request.user.userprofile)
    if request.method == 'POST':
        room.delete()
        messages.success(request, 'Room deleted.')
    return redirect('post_room')


@manager_required
def toggle_room(request, room_id):
    room = get_object_or_404(Room, id=room_id, posted_by=request.user.userprofile)
    if request.method == 'POST':
        room.is_available = not room.is_available
        room.save()
    return redirect('post_room')


@manager_required
def room_requests(request):
    f = request.GET.get('filter', 'all')
    qs = RoomRequest.objects.filter(room__posted_by=request.user.userprofile).order_by('-requested_at')
    if f != 'all':
        qs = qs.filter(status=f)

    base = RoomRequest.objects.filter(room__posted_by=request.user.userprofile)
    return render(request, 'manager/room_requests.html', {
        'requests': qs,
        'total': base.count(),
        'pending': base.filter(status='pending').count(),
        'accepted': base.filter(status='accepted').count(),
        'rejected': base.filter(status='rejected').count(),
        'f': f,
    })


@manager_required
def respond_request(request, req_id):
    req = get_object_or_404(RoomRequest, id=req_id, room__posted_by=request.user.userprofile)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            req.status = 'accepted'
            req.responded_at = timezone.now()
            req.save()
            req.room.is_available = False
            req.room.save()
            messages.success(request, f"Request from {req.seeker.user.username} accepted!")
        elif action == 'reject':
            req.status = 'rejected'
            req.responded_at = timezone.now()
            req.save()
            messages.success(request, "Request rejected.")
    return redirect('room_requests')