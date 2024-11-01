from django.contrib import admin

# Register your models here.

from .models import  Vendor, InventoryItem

admin.site.register(Vendor)
admin.site.register(InventoryItem)
