from django.urls import path
from Scheduler import views

urlpatterns = [
    path('', views.index, name='index'),
    path('loginUser/', views.loginUser, name='loginUser'),
    path('logout/', views.logout, name='logout'),
    path('admin/', views.admin, name='admin'),
    path('adminPage/', views.adminPage, name='adminPage'),
    path('scheduleTest/', views.scheduleTest, name='scheduleTest'),
    path('buildEvent/', views.buildEvent, name='buildEvent'),
    path('checkProgress/', views.checkProgress, name='checkProgress')
]
