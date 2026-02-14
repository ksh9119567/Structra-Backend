from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include("app.accounts.api.v1.urls")),
    path('api/v1/organizations/', include("app.organizations.api.v1.urls")),
    path('api/v1/teams/', include("app.teams.api.v1.urls")),
    path('api/v1/projects/', include("app.projects.api.v1.urls")),
    path('api/v1/tasks/', include("app.tasks.api.v1.urls")),
    path('api/v1/', include("core.api.urls")),  # Activity logs API
]
