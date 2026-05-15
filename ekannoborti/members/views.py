from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import MessMember, MealRate, MealLog, MemberExpense, Deposit, Complaint


def get_mess(user):
    membership = MessMember.objects.filter(user=user, is_active=True).first()
    if membership:
        return membership.mess
    return None

@login_required
def member_dashboard(request):
    if request.user.userprofile.role != 'member':
        messages.error(request, 'Access denied.')
        return redirect('home')

    now = timezone.now()
    today = now.date()
    mess = get_mess(request.user)

    total_meal_cost = 0
    total_expense_share = 0
    total_deposited = 0
    today_log = None
    breakfast_count = 0
    lunch_count = 0
    dinner_count = 0
    total_meals = 0
    current_rate = None
    recent_expenses = []

    if mess:
        today_log = MealLog.objects.filter(member=request.user, log_date=today).first()

        logs_this_month = MealLog.objects.filter(
            member=request.user, mess=mess,
            log_date__month=now.month, log_date__year=now.year
        )
        total_meal_cost = sum(l.meal_cost for l in logs_this_month)
        breakfast_count = logs_this_month.filter(breakfast=True).count()
        lunch_count = logs_this_month.filter(lunch=True).count()
        dinner_count = logs_this_month.filter(dinner=True).count()
        total_meals = breakfast_count + lunch_count + dinner_count

        expenses = MemberExpense.objects.filter(
            mess=mess, expense_month=now.month, expense_year=now.year
        )
        total_expense_share = sum(e.share_amount for e in expenses)
        recent_expenses = expenses.order_by('-created_at')[:4]

        deposits = Deposit.objects.filter(member=request.user, mess=mess)
        total_deposited = sum(d.amount for d in deposits)

        current_rate = MealRate.objects.filter(mess=mess, is_current=True).first()

    total_due = (total_meal_cost + total_expense_share) - total_deposited

    return render(request, 'member/member_dashboard.html', {
        'mess': mess,
        'today_log': today_log,
        'total_meal_cost': total_meal_cost,
        'total_expense_share': total_expense_share,
        'total_deposited': total_deposited,
        'total_due': total_due,
        'total_meals': total_meals,
        'breakfast_count': breakfast_count,
        'lunch_count': lunch_count,
        'dinner_count': dinner_count,
        'current_rate': current_rate,
        'recent_expenses': recent_expenses,
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

    today = timezone.now().date()
    existing_log = MealLog.objects.filter(member=request.user, log_date=today).first()
    rate = MealRate.objects.filter(mess=mess, is_current=True).first()

    if request.method == 'POST':
        breakfast = request.POST.get('breakfast') == 'on'
        lunch = request.POST.get('lunch') == 'on'
        dinner = request.POST.get('dinner') == 'on'

        cost = 0
        if rate:
            if breakfast:
                cost += rate.breakfast_rate
            if lunch:
                cost += rate.lunch_rate
            if dinner:
                cost += rate.dinner_rate

        if existing_log:
            existing_log.breakfast = breakfast
            existing_log.lunch = lunch
            existing_log.dinner = dinner
            existing_log.meal_cost = cost
            existing_log.save()
            messages.success(request, 'Meal log updated!')
        else:
            MealLog.objects.create(
                member=request.user,
                mess=mess,
                log_date=today,
                breakfast=breakfast,
                lunch=lunch,
                dinner=dinner,
                meal_cost=cost,
            )
            messages.success(request, 'Meal logged successfully!')

        return redirect('log_meal')

    recent_logs = MealLog.objects.filter(
        member=request.user, mess=mess
    ).order_by('-log_date')[:10]

    return render(request, 'member/log_meal.html', {
        'existing_log': existing_log,
        'rate': rate,
        'today': today,
        'recent_logs': recent_logs,
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

    now = timezone.now()

    expenses = MemberExpense.objects.filter(
        mess=mess,
        expense_month=now.month,
        expense_year=now.year
    ).order_by('-created_at')

    my_deposits = Deposit.objects.filter(
        member=request.user, mess=mess
    ).order_by('-deposited_at')

    logs = MealLog.objects.filter(
        member=request.user, mess=mess,
        log_date__month=now.month, log_date__year=now.year
    )
    total_meal_cost = sum(l.meal_cost for l in logs)
    total_expense_share = sum(e.share_amount for e in expenses)
    total_deposited = sum(d.amount for d in my_deposits)
    total_due = (total_meal_cost + total_expense_share) - total_deposited

    return render(request, 'member/view_expenses.html', {
        'expenses': expenses,
        'my_deposits': my_deposits,
        'total_meal_cost': total_meal_cost,
        'total_expense_share': total_expense_share,
        'total_deposited': total_deposited,
        'total_due': total_due,
        'current_month': now.strftime('%B %Y'),
    })

@login_required
def file_complaint(request):
    if request.user.userprofile.role != 'member':
        messages.error(request, 'Access denied.')
        return redirect('home')

    mess = get_mess(request.user)
    if not mess:
        messages.error(request, 'You are not assigned to any mess yet.')
        return redirect('member_dashboard')

    if request.method == 'POST':
        complaint_text = request.POST.get('complaint_text', '').strip()
        is_anonymous = request.POST.get('is_anonymous') == 'on'

        if not complaint_text:
            messages.error(request, 'Complaint cannot be empty!')
            return render(request, 'member/file_complaint.html')

        Complaint.objects.create(
            member=request.user,
            mess=mess,
            complaint_text=complaint_text,
            is_anonymous=is_anonymous,
        )
        messages.success(request, 'Complaint submitted successfully!')
        return redirect('member_dashboard')

    return render(request, 'member/file_complaint.html')