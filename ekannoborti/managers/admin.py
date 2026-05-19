from django.contrib import admin
from .models import Mess, MessMember, MealRate, Expense, Deposit

admin.site.register(Mess)
admin.site.register(MessMember)
admin.site.register(MealRate)
admin.site.register(Expense)
admin.site.register(Deposit)
