import logging

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.filters import SearchFilter, OrderingFilter

from app.tasks.models import Task
from app.tasks.api.v1.serializers import (
    TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer
)
from app.tasks.services.task_service import delete_task
from app.tasks.filters import TaskFilter

from app.projects.models import Project

from core.pagination import StandardPagination
from core.permissions.project import IsProjectMember, IsProjectManager, IsProjectOwner
from core.utils import (
    get_project, get_task, get_all_task
)

logger = logging.getLogger(__name__)


class TaskAPI(viewsets.ViewSet):
    """
    Task API (v1)
    """
    queryset = Task.objects.all()
    pagination_class = StandardPagination()
    filterset_class = TaskFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "due_date", "priority"]
    
    def get_permissions(self):
        if self.action in ["list", "retrieve", "create", "update"]:
            permissions = [IsAuthenticated, IsProjectMember]
        elif self.action == "destroy":
            permissions = [IsAuthenticated, IsProjectOwner, IsProjectManager]
        else:
            permissions = [IsAuthenticated]
            
        return [permission() for permission in permissions]
    
    def get_serializer_class(self):
        if self.action == "create":
            return TaskCreateSerializer
        if self.action == "update":
            return TaskUpdateSerializer
        else:
            return TaskSerializer
    
    def apply_filters(self, request, queryset):
        django_filter = DjangoFilterBackend()
        queryset = django_filter.filter_queryset(request, queryset, self)
        
        search_filter = SearchFilter()
        queryset = search_filter.filter_queryset(request, queryset, self)
        
        ordering_filter = OrderingFilter()
        queryset = ordering_filter.filter_queryset(request, queryset, self)
        
        return queryset
        
    def list(self, request):
        project = get_project(request.query_params.get("project_id"))
        self.check_object_permissions(request, project)
        
        tasks = self.apply_filters(request, get_all_task(project))
        
        page = self.pagination_class.paginate_queryset(tasks, request)
        
        return self.pagination_class.get_paginated_response({
            "message": "Success",
            "data": TaskSerializer(page, many=True).data}
        )
    
    def create(self, request):
        self.check_object_permissions(request, serializer.validated_data["project"])
        
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data, 
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        
        task = serializer.save()
        
        return Response({
            "message": "Task created successfully",
            "data": TaskSerializer(task).data}, 
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request):
        task = get_task(request.query_params.get("task_id"))
        self.check_object_permissions(request, task.project)
        
        return Response({
            "message": "Success",
            "data": TaskSerializer(task).data}, 
            status=status.HTTP_200_OK
        )
    
    def update(self, request):
        task = get_task(request.query_params.get("task_id"))
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
        
        return Response({
            "message": "Task updated successfully",
            "data": TaskSerializer(task).data},
            status=status.HTTP_200_OK
        )
        
    def destroy(self, request):
        task = get_task(request.query_params.get("task_id"))
        self.check_object_permissions(request, task.project)
        
        delete_task(
            task=task, 
            performed_by=request.user
        )
        
        return Response(
            {"message": "Task deleted successfully"},
            status=status.HTTP_200_OK
        )
        
    
    
        
    

