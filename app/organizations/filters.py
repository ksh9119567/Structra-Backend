import django_filters

from app.organizations.models import Organization, OrganizationMembership


class OrganizationFilter(django_filters.FilterSet):
    class Meta:
        model = Organization
        fields = []


class OrganizationMembershipFilter(django_filters.FilterSet):
    role = django_filters.CharFilter()
    
    class Meta:
        model = OrganizationMembership
        fields = ["role"]