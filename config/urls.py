from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include("app.accounts.urls")),
    path('api/organizations/', include("app.organizations.urls")),
    path('api/teams/', include("app.teams.urls")),
]
