import logging

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.decorators import action

from projects.models import Project
from serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectMembershipSerializer, ProjectUpdateSerializer, 
    ProjectMemberUpdateSerializer, InviteMemberSerializer,
)

from app.accounts.models import User
from core.utils import (
    get_user, get_project, get_all_project_memberships,
)

from core.permissions.project import IsProjectMember
from core.permissions.combined import (
    IsOrgOwnerOrProjectManager, IsOrgOwnerOrProjectOwner,
)

from services.invite_token_service import verify_invite_token
from projects.services.project_invite_service import send_project_invite
from projects.services.project_membership_service import (
    add_project_member, remove_project_member, self_remove_project_member, update_project_member_role,
)
from projects.services.project_service import (
    transfer_project_ownership, delete_project,
)

logger = logging.getLogger(__name__)


class ProjectAPI(viewsets.ModelViewSet):
    """
    Project API (v1)
    """
    queryset = Project.objects.all()

    def get_permissions(self):
        if self.action in ["list", "create"]:
            permissions = [IsAuthenticated]

        elif self.action in ["transfer_ownership", "destroy"]:
            permissions = [IsAuthenticated, IsOrgOwnerOrProjectOwner]

        elif self.action in ["update", "send_invite", "add_member", "update_member", "remove_member"]:
            permissions = [IsAuthenticated, IsOrgOwnerOrProjectManager]

        elif self.action == ["retrieve", "members", "self_remove_member"]:
            permissions = [IsAuthenticated, IsProjectMember]

        else:
            permissions = [IsAuthenticated]

        return [permission() for permission in permissions]
    
    def get_serializer_class(self):
        if self.action == "create":
            return ProjectCreateSerializer
        if self.action == "update":
            return ProjectUpdateSerializer
        if self.action == "send_invite":
            return InviteMemberSerializer
        if self.action == "update_member":
            return ProjectMemberUpdateSerializer

    def list(self, request):
        projects = Project.objects.filter(
            members=request.user
        ).distinct()

        return Response(ProjectSerializer(projects, many=True).data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        project = serializer.save()
        return Response(
            ProjectSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request):
        project = get_project(request.query_params.get("project_id"))
        self.check_object_permissions(request, project)

        return Response(
            {"message": "Success", "data": ProjectSerializer(project).data},
            status=status.HTTP_200_OK,
        )

    def update(self, request):
        project = get_project(request.data.get("project_id"))
        self.check_object_permissions(request, project)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            project,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Project updated successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    
    def destroy(self, request):
        project = get_project(request.data.get("project_id"))
        self.check_object_permissions(request, project)

        delete_project(
            project=project,
            performed_by=request.user,
        )

        return Response(
            {"message": "Project deleted successfully"},
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------
    # Custom Actions
    # --------------------------------------------------
    @action(detail=True, methods=["get"])
    def members(self, request):
        project_id = request.query_params.get("project_id")
        project = get_project(project_id)

        self.check_object_permissions(request, project)

        members = get_all_project_memberships(project_id)

        return Response(
            {"message": "Success", "data": ProjectMembershipSerializer(members, many=True).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"])
    def self_remove_member(self, request):
        project = get_project(request.data.get("project_id"))
        self.check_object_permissions(request, project)

        self_remove_project_member(
            project=project,
            user=request.user,
        )

        return Response(
            {"message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def send_invite(self, request):
        project = get_project(request.data.get("project_id"))
        self.check_object_permissions(request, project)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = get_user(serializer.validated_data["email"], kind="email")
        if not user:
            raise NotFound("User not found")

        invite_token = send_project_invite(
            project=project,
            user=user,
            invited_by=request.user,
            role=request.data.get("role", "MEMBER"),
        )

        return Response(
            {"message": "Invite sent", "invite_token": invite_token},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def add_member(self, request):
        project = get_project(request.data.get("project_id"))
        self.check_object_permissions(request, project)

        user_id = verify_invite_token(
            invite_type="project",
            token=request.data.get("invite_token"),
        )
        if not user_id:
            raise ValidationError("Invalid invite token")

        user = User.objects.get(id=user_id)

        membership = add_project_member(
            project=project,
            user=user,
            role=request.data.get("role", "MEMBER"),
        )

        return Response(
            ProjectMembershipSerializer(membership).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def update_member(self, request):
        project = get_project(request.data.get("project_id"))
        self.check_object_permissions(request, project)

        target_user = get_user(request.data.get("email"), kind="email")
        if not target_user:
            raise NotFound("User not found")

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data={"role": request.data.get("role")},
            context={
                "request": request,
                "member_user": target_user,
                "project": project,
            },
        )
        serializer.is_valid(raise_exception=True)

        membership = update_project_member_role(
            project=project,
            user=target_user,
            role=serializer.validated_data["role"],
        )

        return Response(
            {
                "message": "Project member updated successfully",
                "data": ProjectMembershipSerializer(membership).data,
            },
            status=status.HTTP_200_OK,
        )
    @action(detail=True, methods=["delete"])
    def remove_member(self, request):
        project = get_project(request.data.get("project_id"))
        self.check_object_permissions(request, project)

        user = get_user(request.data.get("email"), kind="email")
        if not user:
            raise NotFound("User not found")

        remove_project_member(
            project=project,
            user=user,
        )

        return Response(
            {"message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def transfer_ownership(self, request):
        project = get_project(request.data.get("project_id"))
        self.check_object_permissions(request, project)

        new_owner = get_user(request.data.get("email"), kind="email")
        if not new_owner:
            raise NotFound("User not found")

        transfer_project_ownership(
            project=project,
            new_owner=new_owner,
            performed_by=request.user,
        )

        return Response(
            {"message": "Project owner updated successfully"},
            status=status.HTTP_200_OK,
        )

