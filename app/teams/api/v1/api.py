import logging

from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.decorators import action

from app.teams.models import Team
from app.teams.api.v1.serializers import (
    TeamSerializer, TeamCreateSerializer, TeamMembershipSerializer, TeamUpdateSerializer, 
    TeamMemberUpdateSerializer, InviteMemberSerializer,
)

from app.accounts.models import User
from core.utils import (
    get_user, get_team, get_all_team_memberships, get_team_membership,
)
from core.permissions.team import IsTeamMember, IsTeamManager
from core.permissions.combined import IsOrgOwnerOrTeamManager

from services.invite_token_service import verify_invite_token
from app.teams.services.team_invite_service import send_team_invite
from app.teams.services.team_membership_service import (
    add_team_member, remove_team_member, self_remove_team_member, update_team_member_role,
)
from app.teams.services.team_service import (
    transfer_team_ownership, delete_team,
)

logger = logging.getLogger(__name__)


class TeamAPI(viewsets.ViewSet):
    """
    Team API (v1)
    """
    queryset = Team.objects.all()
    
    def get_permission(self):
        if self.action in ["list", "create", "retrieve"]:
            permissions = [IsAuthenticated]
        elif self.action in ["members", "self_remove_member"]:
            permissions = [IsAuthenticated, IsTeamMember]
        elif self.action in ["update", "send_invite", "add_member", "update_member", "remove_member", "delete"]:
            permissions = [IsAuthenticated, IsOrgOwnerOrTeamManager]
        elif self.action in ["transfer_manager"]:
            permissions = [IsAuthenticated, IsTeamManager]
        else:
            permissions = [IsAuthenticated]
        
        return [permission() for permission in permissions]
    
    def get_serializer_class(self):
        if self.action == "create":
            return TeamCreateSerializer
        if self.action == "send_invite":
            return InviteMemberSerializer
        if self.action == "update":
            return TeamUpdateSerializer
        if self.action == "update_member":
            return TeamMemberUpdateSerializer

    def list(self, request):
        teams = Team.objects.filter(memberships__user=request.user)
        
        return Response(
            {"message": "Success", "data": TeamSerializer(teams, many=True).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        team = serializer.save()
        return Response(
            {"message": "Team created successfully", "data": TeamSerializer(team).data},
            status=status.HTTP_201_CREATED,
        )
    
    def retrieve(self, request):
        team = get_team(request.query_params.get("team_id"))
        self.check_object_permissions(request, team)

        return Response(
            {"message": "Success", "data": TeamSerializer(team).data},
            status=status.HTTP_200_OK,
        )
        
    def update(self, request):
        team = get_team(request.data.get("team_id"))
        self.check_object_permissions(request, team)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            team,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Team updated successfully", "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        team = get_team(request.data.get("team_id"))
        self.check_object_permissions(request, team)

        delete_team(
            team=team,
            performed_by=request.user,
        )

        return Response(
            {"message": "Team deleted successfully"},
            status=status.HTTP_200_OK,
        )
        
    # --------------------------------------------------
    # Custom Actions
    # --------------------------------------------------
    @action(detail=True, methods=["get"])
    def members(self, request):
        team_id = request.query_params.get("team_id")
        team = get_team(team_id)

        self.check_object_permissions(request, team)

        members = get_all_team_memberships(team_id)

        return Response(
            {"message": "Success", "data": TeamMembershipSerializer(members, many=True).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"])
    def self_remove_member(self, request):
        team = get_team(request.data.get("team_id"))
        self.check_object_permissions(request, team)

        self_remove_team_member(
            team=team,
            user=request.user,
        )

        return Response(
            {"message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )
    @action(detail=True, methods=["post"])
    def send_invite(self, request):
        team = get_team(request.data.get("team_id"))
        self.check_object_permissions(request, team)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = get_user(serializer.validated_data["email"], kind="email")
        if not user:
            raise NotFound("User not found")

        invite_token = send_team_invite(
            team=team,
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
        team = get_team(request.data.get("team_id"))
        self.check_object_permissions(request, team)

        user_id = verify_invite_token(
            invite_type="team",
            token=request.data.get("invite_token"),
        )
        if not user_id:
            raise ValidationError("Invalid invite token")

        user = User.objects.get(id=user_id)

        membership = add_team_member(
            team=team,
            user=user,
            role=request.data.get("role", "MEMBER"),
        )

        return Response(
            TeamMembershipSerializer(membership).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def update_member(self, request):
        team = get_team(request.data.get("team_id"))
        self.check_object_permissions(request, team)

        target_user = get_user(request.data.get("email"), kind="email")
        if not target_user:
            raise NotFound("User not found")

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data={"role": request.data.get("role")},
            context={
                "request": request,
                "member_user": target_user,
                "team": team,
            },
        )
        serializer.is_valid(raise_exception=True)

        membership = update_team_member_role(
            team=team,
            user=target_user,
            role=serializer.validated_data["role"],
        )

        return Response(
            {
                "message": "Team member updated successfully",
                "data": TeamMembershipSerializer(membership).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"])
    def remove_member(self, request):
        team = get_team(request.data.get("team_id"))
        self.check_object_permissions(request, team)

        user = get_user(request.data.get("email"), kind="email")
        if not user:
            raise NotFound("User not found")

        remove_team_member(
            team=team,
            user=user,
        )

        return Response(
            {"message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def transfer_manager(self, request):
        team = get_team(request.data.get("team_id"))
        self.check_object_permissions(request, team)

        new_owner = get_user(request.data.get("email"), kind="email")
        if not new_owner:
            raise NotFound("User not found")

        transfer_team_ownership(
            team=team,
            new_owner=new_owner,
            performed_by=request.user,
        )

        return Response(
            {"message": "Team manager updated successfully", "data": TeamSerializer(team).data},
            status=status.HTTP_200_OK,
        )
