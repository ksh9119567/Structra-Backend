from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include("app.accounts.urls")),
    path('api/organizations/', include("app.organizations.api.v1.urls")),
    path('api/teams/', include("app.teams.api.v1.urls")),
    path('api/projects/', include("app.projects.api.v1.urls"))
]
