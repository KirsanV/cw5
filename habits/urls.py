from django.urls import path
from . import views

app_name = 'habits'

urlpatterns = [
    path('', views.HabitListCreateView.as_view(), name='habit-list-create'),
    path('<int:pk>/', views.HabitRetrieveUpdateDestroyView.as_view(), name='habit-detail'),
    path('public/', views.PublicHabitListView.as_view(), name='public-habit-list'),
]
