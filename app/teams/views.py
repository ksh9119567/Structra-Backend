import logging

from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from .models import Team, TeamMembership
from .serializers import (
    TeamSerializer, TeamCreateSerializer, TeamMembershipSerializer, TeamUpdateSerializer,
    TeamMemberUpdateSerializer, InviteMemberSerializer
)
from app.accounts.models import User
from app.organizations.models import Organization, OrganizationMembership
from core.utils import get_user
from core.permissions.team import IsTeamMember, IsTeamManager
from core.permissions.combined import IsOrgOwnerOrTeamManager
from core.utils import get_user, get_org, get_team, get_all_team_memberships, get_team_membership
from services.invite_token_service import *
from services.notification_services import *


logger = logging.getLogger(__name__)


# -------------------------------
# 1. LIST + CREATE TEAMS
# -------------------------------
class TeamView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, ]
    
    def get_user_teams(self, request):
        try:
            teams = Team.objects.filter(memberships__user=request.user)
            serializer = TeamSerializer(teams, many=True)
            logger.info(serializer.data)
            return Response({"message": "Success", "data": serializer.data}, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def create_team(self, request):
        try:
            serializer = TeamCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            team = serializer.save()
            logger.info(team)
            return Response({"message": "Team created successfully", "data": TeamSerializer(team).data}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# ---------------------------------------------
# 2. RETRIEVE TEAM + LIST MEMBERS + SELF REMOVE
# ---------------------------------------------
class TeamMembershipView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsTeamMember]
    
    def retrieve(self, request):
        try:
            team_id = request.query_params.get("team_id")
            team = get_team(team_id)
            
            self.check_object_permissions(request, team)
            
            serializer = TeamSerializer(team)
            return Response({"message": "Success", "data": serializer.data}, status=status.HTTP_200_OK)
        
        except NotFound as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        except ValidationError as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def list(self, request):
        try:
            team_id = request.query_params.get("team_id")
            members = get_all_team_memberships(team_id)
            
            team = get_team(team_id)
            
            self.check_object_permissions(request, team)
            
            serializer = TeamMembershipSerializer(members, many=True)
            return Response({"message": "Success", "data": serializer.data}, status=status.HTTP_200_OK)
        
        except NotFound as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        except ValidationError as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def self_remove_member(self, request):
        try:
            team_id = request.data.get("team_id")
            
            team = get_team(team_id)
            
            self.check_object_permissions(request, team)
            
            if team.is_self_remove_allowed:
                if request.user == team.created_by:
                    raise PermissionDenied("You cannot remove the creator of the team")
                
                membership = get_team_membership(team_id, request.user)
                membership.delete()
            else:
                raise PermissionDenied("You are not allowed to remove yourself from the team")
                
            return Response({"message": "Member removed successfully"}, status=status.HTTP_200_OK)
            
        except PermissionDenied as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)
            
        except NotFound as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        except ValidationError as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# ---------------------------------------------------------------------------------------
