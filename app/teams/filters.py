import django_filters

from app.teams.models import Team, TeamMembership


class TeamFilter(django_filters.FilterSet):
    class Meta:
        model = Team
        fields = []
        
        
class TeamMembershipFilter(django_filters.FilterSet):
    role = django_filters.CharFilter()
    
    class Meta:
        model = TeamMembership
        fields = ["role"]