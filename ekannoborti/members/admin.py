from django.contrib import admin
from .models import Mess, MessMember, MealRate, MealLog, MemberExpense, Deposit, Complaint

admin.site.register(Mess)
admin.site.register(MessMember)
admin.site.register(MealRate)
admin.site.register(MealLog)
admin.site.register(MemberExpense)
admin.site.register(Deposit)
admin.site.register(Complaint)