# 3. UPDATE TEAM + SEND INVITE + ADD MEMBER + UPDATE MEMBER + REMOVE MEMBER + DELETE TEAM
# ---------------------------------------------------------------------------------------
class TeamUpdateView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsOrgOwnerOrTeamManager]
        
    def update_team(self, request):
        try:
            team_id = request.data.get("team_id")
            team = get_team(team_id)
            
            self.check_object_permissions(request, team)
            
            serializer = TeamUpdateSerializer(team, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Team updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        
        except NotFound as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        except ValidationError as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def send_invite(self, request):
        try:
            team_id = request.data.get("team_id")
            role = request.data.get("role", "MEMBER")
            
            team = get_team(team_id)

            self.check_object_permissions(request, team)

            serializer = InviteMemberSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data["email"]
            user = get_user(email, kind="email")

            if user is None:
                raise NotFound("User not found")

            if TeamMembership.objects.filter(team=team, user=user).exists():
                raise ValidationError("User already a member")

            invite_token = store_invite_token(user.id, invite_type="team")
            send_invite_email(email, invite_type="Team", name=team.name, sender=request.user.email)
            
            return Response({"message": "If that account exists, an invite has been sent", "invite_token": invite_token}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def add_member(self, request):
        try:
            invite_token = request.data.get("invite_token")
            team_id = request.data.get("team_id")
            role = request.data.get("role", "MEMBER")
            
            team = get_team(team_id)
            
            self.check_object_permissions(request, team)
            
            user_id = verify_invite_token(invite_type="organization", token=invite_token)
            if user_id is None:
                raise ValidationError("Invalid invite token")
            
            user = User.objects.get(id=user_id)

            if user is None:
                raise NotFound("User not found")
            
            if TeamMembership.objects.filter(team=team, user=user).exists():
                raise ValidationError("User already a member")
            
            TeamMembership.objects.create(team=team, role=role, user=user)
            
            return Response({"message": "Member added successfully", "email": user.email, "role": role}, status=status.HTTP_200_OK)
        
        except NotFound as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        except ValidationError as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def update_member(self, request):
        try:
            team_id = request.data.get("team_id")
            target_email = request.data.get("email")
            new_role = request.data.get("role")
            
            team = get_team(team_id)
            
            self.check_object_permissions(request, team)
            
            target_user = get_user(target_email, kind="email")
            if not target_user:
                raise NotFound("User not found")
            
            membership = get_team_membership(team_id, target_user)
            
            serializer = TeamMemberUpdateSerializer(data={"role": new_role}, context={"request": request, "member_user": target_user, "team": team})
            serializer.is_valid(raise_exception=True)
            
            membership.role = new_role
            membership.save()
            
            return Response({"message": "Team member updated successfully", "data": TeamMembershipSerializer(membership).data}, status=status.HTTP_200_OK)
        
        except NotFound as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        except ValidationError as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def remove_member(self, request):
        try:
            team_id = request.data.get("team_id")
            user_email = request.data.get("email")
            
            team = get_team(team_id)
            
            self.check_object_permissions(request, team)
            
            user = get_user(user_email, kind="email")
            if user is None:
                raise NotFound("User not found")
            
            if user == team.created_by:
                raise PermissionDenied("You cannot remove the creator of the team") 
            
            membership = get_team_membership(team_id, user)
            
            membership.delete()
            
            return Response({"message": "Member removed successfully"}, status=status.HTTP_200_OK)
        
        except PermissionDenied as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)
            
        except NotFound as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        except ValidationError as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def delete_team(self, request):
        try:
            team_id = request.data.get("team_id")
            team = get_team(team_id)
            
            self.check_object_permissions(request, team)
            
            if team.created_by != request.user:
                return PermissionDenied("You are not the creator of the team")
            
            team.delete()
            return Response({"message": "Team deleted successfully"}, status=status.HTTP_200_OK)
        
        except PermissionDenied as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)
            
        except NotFound as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        except ValidationError as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# ----------------------
# 4. TRANSFER OWNERSHIP
# ----------------------
class TeamManagerView(APIView):
    permission_classes = [IsAuthenticated, IsTeamManager]
    
    def put(self, request):
        try:
            team_id = request.data.get("team_id")
            new_owner_email = request.data.get("email")
            
            team = get_team(team_id)
            
            self.check_object_permissions(request, team)
            
            if team.created_by != request.user:
                raise PermissionDenied("You are not the team creator")
            
            new_owner = get_user(new_owner_email, kind="email")
            
            if new_owner is None:
                raise NotFound("User not found")
            
            if new_owner == team.created_by:
                raise ValidationError("User is already the team creator")
            
            if not OrganizationMembership.objects.filter(organization=team.organization, user=new_owner).exists():
                raise ValidationError("User is not a member of the organization")
            
            if not TeamMembership.objects.filter(team=team, user=new_owner).exists():
                raise ValidationError("User is not a member of the team")
            
            new_owner_membership = get_team_membership(team_id, new_owner)
            
            new_owner_membership.role = "MANAGER"
            new_owner_membership.save()

            team.created_by = new_owner
            team.save()
            
            return Response({"message": "Team manager updated successfully", "data": TeamSerializer(team).data}, status=status.HTTP_200_OK)
        
        except PermissionDenied as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)
        
        except NotFound as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        except ValidationError as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)