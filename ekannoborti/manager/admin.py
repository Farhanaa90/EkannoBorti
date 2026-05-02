from django.contrib import admin
from .models import Mess, MessMember, MealRate, Expense, Deposit, Complaint, ManagerRotation, Notification

admin.site.register(Mess)
admin.site.register(MessMember)
admin.site.register(MealRate)
admin.site.register(Expense)
admin.site.register(Deposit)
admin.site.register(Complaint)
admin.site.register(ManagerRotation)
admin.site.register(Notification)