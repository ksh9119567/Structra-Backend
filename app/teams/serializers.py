from rest_framework import serializers

from .models import Team, TeamMembership
from app.accounts.models import User
from app.organizations.models import Organization, OrganizationMembership
from app.organizations.models import Organization
from core.permissions.base import get_org_role, get_team_role
from core.constants import TEAM_ROLES, TEAM_ROLE_HIERARCHY


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
        
        if not org_id:
            return attrs

        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            raise serializers.ValidationError("Organization not found.")

        # Check Org permission (Admin or Owner)
        role = get_org_role(request.user, org)
        if role not in ["OWNER", "ADMIN"]:
            raise serializers.ValidationError("You do not have permission to create a team.")

        attrs["organization"] = org
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        org = validated_data.pop("organization", None)

        team = Team.objects.create(created_by=request.user, **validated_data)

        if org:
            team.organization = org
            team.save()

        TeamMembership.objects.create(user=request.user, team=team, role="MANAGER")
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
    role = serializers.ChoiceField(choices=[r[0] for r in TEAM_ROLES], required=False)

    def validate(self, attrs):
        request = self.context["request"]
        team = self.context["team"]
        target_user = self.context["member_user"]

        acting_role = get_team_role(request.user, team)
        target_role = get_team_role(target_user, team)

        new_role = attrs.get("role")
        
        # Only MANAGER or higher roles can modify
        if TEAM_ROLE_HIERARCHY[acting_role] < TEAM_ROLE_HIERARCHY["MANAGER"]:
            raise serializers.ValidationError("Only Team Manager can modify team members.")

        # Manager cannot change equal/higher roles
        if target_role and TEAM_ROLE_HIERARCHY[target_role] >= TEAM_ROLE_HIERARCHY[acting_role]:
            raise serializers.ValidationError("You cannot modify a member with equal or higher role.")

        # Prevent downgrading the last manager
        if target_role == "MANAGER" and new_role != "MANAGER":
            manager_count = team.memberships.filter(role="MANAGER").count()
            if manager_count == 1:
                raise serializers.ValidationError("Cannot remove the last manager.")
            
        return attrs
