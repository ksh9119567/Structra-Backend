from rest_framework import serializers

from core.permissions import project
from tasks.models import Task

from app.projects.models import Project
from app.accounts.models import User
from core.permissions.base import get_project_role


class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    parent_task = serializers.CharField(source="parent.title", read_only=True)
    assigned_to = serializers.EmailField(source="assigned_to.email", read_only=True)
    created_by = serializers.EmailField(source="created_by.email", read_only=True)
    
    class Meta:
        model = Task
        fields = [
            "id", "project", "project_name", "parent", "parent_task", "title", "description",
            "start_date", "due_date", "status", "priority", "task_type", "assigned_to", "created_by"
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
    class Meta:
        model = Task
        fields = [
            "title", "description", "start_date", "due_date", "status", "priority", "task_type", "assigned_to"
        ]