import logging

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from tasks.models import Task
from app.tasks.api.v1.serializers import (
    TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer
)
from app.tasks.services.task_service import delete_task

from app.projects.models import Project
from core.pagination import StandardPagination
from core.permissions.project import IsProjectMember
from core.utils import (
    get_project, get_task
)

logger = logging.getLogger(__name__)


class TaskAPI(viewsets.ViewSet):
    """
    Task API (v1)
    """
    queryset = Task.objects.all()
    pagination_class = StandardPagination()
    
    def get_permissions(self):
        if self.action in ["list", "retrieve", "create", "update", "destroy"]:
            permissions = [IsAuthenticated, IsProjectMember]
        else:
            permissions = [IsAuthenticated]
            
        return [permission() for permission in permissions]
    
    def get_serializer_class(self):
        if self.action == "create":
            return TaskCreateSerializer
        elif self.action == "update":
            return TaskUpdateSerializer
    
    def list(self, request):
        project = get_project(request.query_params.get("project_id"))
        self.check_object_permissions(request, project)
        
        tasks = Task.objects.filter(project = project).order_by("-created_at")
        
        page = self.pagination_class.paginate_queryset(tasks, request)
        
        return self.pagination_class.get_paginated_response(
            TaskSerializer(page, many=True).data, 
            status=status.HTTP_200_OK
        )
    
    def create(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data, 
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        
        self.check_object_permissions(request, serializer.validated_data["project"])
        
        task = serializer.save()
        
        return Response(
            TaskSerializer(task).data, 
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request):
        task = get_task(request.query_params.get("task_id"))
        self.check_object_permissions(request, task.project)
        
        return Response(
            TaskSerializer(task).data, 
            status=status.HTTP_200_OK
        )
    
    def update(self, request):
        task = get_task(request.data.get("task_id"))
        self.check_object_permissions(request, task.project)
        
        serializer_class = TaskUpdateSerializer
        serializer = serializer_class(
            task,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            TaskSerializer(task).data,
            status=status.HTTP_200_OK
        )
        
    def destroy(self, request):
        task = get_task(request.data.get("task_id"))
        self.check_object_permissions(request, task.project)
        
        delete_task(
            task=task, 
            performed_by=request.user
        )
        
        return Response(
            {"message": "Task deleted successfully"},
            status=status.HTTP_200_OK
        )
        
    
    
        
    

