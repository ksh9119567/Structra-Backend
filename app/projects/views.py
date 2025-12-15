import logging

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from .models import Project, ProjectMembership
from .serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectMembershipSerializer, 
    ProjectUpdateSerializer, ProjectMemberUpdateSerializer, InviteMemberSerializer
)
from app.accounts.models import User
from app.organizations.models import OrganizationMembership
from core.utils import get_user, get_project, get_all_project_memberships, get_project_membership
from core.permissions.project import *
from core.permissions.combined import *
from services.invite_token_service import *
from services.notification_services import *


logger = logging.getLogger(__name__)


# -------------------------------
# 1. LIST + CREATE PROJECTS
# -------------------------------
class ProjectView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_projects(self, request):
        try:
            prj = Project.objects.filter(members = request.user).distinct()
            
            serializer = ProjectSerializer(prj, many=True)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error fetching projects for user {request.user.id}: {str(e)}")
            return Response({"detail": "Error fetching projects."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
    def create_project(serf, request):
        try:
            serializer = ProjectCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception = True)
            
            prj = serializer.save()
            
            response = ProjectSerializer(prj).data
            return Response(response, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Error creating project for user {request.user.id}: {str(e)}")
            return Response({"detail": "Error creating project."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            
# ---------------------------------------------
# 2. RETRIEVE RROJECT + LIST MEMBERS + SELF REMOVE
# ---------------------------------------------
class ProjectMembershipView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsProjectMember]
    
    def retrieve(self, request):
        try:
            project_id = request.query_params.get("project_id", None)
            project = get_project(project_id)
            
            self.check_object_permissions(request, project)
            
            serializer = ProjectSerializer(project)
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
            project_id = request.query_params.get("project_id", None)
            members = get_all_project_memberships(project_id)
            
            project = get_project(project_id)
            
            self.check_object_permissions(request, project)
            
            serializer = ProjectMembershipSerializer(members, many=True)
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
            project_id = request.data.get("project_id")
            project = get_project(project_id)
            self.check_object_permissions(request, project)
            if project.is_self_remove_allowed:
                if request.user == project.created_by:
                    raise PermissionDenied("Project creator cannot remove themselves.")
                membership = get_project_membership(project_id, request.user)
                membership.delete()
            else:
                raise PermissionDenied("Self removal is not allowed for this project.")
            
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
        

class ProjectUpdateView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsOrgOwnerOrProjectManager]
    
    def update_project(self, request):
        try:
            project_id = request.data.get("project_id")
            project = get_project(project_id)
            
            self.check_object_permissions(request, project)
            serializer = ProjectUpdateSerializer(project, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Project updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        
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
            project_id = request.data.get("project_id")
            role = request.data.get("role", "MEMBER")
            
            project = get_project(project_id)

            self.check_object_permissions(request, project)

            serializer = InviteMemberSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data["email"]
            user = get_user(email, kind="email")

            if user is None:
                raise NotFound("User not found")

            if ProjectMembership.objects.filter(project=project, user=user).exists():
                raise ValidationError("User already a member")

            invite_token = store_invite_token(user.id, invite_type="project")
            send_invite_email(email, invite_type="Project", name=project.name, sender=request.user.email)
            
            return Response({"message": "If that account exists, an invite has been sent", "invite_token": invite_token}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def add_member(self, request):
        try:
            invite_token = request.data.get("invite_token")
            project_id = request.data.get("project_id")
            role = request.data.get("role", "MEMBER")
            
            project = get_project(project_id)
            
            self.check_object_permissions(request, project)
            
            user_id = verify_invite_token(invite_type="project", token=invite_token)
            if user_id is None:
                raise ValidationError("Invalid invite token")
            
            user = User.objects.get(id=user_id)

            if user is None:
                raise NotFound("User not found")
            
            if ProjectMembership.objects.filter(project=project, user=user).exists():
                raise ValidationError("User already a member")
            
            ProjectMembership.objects.create(project=project, role=role, user=user)
            
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
        import ipdb; ipdb.set_trace()
        try:
            project_id = request.data.get("project_id")
            target_email = request.data.get("email")
            new_role = request.data.get("role")
            
            project = get_project(project_id)
            
            self.check_object_permissions(request, project)
            
            target_user = get_user(target_email, kind="email")
            if not target_user:
                raise NotFound("User not found")
            
            membership = get_project_membership(project_id, target_user)
            
            serializer = ProjectMemberUpdateSerializer(data={"role": new_role}, context={"request": request, "member_user": target_user, "project": project})
            serializer.is_valid(raise_exception=True)
            
            membership.role = new_role
            membership.save()
            
            return Response({"message": "Project member updated successfully", "data": ProjectMembershipSerializer(membership).data}, status=status.HTTP_200_OK)
        
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
            project_id = request.data.get("project_id")
            user_email = request.data.get("email")
            
            project = get_project(project_id)
            
            self.check_object_permissions(request, project)
            
            user = get_user(user_email, kind="email")
            if user is None:
                raise NotFound("User not found")
            
            if user == project.created_by:
                raise PermissionDenied("You cannot remove the creator of the project") 
            
            membership = get_project_membership(project_id, user)
            
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
        
        
class ProjectOwnerView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsOrgOwnerOrProjectOwner]
    
    def transfer_ownership(self, request):
        try:
            project_id = request.data.get("project_id")
            new_owner_email = request.data.get("email")
            
            project = get_project(project_id)
            
            self.check_object_permissions(request, project)
            
            if project.created_by != request.user:
                raise PermissionDenied("You are not the project creator")
            
            new_owner = get_user(new_owner_email, kind="email")
            
            if new_owner is None:
                raise NotFound("User not found")
            
            if new_owner ==project.created_by:
                raise ValidationError("User is already the project creator")
            
            if not OrganizationMembership.objects.filter(organization=project.organization, user=new_owner).exists():
                raise ValidationError("User is not a member of the organization")
            
            if not ProjectMembership.objects.filter(project=project, user=new_owner).exists():
                raise ValidationError("User is not a member of the project")
            
            new_owner_membership = get_project_membership(project_id, new_owner)
            
            new_owner_membership.role = "MANAGER"
            new_owner_membership.save()

            project.created_by = new_owner
            project.save()
            
            return Response({"message": "Project manager updated successfully", "data": ProjectSerializer(project).data}, status=status.HTTP_200_OK)
        
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
        
    def delete_project(self, request):
        try:
            project_id = request.data.get("project_id")
            project = get_project(project_id) 
                       
            self.check_object_permissions(request, project)
            
            if project.created_by != request.user:
                return PermissionDenied("You are not the creator of the project")
            
            project.delete()
            return Response({"message": "Project deleted successfully"}, status=status.HTTP_200_OK)
        
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