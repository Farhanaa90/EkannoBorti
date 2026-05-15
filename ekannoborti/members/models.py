from django.db import models
from django.contrib.auth.models import User


class Mess(models.Model):
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_mess')
    mess_name = models.CharField(max_length=100)
    mess_code = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.mess_name


class MessMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mess_memberships')
    mess = models.ForeignKey(Mess, on_delete=models.CASCADE, related_name='members')
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    room_number = models.CharField(max_length=10, blank=True)

    class Meta:
        unique_together = ['user', 'mess']

    def __str__(self):
        return f"{self.user.username} in {self.mess.mess_name}"


class MealRate(models.Model):
    mess = models.ForeignKey(Mess, on_delete=models.CASCADE, related_name='meal_rates')
    breakfast_rate = models.FloatField(default=0)
    lunch_rate = models.FloatField(default=0)
    dinner_rate = models.FloatField(default=0)
    start_date = models.DateField()
    is_current = models.BooleanField(default=True)
    set_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Rate from {self.start_date}"


class MealLog(models.Model):
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_logs')
    mess = models.ForeignKey(Mess, on_delete=models.CASCADE, related_name='meal_logs')
    log_date = models.DateField()
    breakfast = models.BooleanField(default=False)
    lunch = models.BooleanField(default=False)
    dinner = models.BooleanField(default=False)
    meal_cost = models.FloatField(default=0)

    class Meta:
        unique_together = ['member', 'log_date']

    def __str__(self):
        return f"{self.member.username} - {self.log_date}"


class MemberExpense(models.Model):
    mess = models.ForeignKey(Mess, on_delete=models.CASCADE, related_name='expenses')
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_expenses')
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    total_amount = models.FloatField()
    share_amount = models.FloatField(default=0)
    expense_month = models.IntegerField()
    expense_year = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.expense_month}/{self.expense_year}"


class Deposit(models.Model):
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposits')
    mess = models.ForeignKey(Mess, on_delete=models.CASCADE, related_name='deposits')
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recorded_deposits')
    amount = models.FloatField()
    note = models.TextField(blank=True)
    deposited_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.username} deposited {self.amount}"


class MessInvitation(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    mess_name  = models.CharField(max_length=200)
    mess_address = models.CharField(max_length=300, blank=True)
    manager_username = models.CharField(max_length=150)
    member     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invitations')
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def str(self):
        return f"{self.manager_username} invited {self.member.username} to {self.mess_name}"
