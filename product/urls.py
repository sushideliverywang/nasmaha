
from django.urls import path
from . import views


urlpatterns = [
    path('brand/', views.brand_list, name='brand_list'),
    path('brand/add/', views.brand_add, name='brand_add'),
    path('brand/edit/<int:pk>/', views.brand_edit, name='brand_edit'),
    path('brand/delete/<int:pk>/', views.brand_delete, name='brand_delete'),

    path('category/', views.category_list, name='category_list'),
    path('category/add/', views.category_add, name='category_add'),
    path('category/edit/<int:pk>/', views.category_edit, name='category_edit'),
    path('category/delete/<int:pk>/', views.category_delete, name='category_delete'),

    path('product-model/', views.product_model_list, name="product_model_list"),
    path('product-model/add/', views.product_model_add, name="product_model_add"),
    path('product-model/edit/<int:pk>', views.product_model_edit, name="product_model_edit"),
    path('product-model/delete/<int:pk>', views.product_model_delete, name="product_model_delete"),

    path('scraper/', views.scraper_view, name='scraper'),
    path('scraper/update-model/', views.scraper_update_model, name='scraper_update_model'),
]