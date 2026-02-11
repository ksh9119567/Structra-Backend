import django_filters

from app.organizations.models import OrganizationMembership

class OrganizationMembershipFilter(django_filters.FilterSet):
    role = django_filters.CharFilter()
    
    class Meta:
        model = OrganizationMembership
        fields = ["role"]