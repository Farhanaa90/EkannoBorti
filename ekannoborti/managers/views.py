import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from users.models import UserProfile
from rooms.models import Room, RoomRequest
from .models import Mess, MessMember, MealRate, Expense, Deposit,Complaint, ManagerRotation, Notification
from members.models import MessInvitation
from members.models import MealLog, Mess as MemberMess


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


def unread_notifs(mess):
    if mess:
        return mess.notifications.filter(
            is_read=False,
            notif_type__in=['manager_only', 'room_request', 'complaint']
        ).count()
    return 0


@manager_required
def create_mess(request):
    if get_mess(request):
        return redirect('manager_dashboard')

    if request.method == 'POST':
        mess_name = request.POST.get('mess_name', '').strip()
        address   = request.POST.get('address', '').strip()
        if not mess_name or not address:
            messages.error(request, 'Please fill in all fields.')
            return render(request, 'managers/create_mess.html')
        Mess.objects.create(manager=request.user.userprofile, mess_name=mess_name, address=address)
        messages.success(request, f'Mess "{mess_name}" created successfully!')
        return redirect('manager_dashboard')

    return render(request, 'managers/create_mess.html')


@manager_required
def dashboard(request):
    mess = get_mess(request)
    if not mess:
        return render(request, 'managers/no_mess.html')

    today             = timezone.now().date()
    total_members     = mess.members.count()
    active_members    = mess.members.filter(is_active=True).count()
    month_expense     = Expense.objects.filter(
        mess=mess, expense_month__year=today.year, expense_month__month=today.month
    ).aggregate(t=Sum('total_amount'))['t'] or 0
    total_deposit     = Deposit.objects.filter(mess=mess).aggregate(t=Sum('amount'))['t'] or 0
    pending_requests  = RoomRequest.objects.filter(room__posted_by=request.user.userprofile, status='pending').count()
    unread_complaints = mess.complaints.filter(is_read=False).count()

    return render(request, 'managers/manager_dashboard.html', {
        'mess':              mess,
        'total_members':     total_members,
        'active_members':    active_members,
        'month_expense':     month_expense,
        'total_deposit':     total_deposit,
        'pending_requests':  pending_requests,
        'unread_complaints': unread_complaints,
        'unread_notifs':     unread_notifs(mess),
    })


