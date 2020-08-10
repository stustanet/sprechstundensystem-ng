from django.contrib import admin

# Register your models here.
from management import models

admin.site.register(models.Settings)
admin.site.register(models.Admin)
admin.site.register(models.Appointment)
