from rest_framework import serializers

from app.governance.models import OrganizationSettings, TeamSettings, ProjectSettings

from core.constants import org_constant, team_constant, project_constant

class OrgSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationSettings
        fields = '__all__'
        

class OrgSettingsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationSettings
        fields = '__all__'
        
    def validate(self, attrs):
        for field_name, new_value in attrs.items():

            # derive action name from field
            action_name = field_name.replace("_min_role", "")

            if action_name not in org_constant.ORG_ACTION_POLICIES:
                continue

            policy = org_constant.ORG_ACTION_POLICIES[action_name]

            system_min = policy["system_min_role"]
            system_max = policy["system_max_role"]

            if org_constant.ORG_ROLE_HIERARCHY[new_value] < org_constant.ORG_ROLE_HIERARCHY[system_min]:
                raise serializers.ValidationError(
                    f"{field_name} cannot be lower than {system_min}"
                )

            if org_constant.ORG_ROLE_HIERARCHY[new_value] > org_constant.ORG_ROLE_HIERARCHY[system_max]:
                raise serializers.ValidationError(
                    f"{field_name} cannot be higher than {system_max}"
                )

        return attrs


class TeamSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamSettings
        fields = '__all__'
        
        
class TeamSettingsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamSettings
        fields = [
            "invite_member_min_role",
            "update_member_min_role",
            "remove_member_min_role",
            "create_project_min_role",
        ]
        
    def validate(self, attrs):
        for field_name, new_value in attrs.items():
            
            action_name = field_name.replace("_min_role", "")
            if action_name not in team_constant.TEAM_ACTION_POLICIES:
                continue
            
            policy = team_constant.TEAM_ACTION_POLICIES[action_name]

            system_min = policy["system_min_role"]
            system_max = policy["system_max_role"]

            if team_constant.TEAM_ROLE_HIERARCHY[new_value] < team_constant.TEAM_ROLE_HIERARCHY[system_min]:
                raise serializers.ValidationError(
                    f"{field_name} cannot be lower than {system_min}"
                )

            if team_constant.TEAM_ROLE_HIERARCHY[new_value] > team_constant.TEAM_ROLE_HIERARCHY[system_max]:
                raise serializers.ValidationError(
                    f"{field_name} cannot be higher than {system_max}"
                )
                
        return attrs
    
        
class ProjectSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSettings
        fields = '__all__'
        

class ProjectSettingsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSettings
        fields = [
            "invite_member_min_role",
            "update_member_min_role",
            "remove_member_min_role",
            "create_task_min_role",
            "update_task_min_role",
            "delete_task_min_role",
        ]
        
    def validate(self, attrs):
        for field_name, new_value in attrs.items():
            
            action_name = field_name.replace("_min_role", "")
            if action_name not in project_constant.PROJECT_ACTION_POLICIES:
                continue
            
            policy = project_constant.PROJECT_ACTION_POLICIES[action_name]

            system_min = policy["system_min_role"]
            system_max = policy["system_max_role"]

            if project_constant.PROJECT_ROLE_HIERARCHY[new_value] < project_constant.PROJECT_ROLE_HIERARCHY[system_min]:
                raise serializers.ValidationError(
                    f"{field_name} cannot be lower than {system_min}"
                )

            if project_constant.PROJECT_ROLE_HIERARCHY[new_value] > project_constant.PROJECT_ROLE_HIERARCHY[system_max]:
                raise serializers.ValidationError(
                    f"{field_name} cannot be higher than {system_max}"
                )
                
        return attrs