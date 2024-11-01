from django.contrib import admin
from .models import Brand, Category, ProductModel, ProductImage, Spec, ProductSpec
# Register your models here.

admin.site.register(Brand)
admin.site.register(Category)
admin.site.register(Spec)
admin.site.register(ProductSpec)


class ProductImageInline(admin.TabularInline):  # You can use TabularInline or StackedInline
    model = ProductImage
    extra = 1  # Allows one extra image field to appear for new uploads by default

class ProductModelAdmin(admin.ModelAdmin):
    list_display = ('model_number',)  # Customize how the list of products will be displayed in the admin
    inlines = [ProductImageInline]  # Include the inline form for ProductImage

admin.site.register(ProductModel, ProductModelAdmin)
