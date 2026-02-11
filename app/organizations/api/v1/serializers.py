from rest_framework import serializers

from app.organizations.models import Organization, OrganizationMembership
from core.constants import ORG_ROLE_HIERARCHY
from core.permissions.base import get_org_role

class OrganizationSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    team_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = ["id", "name", "owner", "owner_email", "member_count", "team_count", "project_count"]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_team_count(self, obj):
        return obj.teams.count()

    def get_project_count(self, obj):
        return obj.projects.count()

    def get_owner_email(self, obj):
        return obj.owner.email
                
class OrganizationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name"]

    def validate_name(self, value):
        if Organization.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Organization with this name already exists.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        org = Organization.objects.create(owner=user, **validated_data)
        OrganizationMembership.objects.create(user=user, organization=org, role="OWNER")
        return org


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name"]   # only updatable field
    
    def validate_name(self, value):
        # Allow same name if org not changing
        instance = self.instance
        if Organization.objects.filter(name__iexact=value).exclude(id=instance.id).exists():
            raise serializers.ValidationError("Org with this name already exists.")
        return value


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ["user", "user_email", "role", "joined_at"]
        read_only_fields = ["joined_at"]


class OrganizationMemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["OWNER", "ADMIN", "MANAGER", "MEMBER", "VIEWER"])

    def validate(self, attrs):
        request = self.context["request"]
        acting_user = request.user
        target_user = self.context["member_user"]
        organization = self.context["organization"]

        acting_role = get_org_role(acting_user, organization)
        target_role = get_org_role(target_user, organization)
        new_role = attrs["role"]

        # Prevent lower rank editing higher rank
        if ORG_ROLE_HIERARCHY[acting_role] <= ORG_ROLE_HIERARCHY[target_role]:
            raise serializers.ValidationError("You cannot modify a user with equal or higher role.")

        # Prevent promoting someone above you
        if ORG_ROLE_HIERARCHY[new_role] >= ORG_ROLE_HIERARCHY[acting_role]:
            raise serializers.ValidationError("You cannot assign a role equal or higher than your own.")

        return attrs


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        request = self.context["request"]
        if request.user.email == value:
            raise serializers.ValidationError("You cannot invite yourself.")
        return value
