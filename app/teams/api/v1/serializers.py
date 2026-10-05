from django.db import transaction

from rest_framework import serializers

from app.teams.models import Team, TeamMembership
from app.accounts.models import User
from app.organizations.models import Organization, OrganizationMembership
from app.organizations.models import Organization
from core.permissions.base import get_org_role, get_team_role
from core.permissions.resolver import team_member_admin_role
from core.constants.team_constant import TEAM_ROLES, TEAM_ROLE_HIERARCHY
from core.constants.org_constant import ORG_ROLE_HIERARCHY


class TeamSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    
    class Meta:
        model = Team
        fields = ["id", "name", "description", "organization", "organization_name", "created_by", 
                  "created_by_email", "member_count", "project_count", "created_at"]
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_project_count(self, obj):
        return obj.projects.count()
    
        
class TeamCreateSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Team
        fields = ["name", "description", "organization_id"]

    def validate(self, attrs):
        request = self.context["request"]
        org_id = attrs.get("organization_id", None)
        
        if org_id:
            try:
                org = Organization.objects.get(id=org_id, is_deleted=False)
            except Organization.DoesNotExist:
                raise serializers.ValidationError("Organization not found.")

            # Check Org permission (Admin or Owner)
            role = get_org_role(request.user, org)
            min_role = org.settings.create_team_min_role

            if ORG_ROLE_HIERARCHY.get(role, -1) < ORG_ROLE_HIERARCHY[min_role]:
                raise serializers.ValidationError("You do not have permission to create a team.")

            # Soft-deleted teams no longer count against the quota.
            if org.teams.filter(is_deleted=False).count() >= org.settings.max_teams:
                raise serializers.ValidationError("Organization has reached maximum team limit.")

            attrs["organization"] = org
            
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        org = validated_data.pop("organization", None)

        # All-or-nothing: never leave a team behind without its Owner membership.
        with transaction.atomic():
            team = Team.objects.create(created_by=request.user, **validated_data)

            if org:
                team.organization = org
                team.save()

            TeamMembership.objects.create(user=request.user, team=team, role="OWNER")
        return team


class TeamMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    
    class Meta:
        model = TeamMembership
        fields = ["user", "user_email", "role", "joined_at"]
        read_only_fields = ["joined_at"]
        
        
class TeamUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["name", "description"]
        

class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        request = self.context["request"]
        if request.user.email == value:
            raise serializers.ValidationError("You cannot invite yourself.")
        return value
    
    
class TeamMemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[r[0] for r in TEAM_ROLES])

    def validate(self, attrs):
        request = self.context["request"]
        team = self.context["team"]
        target_user = self.context["member_user"]

        # An org owner (governance backstop) acts with team-Owner authority.
        acting_role = team_member_admin_role(request.user, team)
        target_role = get_team_role(target_user, team)

        if target_role is None:
            raise serializers.ValidationError("User is not a member of this team.")

        new_role = attrs["role"]

        min_role = team.settings.update_member_min_role

        if TEAM_ROLE_HIERARCHY.get(acting_role, -1) < TEAM_ROLE_HIERARCHY[min_role]:
            raise serializers.ValidationError("You do not have permission to modify team members.")

        # Manager cannot change equal/higher roles
        if TEAM_ROLE_HIERARCHY[target_role] >= TEAM_ROLE_HIERARCHY[acting_role]:
            raise serializers.ValidationError("You cannot modify a member with equal or higher role.")

        if TEAM_ROLE_HIERARCHY[new_role] >= TEAM_ROLE_HIERARCHY[acting_role]:
            raise serializers.ValidationError("You cannot assign a role equal or higher than your own.")

        # Prevent downgrading the last manager
        if target_role == "MANAGER" and new_role != "MANAGER":
            manager_count = team.memberships.filter(role="MANAGER").count()
            if manager_count == 1:
                raise serializers.ValidationError("Cannot change the role of last remaining manager.")
            
        return attrs