@manager_required
def manage_members(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        try:
            target = UserProfile.objects.get(user__username=username)
        except UserProfile.DoesNotExist:
            messages.error(request, f"User '{username}' not found.")
            return redirect('manage_members')

        if MessMember.objects.filter(mess=mess, user=target, is_active=True).exists():
            messages.error(request, f"{username} is already a member.")
            return redirect('manage_members')

        if MessInvitation.objects.filter(
            mess_name=mess.mess_name,
            member=target.user,
            status='pending'
        ).exists():
            messages.error(request, f"An invitation has already been sent to {username}.")
            return redirect('manage_members')

        MessInvitation.objects.create(
            mess_name=mess.mess_name,
            mess_address=mess.address,
            manager_username=request.user.username,
            member=target.user,
            status='pending'
        )

        Notification.objects.create(
            mess=mess,
            text=f"An invitation has been sent to {username} to join the mess.",
            notif_type="manager_only"
        )

        Notification.objects.create(
            recipient=target.user,
            text=f"You have received an invitation from mess '{mess.mess_name}'!",
            notif_type="member_invite"
        )

        Notification.objects.create(
            mess=mess,
            text=f"'{username}' has been invited as a new member to the mess.",
            notif_type="member_add"
        )

        messages.success(request, f"Invitation sent to {username}!")
        return redirect('manage_members')

    status_f = request.GET.get('status', 'all')
    search   = request.GET.get('search', '').strip()
    members  = mess.members.all()
    if status_f == 'active':
        members = members.filter(is_active=True)
    elif status_f == 'inactive':
        members = members.filter(is_active=False)
    if search:
        members = members.filter(user__user__username__icontains=search)

    pending_invitations = MessInvitation.objects.filter(
        mess_name=mess.mess_name,
        status='pending'
    )

    return render(request, 'managers/manage_members.html', {
        'mess':                mess,
        'members':             members,
        'total':               mess.members.count(),
        'active':              mess.members.filter(is_active=True).count(),
        'inactive':            mess.members.filter(is_active=False).count(),
        'status_f':            status_f,
        'search':              search,
        'unread_notifs':       unread_notifs(mess),
        'pending_invitations': pending_invitations,
    })


@manager_required
def remove_member(request, member_id):
    mess   = get_mess(request)
    member = get_object_or_404(MessMember, id=member_id, mess=mess)
    if request.method == 'POST':
        name = member.user.user.username
        member.delete()
        Notification.objects.create(
            mess=mess,
            text=f"{name} has been removed from the mess.",
            notif_type="member_alert"
        )
        messages.success(request, f"{name} removed from mess.")
    return redirect('manage_members')


@manager_required
def set_meal_rate(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    if request.method == 'POST':
        breakfast = round(float(request.POST.get('breakfast', 0) or 0), 2)
        lunch = round(float(request.POST.get('lunch', 0) or 0), 2)
        dinner = round(float(request.POST.get('dinner', 0) or 0), 2)
        start_date = request.POST.get('start_date')
        end_date   = request.POST.get('end_date') or None
        MealRate.objects.filter(mess=mess, is_active=True).update(is_active=False)
        MealRate.objects.create(
            mess=mess, breakfast=breakfast, lunch=lunch, dinner=dinner,
            start_date=start_date, end_date=end_date, is_active=True
        )
        Notification.objects.create(
            mess=mess,
            text=f"Meal rate updated: Breakfast BDT{breakfast}, Lunch BDT{lunch}, Dinner BDT{dinner}.",
            notif_type="meal_rate"
        )
        messages.success(request, 'Meal rate saved!')
        return redirect('set_meal_rate')

    current_rate = MealRate.objects.filter(mess=mess, is_active=True).first()
    rate_history = MealRate.objects.filter(mess=mess).order_by('-start_date')
    return render(request, 'managers/set_meal_rate.html', {
        'mess':          mess,
        'current_rate':  current_rate,
        'rate_history':  rate_history,
        'unread_notifs': unread_notifs(mess),
    })


@manager_required
def add_expense(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    if request.method == 'POST':
        title         = request.POST.get('title', '').strip()
        description   = request.POST.get('description', '').strip()
        total_amount = round(float(request.POST.get('total_amount', 0) or 0), 2)
        expense_month = request.POST.get('expense_month', '')
        if not title or total_amount <= 0:
            messages.error(request, 'Please enter a title and valid amount.')
            return redirect('add_expense')
        month_date = datetime.datetime.strptime(expense_month + '-01', '%Y-%m-%d').date()
        Expense.objects.create(
            mess=mess, title=title, description=description,
            total_amount=total_amount, expense_month=month_date
        )
        Notification.objects.create(
            mess=mess,
            text=f"New expense added: {title} — BDT{total_amount}.",
            notif_type="expense"
        )
        messages.success(request, f'Expense "{title}" added!')
        return redirect('add_expense')

    today            = timezone.now().date()
    month_expenses   = Expense.objects.filter(
        mess=mess, expense_month__year=today.year, expense_month__month=today.month
    )
    total_this_month = month_expenses.aggregate(t=Sum('total_amount'))['t'] or 0
    active_count     = mess.members.filter(is_active=True).count()
    per_member       = round(total_this_month / active_count, 2) if active_count else 0
    return render(request, 'managers/add_expense.html', {
        'mess':             mess,
        'month_expenses':   month_expenses,
        'total_this_month': total_this_month,
        'per_member':       per_member,
        'active_count':     active_count,
        'unread_notifs':    unread_notifs(mess),
    })


@manager_required
def record_deposit(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    today = timezone.now().date()
    selected_month = request.GET.get(
        'filter_month',
        f"{today.year}-{str(today.month).zfill(2)}"
    )
    year, month = map(int, selected_month.split('-'))

    if request.method == 'POST':
        member_id    = request.POST.get('member')
        amount = round(float(request.POST.get('amount', 0)), 2)
        deposit_date = request.POST.get('deposit_date')
        note         = request.POST.get('note', '').strip()
        member       = get_object_or_404(MessMember, id=member_id, mess=mess)
        Deposit.objects.create(
            mess=mess, member=member,
            amount=amount, deposit_date=deposit_date, note=note
        )
        Notification.objects.create(
            recipient=member.user.user,
            text=f"Your deposit of BDT{amount} has been recorded.",
            notif_type="deposit"
        )
        messages.success(request, "Deposit recorded successfully!")
        return redirect('record_deposit')

    deposits        = Deposit.objects.filter(
        mess=mess, deposit_date__year=year, deposit_date__month=month
    ).order_by('-deposit_date')
    this_month      = deposits.aggregate(t=Sum('amount'))['t'] or 0
    total_expense   = Expense.objects.filter(mess=mess).aggregate(t=Sum('total_amount'))['t'] or 0
    total_deposited = Deposit.objects.filter(mess=mess).aggregate(t=Sum('amount'))['t'] or 0
    balance         = total_deposited - total_expense
    members         = mess.members.filter(is_active=True)
    month_choices   = [
        {
            'value': f"{today.year}-{str(m).zfill(2)}",
            'label': datetime.date(today.year, m, 1).strftime('%B %Y')
        }
        for m in range(1, 13)
    ]

    return render(request, 'managers/record_deposit.html', {
        'mess':           mess,
        'members':        members,
        'deposits':       deposits,
        'this_month':     this_month,
        'total_expense':  total_expense,
        'balance':        balance,
        'month_choices':  month_choices,
        'selected_month': selected_month,
        'current_month':  datetime.date(year, month, 1).strftime('%B %Y'),
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
        room    = Room(
            posted_by=request.user.userprofile, address=address,
            details=details, monthly_price=price, is_available=True
        )
        if photo:
            room.photo = photo
        room.save()
        Notification.objects.create(
            mess=mess,
            text=f"New room posted: {address}.",
            notif_type="manager_only"
        )
        messages.success(request, 'Room posted successfully!')
        return redirect('post_room')

    my_rooms = Room.objects.filter(posted_by=request.user.userprofile).order_by('-posted_at')
    return render(request, 'managers/post_room.html', {
        'mess':          mess,
        'my_rooms':      my_rooms,
        'unread_notifs': unread_notifs(mess),
    })


@manager_required
def delete_room(request, room_id):
    room = get_object_or_404(Room, id=room_id, posted_by=request.user.userprofile)
    if request.method == 'POST':
        mess = get_mess(request)
        Notification.objects.create(
            mess=mess,
            text=f"Room deleted: {room.address}.",
            notif_type="manager_only"
        )
        room.delete()
        messages.success(request, 'Room deleted.')
    return redirect('post_room')


@manager_required
def toggle_room(request, room_id):
    room = get_object_or_404(Room, id=room_id, posted_by=request.user.userprofile)
    if request.method == 'POST':
        room.is_available = not room.is_available
        room.save()
        mess   = get_mess(request)
        status = "Available" if room.is_available else "Unavailable"
        Notification.objects.create(
            mess=mess,
            text=f"Room marked as {status}: {room.address}.",
            notif_type="manager_only"
        )
    return redirect('post_room')



@manager_required
def room_requests(request):
    mess = get_mess(request)
    f    = request.GET.get('filter', 'all')
    qs   = RoomRequest.objects.filter(room__posted_by=request.user.userprofile).order_by('-requested_at')
    if f != 'all':
        qs = qs.filter(status=f)
    base = RoomRequest.objects.filter(room__posted_by=request.user.userprofile)
    return render(request, 'managers/room_requests.html', {
        'room_requests':   qs,
        'current_filter':  f,
        'total':           base.count(),
        'pending_count':   base.filter(status='pending').count(),
        'accepted_count':  base.filter(status='accepted').count(),
        'rejected_count':  base.filter(status='rejected').count(),
        'unread_notifs':   unread_notifs(mess),
    })


@manager_required
def respond_request(request, req_id):
    req  = get_object_or_404(RoomRequest, id=req_id, room__posted_by=request.user.userprofile)
    mess = get_mess(request)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            req.status       = 'accepted'
            req.responded_at = timezone.now()
            req.save()
            req.room.is_available = False
            req.room.save()
            Notification.objects.create(
                mess=mess,
                text=f"Room request from {req.seeker.user.username} was accepted.",
                notif_type="manager_only"
            )
            Notification.objects.create(
                recipient=req.seeker.user,
                text=f"Your room request for '{req.room.address}' has been accepted!",
                notif_type="seeker"
            )
            messages.success(request, f"Request from {req.seeker.user.username} accepted!")
        elif action == 'reject':
            req.status       = 'rejected'
            req.responded_at = timezone.now()
            req.save()
            Notification.objects.create(
                mess=mess,
                text=f"Room request from {req.seeker.user.username} was rejected.",
                notif_type="manager_only"
            )
            Notification.objects.create(
                recipient=req.seeker.user,
                text=f"Your room request for '{req.room.address}' was declined.",
                notif_type="seeker"
            )
            messages.success(request, "Request rejected.")
    return redirect('room_requests')


@manager_required
def view_member_profile(request, member_id):
    mess            = get_mess(request)
    member          = get_object_or_404(MessMember, id=member_id, mess=mess)
    total_deposited = Deposit.objects.filter(mess=mess, member=member).aggregate(t=Sum('amount'))['t'] or 0
    total_expense   = Expense.objects.filter(mess=mess).aggregate(t=Sum('total_amount'))['t'] or 0
    active_count    = mess.members.filter(is_active=True).count()
    per_member_due = round(total_expense / active_count, 2) if active_count else 0
    total_due = round(max(0, per_member_due - total_deposited), 2)
    recent_deposits = Deposit.objects.filter(mess=mess, member=member).order_by('-deposit_date')[:5]

    return render(request, 'managers/member_profile.html', {
        'member':          member,
        'mess':            mess,
        'total_deposited': total_deposited,
        'total_due':       total_due,
        'recent_deposits': recent_deposits,
        'unread_notifs':   unread_notifs(mess),
    })


@manager_required
def manager_log_meal(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    today        = timezone.now().date()
    current_rate = MealRate.objects.filter(mess=mess, is_active=True).first()
    existing_log = MealLog.objects.filter(
        member=request.user, log_date=today
    ).first()

    if request.method == 'POST':
        breakfast = request.POST.get('breakfast') == 'on'
        lunch     = request.POST.get('lunch') == 'on'
        dinner    = request.POST.get('dinner') == 'on'

        cost = 0
        if current_rate:
            if breakfast: cost += current_rate.breakfast
            if lunch:     cost += current_rate.lunch
            if dinner:    cost += current_rate.dinner

        member_mess, _ = MemberMess.objects.get_or_create(
            mess_name=mess.mess_name,
            defaults={
                'manager':   request.user,
                'mess_code': f"MESS{mess.id}",
                'address':   mess.address,
                'is_active': True,
            }
        )

        if existing_log:
            existing_log.breakfast = breakfast
            existing_log.lunch     = lunch
            existing_log.dinner    = dinner
            existing_log.meal_cost = cost
            existing_log.save()
            action_text = "updated"
            messages.success(request, 'Meal log updated!')
        else:
            MealLog.objects.create(
                member=request.user,
                mess=member_mess,
                log_date=today,
                breakfast=breakfast,
                lunch=lunch,
                dinner=dinner,
                meal_cost=cost,
            )
            action_text = "added"
            messages.success(request, 'Meal logged successfully!')

        meals = []
        if breakfast: meals.append("Breakfast")
        if lunch:     meals.append("Lunch")
        if dinner:    meals.append("Dinner")
        meal_str = ", ".join(meals) if meals else "No meals"
        Notification.objects.create(
            mess=mess,
            text=f"Manager {request.user.username}'s meal log for {today} has been {action_text}: {meal_str}.",
            notif_type="meal_log"
        )

        return redirect('manager_log_meal')

    recent_logs = MealLog.objects.filter(
        member=request.user
    ).order_by('-log_date')[:10]

    return render(request, 'managers/log_meal.html', {
        'mess':          mess,
        'today':         today,
        'rate':          current_rate,
        'existing_log':  existing_log,
        'recent_logs':   recent_logs,
        'unread_notifs': unread_notifs(mess),
    })
    
    
@manager_required
def notifications(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    notifs = mess.notifications.filter(
        notif_type__in=['manager_only', 'room_request', 'complaint']
    ).order_by('-created_at')

    notifs.update(is_read=True)

    return render(request, 'managers/notifications.html', {
        'mess':          mess,
        'notifications': notifs,
        'unread_notifs': 0,
    })
    
    
@manager_required
def view_complaints(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')
    f  = request.GET.get('filter', 'all')
    qs = mess.complaints.all().order_by('-submitted_at')
    if f == 'unread':
        qs = qs.filter(is_read=False)
    elif f == 'read':
        qs = qs.filter(is_read=True)
    return render(request, 'managers/complaints.html', {
        'mess':          mess,
        'complaints':    qs,
        'total':         mess.complaints.count(),
        'unread':        mess.complaints.filter(is_read=False).count(),
        'read':          mess.complaints.filter(is_read=True).count(),
        'f':             f,
        'unread_notifs': unread_notifs(mess),
    })


@manager_required
def mark_complaint_read(request, complaint_id):
    mess = get_mess(request)
    c    = get_object_or_404(Complaint, id=complaint_id, mess=mess)
    if request.method == 'POST':
        c.is_read = True
        c.save()
        if c.submitted_by:
            Notification.objects.create(
                recipient=c.submitted_by,
                text="Your complaint has been reviewed and acknowledged by the manager.",
                notif_type="complaint_feedback"
            )
    return redirect('view_complaints')
    
    
@manager_required
def manager_rotation(request):
    mess = get_mess(request)
    if not mess:
        return redirect('manager_dashboard')

    if request.method == 'POST':
        new_manager_id = request.POST.get('new_manager')
        term_months    = int(request.POST.get('term_months', 6))
        rotation_date  = request.POST.get('rotation_date')
        notes          = request.POST.get('notes', '').strip()
        new_mgr        = get_object_or_404(UserProfile, id=new_manager_id)
        ManagerRotation.objects.create(
            mess=mess, outgoing_manager=request.user.userprofile,
            incoming_manager=new_mgr, term_months=term_months,
            rotation_date=rotation_date, notes=notes
        )
        old_mgr      = mess.manager
        old_mgr.role = 'member'
        old_mgr.save()
        mess.manager = new_mgr
        mess.save()
        new_mgr.role = 'manager'
        new_mgr.save()
        Notification.objects.create(
            mess=mess,
            text=f"{new_mgr.user.username} is now the new manager.",
            notif_type="rotation"
        )
        messages.success(request, f"{new_mgr.user.username} is now the new manager!")
        return redirect('home')

    eligible = mess.members.filter(is_active=True).exclude(user=request.user.userprofile)
    history  = ManagerRotation.objects.filter(mess=mess).order_by('rotation_date')
    return render(request, 'managers/rotation.html', {
        'mess':          mess,
        'eligible':      eligible,
        'history':       history,
        'unread_notifs': unread_notifs(mess),
    })
    