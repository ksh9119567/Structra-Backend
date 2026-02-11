from rest_framework import serializers

from core.permissions import project
from app.tasks.models import Task

from app.projects.models import Project
from app.accounts.models import User
from core.permissions.base import get_project_role


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    parent_task = serializers.CharField(source="parent.title", read_only=True)
    assigned_to_email = serializers.EmailField(source="assigned_to.email", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    
    class Meta:
        model = Task
        fields = [
            "id", "project", "project_name", "parent", "parent_task", "title", "description",
            "start_date", "due_date", "status", "priority", "task_type", "assigned_to", "assigned_to_email", 
            "created_by_email"
        ]
        
class TaskCreateSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(write_only=True, required=True, allow_null=False)
    parent_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Task
        fields = [
            "title", "description", "project_id", "parent_id"
        ]
        
    def validate(self, attrs):
        request = self.context["request"]
        project_id = attrs.get("project_id")
        parent_id = attrs.get("parent_id", None)
        
        if parent_id:
            try:
                parent_task = Task.objects.get(id=parent_id)
                if parent_task.project.id != project_id:
                    raise serializers.ValidationError("Parent task must belong to the same project.")
            except Task.DoesNotExist:
                raise serializers.ValidationError("Parent task not found.")
            
            role = get_project_role(request.user, parent_task.project)
            if role not in ["OWNER", "MANAGER", "CONTRIBUTOR"]:
                raise serializers.ValidationError("You do not have permission to create a subtask in this project.")
            
            attrs["parent"] = parent_task
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project not found.")
        
        attrs["project"] = project
        
        role = get_project_role(request.user, project)
        if role not in ["OWNER", "MANAGER", "CONTRIBUTOR"]:
            raise serializers.ValidationError("You do not have permission to create a task in this project.")
        
        return attrs
    
    def create(self, validated_data):
        request = self.context["request"]
        task = Task.objects.create(created_by=request.user, **validated_data)
        
        return task
        

class TaskUpdateSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    
    class Meta:
        model = Task
        fields = [
            "title", "description", "start_date", "due_date", "status", "priority", "task_type", "assigned_to"
        ]
    
    def update(self, instance, validated_data):
        validated_data.pop('project', None)
        validated_data.pop('parent', None)
        validated_data.pop('created_by', None)
        user = self.context["request"].user
        
        if instance.assigned_to:
            # if request user is not creator or assigned_to, raise permission denied
            if user != instance.created_by and user != instance.assigned_to:
                raise serializers.ValidationError("You do not have permission to update this task.")
        else:
            if user != instance.created_by:
                raise serializers.ValidationError("You do not have permission to update this task.")
                
        # If assigned_to is being set, ensure the user is a member of the task's project
        assigned_user = validated_data.get('assigned_to', None)
        if assigned_user is not None:
            role = get_project_role(assigned_user, instance.project)
            if role not in ["OWNER", "MANAGER", "CONTRIBUTOR"]:
                raise serializers.ValidationError("User is not a member of the task's project.")

        return super().update(instance, validated_data)