import django_filters

from app.teams.models import TeamMembership

class TeamMembershipFilter(django_filters.FilterSet):
    role = django_filters.CharFilter()
    
    class Meta:
        model = TeamMembership
        fields = ["role"]