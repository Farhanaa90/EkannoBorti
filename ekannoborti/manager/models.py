from django.db import models
from users.models import UserProfile


class Mess(models.Model):
    manager = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='managed_messes')
    mess_name = models.CharField(max_length=200)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.mess_name


class MessMember(models.Model):
    mess = models.ForeignKey(Mess, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='mess_memberships')
    joined_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.mess.mess_name}"

    def total_due(self):
        from django.db.models import Sum
        total_expense = Expense.objects.filter(mess=self.mess).aggregate(
            total=Sum('total_amount'))['total'] or 0
        active_count = self.mess.members.filter(is_active=True).count()
        my_share = round(total_expense / active_count, 2) if active_count else 0
        my_deposits = self.deposits.aggregate(total=Sum('amount'))['total'] or 0
        return round(my_share - my_deposits, 2)


class MealRate(models.Model):
    mess = models.ForeignKey(Mess, on_delete=models.CASCADE, related_name='meal_rates')
    breakfast = models.FloatField(default=0)
    lunch = models.FloatField(default=0)
    dinner = models.FloatField(default=0)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def daily_total(self):
        return self.breakfast + self.lunch + self.dinner

    def __str__(self):
        return f"{self.mess.mess_name} - Meal Rate"


class Expense(models.Model):
    mess = models.ForeignKey(Mess, on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    total_amount = models.FloatField()
    expense_month = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def per_member_share(self):
        count = self.mess.members.filter(is_active=True).count()
        return round(self.total_amount / count, 2) if count else 0

    def __str__(self):
        return f"{self.title} - {self.total_amount}"


class Deposit(models.Model):
    mess = models.ForeignKey(Mess, on_delete=models.CASCADE, related_name='deposits')
    member = models.ForeignKey(MessMember, on_delete=models.CASCADE, related_name='deposits')
    amount = models.FloatField()
    deposit_date = models.DateField()
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.user.username} - {self.amount}"




