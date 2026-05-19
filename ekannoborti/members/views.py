from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import MessInvitation, MealLog, Mess as MemberMess

from itertools import chain
from django.db.models import QuerySet

from managers.models import (
    Mess,
    MessMember,
    MealRate,
    Expense,
    Deposit,
    Notification,
)


def get_mess(user):
    membership = MessMember.objects.filter(
        user=user.userprofile, is_active=True
    ).first()
    if membership:
        return membership.mess
    return None


def get_my_member_obj(user, mess):
    return MessMember.objects.filter(
        user=user.userprofile, mess=mess, is_active=True
    ).first()


def get_member_mess(manager_mess):
    try:
        return MemberMess.objects.get(mess_name=manager_mess.mess_name)
    except MemberMess.DoesNotExist:
        return None


@login_required
def member_dashboard(request):
    if request.user.userprofile.role != 'member':
        messages.error(request, 'Access denied.')
        return redirect('home')

    now   = timezone.now()
    today = now.date()
    mess  = get_mess(request.user)

    total_meal_cost     = 0
    total_expense_share = 0
    total_deposited     = 0
    total_due           = 0
    total_meals         = 0
    breakfast_count     = 0
    lunch_count         = 0
    dinner_count        = 0
    today_log           = None
    current_rate        = None
    recent_expenses     = []

    if mess:
        now_month_logs  = MealLog.objects.filter(
            member=request.user,
            log_date__month=now.month,
            log_date__year=now.year
        )
        total_meal_cost = round(sum(l.meal_cost for l in now_month_logs), 2)
        total_meals     = now_month_logs.count()
        breakfast_count = now_month_logs.filter(breakfast=True).count()
        lunch_count     = now_month_logs.filter(lunch=True).count()
        dinner_count    = now_month_logs.filter(dinner=True).count()
        today_log       = MealLog.objects.filter(
            member=request.user, log_date=today
        ).first()

        active_count = mess.members.filter(is_active=True).count()
        expenses     = Expense.objects.filter(
            mess=mess,
            expense_month__year=now.year,
            expense_month__month=now.month
        )
        total_all_expenses  = sum(e.total_amount for e in expenses)
        total_expense_share = round(total_all_expenses / active_count, 2) if active_count else 0
        recent_expenses = expenses.order_by('-created_at')[:4]

        my_member = get_my_member_obj(request.user, mess)
        if my_member:
            my_deposits     = Deposit.objects.filter(mess=mess, member=my_member)
            total_deposited = round(sum(d.amount for d in my_deposits), 2)

        current_rate = mess.meal_rates.filter(is_active=True).first()

    total_due = round((total_meal_cost + total_expense_share) - total_deposited, 2)

    pending_invitation = MessInvitation.objects.filter(
        member=request.user,
        status='pending'
    ).first()

    return render(request, 'member/member_dashboard.html', {
        'mess':                mess,
        'pending_invitation':  pending_invitation,
        'today_log':           today_log,
        'total_meal_cost':     total_meal_cost,
        'total_expense_share': total_expense_share,
        'total_deposited':     total_deposited,
        'total_due':           total_due,
        'total_meals':         total_meals,
        'breakfast_count':     breakfast_count,
        'lunch_count':         lunch_count,
        'dinner_count':        dinner_count,
        'current_rate':        current_rate,
        'recent_expenses':     recent_expenses,
    })


