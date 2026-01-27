import logging

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.decorators import action

from app.organizations.models import Organization
from app.organizations.api.v1.serializers import (
    OrganizationSerializer, OrganizationCreateSerializer, OrganizationUpdateSerializer,
    OrganizationMembershipSerializer, InviteMemberSerializer, OrganizationMemberUpdateSerializer,
)

from app.accounts.models import User

from core.utils import (
    get_org, get_user, get_all_org_memberships,
)
from core.permissions.organization import (
    IsOrganizationAdmin, IsOrganizationMember, IsOrganizationOwner,
)

from app.organizations.services.organization_invite_service import send_organization_invite
from app.organizations.services.organization_membership_service import (
    add_member, remove_member, self_remove, update_role,
)

from app.organizations.services.organization_service import (
    transfer_ownership, delete_organization,
)

from services.invite_token_service import verify_invite_token

logger = logging.getLogger(__name__)


class OrganizationAPI(viewsets.ModelViewSet):
    """
    Organization API (v1)
    """
    queryset = Organization.objects.all()

    def get_permissions(self):
        if self.action in ["list", "create"]:
            permissions = [IsAuthenticated]

        elif self.action in ["update", "send_invite", "add_member", "update_member"]:
            permissions = [IsAuthenticated, IsOrganizationOwner | IsOrganizationAdmin]

        elif self.action in ["transfer_owner", "remove_member", "destroy"]:
            permissions = [IsAuthenticated, IsOrganizationOwner]

        elif self.action == ["retrieve", "members", "self_remove_member"]:
            permissions = [IsAuthenticated, IsOrganizationMember]

        else:
            permissions = [IsAuthenticated]

        return [permission() for permission in permissions]

    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationCreateSerializer
        if self.action == "update":
            return OrganizationUpdateSerializer
        if self.action == "send_invite":
            return InviteMemberSerializer
        if self.action == "update_member":
            return OrganizationMemberUpdateSerializer

    def list(self, request):
        orgs = Organization.objects.filter(
            memberships__user=request.user
        ).distinct()

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(orgs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        org = serializer.save()
        return Response(
            OrganizationSerializer(org).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        org = self.get_object()
        self.check_object_permissions(request, org)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(org)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        org = self.get_object()
        self.check_object_permissions(request, org)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            org,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        org = self.get_object()
        self.check_object_permissions(request, org)

        delete_organization(
            organization=org,
            performed_by=request.user,
        )

        return Response(
            {"message": "Organization deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )

    # --------------------------------------------------
    # Custom Actions
    # --------------------------------------------------
    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        org = self.get_object()
        self.check_object_permissions(request, org)

        members = get_all_org_memberships(org.id)

        return Response(
            OrganizationMembershipSerializer(members, many=True).data, 
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["delete"])
    def self_remove_member(self, request, pk=None):
        org = self.get_object()
        self.check_object_permissions(request, org)

        self_remove(
            organization=org,
            user=request.user,
        )

        return Response(
            {"message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def send_invite(self, request, pk=None):
        org = self.get_object()
        self.check_object_permissions(request, org)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = get_user(serializer.validated_data["email"], kind="email")
        if not user:
            raise NotFound("User not found")

        invite_token = send_organization_invite(
            organization=org,
            user=user,
            invited_by=request.user,
            role=request.data.get("role", "MEMBER"),
        )

        return Response(
            {"invite_token": invite_token},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def add_member(self, request, pk=None):
        org = self.get_object()
        self.check_object_permissions(request, org)

        user_id = verify_invite_token(
            invite_type="organization",
            token=request.data.get("invite_token"),
        )
        if not user_id:
            raise ValidationError("Invalid invite token")

        user = User.objects.get(id=user_id)

        membership = add_member(
            organization=org,
            user=user,
            role=request.data.get("role", "MEMBER"),
        )

        return Response(
            OrganizationMembershipSerializer(membership).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def update_member(self, request, pk=None):
        org = self.get_object()
        self.check_object_permissions(request, org)

        target_user = get_user(request.data.get("email"), kind="email")
        if not target_user:
            raise NotFound("User not found")

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data={"role": request.data.get("role")},
            context={
                "request": request,
                "member_user": target_user,
                "organization": org,
            },
        )
        serializer.is_valid(raise_exception=True)

        membership = update_role(
            organization=org,
            user=target_user,
            role=serializer.validated_data["role"],
        )

        return Response(
            OrganizationMembershipSerializer(membership).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def transfer_owner(self, request, pk=None):
        org = self.get_object()
        self.check_object_permissions(request, org)

        new_owner = get_user(request.data.get("email"), kind="email")
        if not new_owner:
            raise NotFound("User not found")

        transfer_ownership(
            organization=org,
            new_owner=new_owner,
            performed_by=request.user,
        )

        return Response(
            {"message": "Ownership transferred successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"])
    def remove_member(self, request, pk=None):
        org = self.get_object()
        self.check_object_permissions(request, org)

        user = get_user(request.data.get("email"), kind="email")
        if not user:
            raise NotFound("User not found")

        remove_member(
            organization=org,
            user=user,
        )

        return Response(
            {"message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )
