import logging

from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from .models import Organization, OrganizationMembership
from .serializers import ( 
    OrganizationSerializer,OrganizationCreateSerializer, OrganizationUpdateSerializer,
    OrganizationMembershipSerializer, InviteMemberSerializer, OrganizationMemberUpdateSerializer
)
from app.accounts.models import User
from core.utils import get_user, get_org, get_org_membership, get_all_org_memberships
from core.permissions.organization import IsOrganizationAdmin, IsOrganizationMember, IsOrganizationOwner
from services.invite_token_service import *
from services.notification_services import *


logger = logging.getLogger(__name__)


# -------------------------------
# 1. LIST + CREATE ORGANIZATIONS
# -------------------------------
class OrganizationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:    
            orgs = Organization.objects.filter(memberships__user=request.user).distinct()

            serializer = OrganizationSerializer(orgs, many=True)
            
            return Response({"message": "Success", "data": serializer.data}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            serializer = OrganizationCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)

            org = serializer.save()
            response = OrganizationSerializer(org).data
            
            return Response({"message": "Organization created successfully", "data": response}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------
# 2. RETRIEVE ORG + LIST MEMBERS + SELF REMOVE
# ---------------------------------------------
class OrganizationMembershipView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def retrieve(self, request):
        try:
            org_id = request.query_params.get("org_id")
            org = get_org(org_id)
            
            self.check_object_permissions(request, org)
            
            serializer = OrganizationSerializer(org)
            
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
            org_id = request.query_params.get("org_id")
            members = get_all_org_memberships(org_id)
            
            org = get_org(org_id)
            
            self.check_object_permissions(request, org)

            serializer = OrganizationMembershipSerializer(members, many=True)
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
            org_id = request.data.get("org_id")
            
            org = get_org(org_id)
            
            self.check_object_permissions(request, org)
            
            if org.is_self_remove_allowed:
                if request.user == org.owner:
                    raise PermissionDenied("You cannot remove the owner")
                
                membership = get_org_membership(org_id, request.user)
                membership.delete()
            else:
                raise PermissionDenied("You are not allowed to remove yourself from the organization")
                
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
    
    
# ---------------------------------------------------------
# 3. UPDATE ORG + SEND INVITE + ADD MEMBER + UPDATE MEMBER 
# ---------------------------------------------------------
class OrganizationUpdateView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationOwner | IsOrganizationAdmin]

    def update_org(self, request):
        try:
            org_id = request.query_params.get("org_id")
            org = get_org(org_id)

            self.check_object_permissions(request, org)

            serializer = OrganizationUpdateSerializer(org, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response({"message": "Organization updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        
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
            org_id = request.data.get("org_id")
            role = request.data.get("role", "MEMBER")
            
            org = get_org(org_id)

            self.check_object_permissions(request, org)

            serializer = InviteMemberSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data["email"]
            user = get_user(email, kind="email")

            if user is None:
                raise NotFound("User not found")

            if OrganizationMembership.objects.filter(organization=org, user=user).exists():
                raise ValidationError("User already a member")

            invite_token = store_invite_token(user.id, invite_type="organization")
            send_invite_email(email, invite_type="Organization", name=org.name, sender=request.user.email)
            
            return Response({"message": "If that account exists, an invite has been sent", "invite_token": invite_token}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def add_member(self, request):
        try:
            invite_token = request.data.get("invite_token")
            org_id = request.data.get("org_id")
            role = request.data.get("role", "MEMBER")
            
            org = get_org(org_id)

            self.check_object_permissions(request, org)

            user_id = verify_invite_token(invite_type="organization", token=invite_token)
            if user_id is None:
                raise ValidationError("Invalid invite token")

            user = User.objects.get(id=user_id)

            if user is None:
                raise NotFound("User not found")

            if OrganizationMembership.objects.filter(organization=org, user=user).exists():
                raise ValidationError("User already a member")
            
            OrganizationMembership.objects.create(organization=org, user=user, role=role)

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
            org_id = request.data.get("org_id")
            target_email = request.data.get("email")
            new_role = request.data.get("role")

            org = get_org(org_id)

            self.check_object_permissions(request, org)

            target_user = get_user(target_email, kind="email")
            if not target_user:
                raise NotFound("User not found")

            membership = get_org_membership(org_id, target_user)

            serializer = OrganizationMemberUpdateSerializer(data={"role": new_role}, context={"request": request, "member_user": target_user, "organization": org})
            serializer.is_valid(raise_exception=True)

            membership.role = new_role
            membership.save()

            return Response({"message": "Member role updated", "data": OrganizationMembershipSerializer(membership).data}, status=status.HTTP_200_OK)
        
        except NotFound as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        except ValidationError as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------
# 4. TRANSFER OWNERSHIP + REMOVE MEMBER + DELETE ORG
# ---------------------------------------------------
class OrganizationDeleteView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationOwner]

    def transfer_owner(self, request):
        try:
            org_id = request.data.get("org_id")
            new_owner_email = request.data.get("email")

            org = get_org(org_id)

            self.check_object_permissions(request, org)
            
            if org.owner != request.user:
                raise PermissionDenied("You are not the owner")
            
            new_owner = get_user(new_owner_email, kind="email")
            
            if new_owner is None:
                raise NotFound("User not found")

            if new_owner == org.owner:
                raise ValidationError("User is already the owner")
            
            if not OrganizationMembership.objects.filter(organization=org, user=new_owner).exists():
                raise ValidationError("User is not a member of the organization")
            
            new_owner_membership = get_org_membership(org_id, new_owner)

            new_owner_membership.role = "OWNER"
            new_owner_membership.save()

            org.owner = new_owner
            org.save()

            return Response({"message": "Owner updated successfully", "data": OrganizationSerializer(org).data}, status=status.HTTP_200_OK)
        
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
        
    def remove_member(self, request):
        try:
            org_id = request.data.get("org_id")
            user_email = request.data.get("email")

            org = get_org(org_id)

            self.check_object_permissions(request, org)

            user = get_user(user_email, kind="email")
            if user is None:
                raise NotFound("User not found")

            if user == org.owner:
                raise PermissionDenied("You cannot remove the owner")
            
            membership = get_org_membership(org_id, user)

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
        
    def delete_org(self, request):
        try:
            org_id = request.data.get("org_id")
            org = get_org(org_id)

            self.check_object_permissions(request, org)

            if org.owner != request.user:
                raise PermissionDenied("You are not the owner")
            
            org.delete()

            return Response({"message": "Organization deleted successfully"}, status=status.HTTP_200_OK)

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