@login_required
def log_meal(request):
    if request.user.userprofile.role != 'member':
        messages.error(request, 'Access denied.')
        return redirect('home')

    mess = get_mess(request.user)
    if not mess:
        messages.error(request, 'You are not assigned to any mess yet.')
        return redirect('member_dashboard')

    today        = timezone.now().date()
    current_rate = mess.meal_rates.filter(is_active=True).first()
    existing_log = MealLog.objects.filter(
        member=request.user, log_date=today
    ).first()

    if request.method == 'POST':
        breakfast = request.POST.get('breakfast') == 'on'
        lunch     = request.POST.get('lunch') == 'on'
        dinner    = request.POST.get('dinner') == 'on'

        cost = 0.0
        if current_rate:
            if breakfast: cost += current_rate.breakfast
            if lunch:     cost += current_rate.lunch
            if dinner:    cost += current_rate.dinner
        cost = round(cost, 2)

        member_mess = get_member_mess(mess)

        if not member_mess:
            member_mess = MemberMess.objects.create(
                mess_name=mess.mess_name,
                manager=request.user,
                mess_code=f"MESS{mess.id}",
                address=mess.address,
                is_active=True,
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
            text=f"{request.user.username}'s meal log for {today} has been {action_text}: {meal_str}.",
            notif_type="meal_log"
        )

        return redirect('log_meal')

    recent_logs = MealLog.objects.filter(
        member=request.user
    ).order_by('-log_date')[:10]

    return render(request, 'member/log_meal.html', {
        'mess':         mess,
        'today':        today,
        'rate':         current_rate,
        'existing_log': existing_log,
        'recent_logs':  recent_logs,
    })


@login_required
def view_expenses(request):
    if request.user.userprofile.role != 'member':
        messages.error(request, 'Access denied.')
        return redirect('home')

    mess = get_mess(request.user)
    if not mess:
        messages.error(request, 'You are not assigned to any mess yet.')
        return redirect('member_dashboard')

    now          = timezone.now()
    active_count = mess.members.filter(is_active=True).count()

    expenses_qs = Expense.objects.filter(
        mess=mess,
        expense_month__year=now.year,
        expense_month__month=now.month
    ).order_by('-created_at')

    expenses = []
    for e in expenses_qs:
        e.share_amount = round(e.total_amount / active_count, 2) if active_count else 0
        expenses.append(e)

    total_expense_share = round(sum(e.total_amount for e in expenses_qs) / active_count, 2) if active_count else 0

    my_member       = get_my_member_obj(request.user, mess)
    my_deposits     = []
    total_deposited = 0

    if my_member:
        my_deposits = Deposit.objects.filter(
            mess=mess, member=my_member
        ).order_by('-deposit_date')
        total_deposited = round(sum(d.amount for d in my_deposits), 2)

    meal_logs = MealLog.objects.filter(
        member=request.user,
        log_date__month=now.month,
        log_date__year=now.year
    )
    total_meal_cost = round(sum(l.meal_cost for l in meal_logs), 2)
    total_due = round((total_expense_share + total_meal_cost) - total_deposited, 2)

    return render(request, 'member/view_expenses.html', {
        'expenses':            expenses,
        'my_deposits':         my_deposits,
        'total_meal_cost':     total_meal_cost,
        'total_expense_share': total_expense_share,
        'total_deposited':     total_deposited,
        'total_due':           total_due,
        'current_month':       now.strftime('%B %Y'),
    })



@login_required
def view_invitations(request):
    invitations = MessInvitation.objects.filter(
        member=request.user
    ).order_by('-created_at')

    return render(request, 'member/invitations.html', {
        'invitations': invitations,
    })


@login_required
def respond_invitation(request, invite_id):
    invitation = get_object_or_404(
        MessInvitation,
        id=invite_id,
        member=request.user,
        status='pending'
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'accept':
            invitation.status = 'accepted'
            invitation.save()

            try:
                mess_obj       = Mess.objects.get(mess_name=invitation.mess_name)
                target_profile = request.user.userprofile

                member_obj, created = MessMember.objects.get_or_create(
                    user=target_profile,
                    mess=mess_obj,
                    defaults={
                        'joined_date': timezone.now().date(),
                        'is_active':   True,
                    }
                )
                if not created:
                    member_obj.is_active = True
                    member_obj.save()

                MemberMess.objects.get_or_create(
                    mess_name=invitation.mess_name,
                    defaults={
                        'manager':   request.user,
                        'mess_code': f"MESS{mess_obj.id}",
                        'address':   invitation.mess_address,
                        'is_active': True,
                    }
                )

            except Mess.DoesNotExist:
                messages.error(request, 'Mess not found. Please contact your manager.')
                return redirect('view_invitations')

            messages.success(request, f"You have joined '{invitation.mess_name}'!")

        elif action == 'reject':
            invitation.status = 'rejected'
            invitation.save()
            messages.info(request, "Invitation rejected.")

    return redirect('view_invitations')