from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.api.views import ActivityLogViewSet

router = DefaultRouter()
router.register(r'activity-logs', ActivityLogViewSet, basename='activity-log')

urlpatterns = [
    path('', include(router.urls)),
]
