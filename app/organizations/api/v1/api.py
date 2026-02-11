import logging

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from app.organizations.models import Organization
from app.organizations.filters import OrganizationMembershipFilter
from app.organizations.services.organization_invite_service import send_organization_invite
from app.organizations.api.v1.serializers import (
    OrganizationSerializer, OrganizationCreateSerializer, OrganizationUpdateSerializer,
    OrganizationMembershipSerializer, InviteMemberSerializer, OrganizationMemberUpdateSerializer,
)
from app.organizations.services.organization_membership_service import (
    add_member, remove_member, self_remove, update_role,
)
from app.organizations.services.organization_service import (
    transfer_ownership, delete_organization,
)

from app.accounts.models import User

from core.utils import (
    get_org, get_user, get_all_org_memberships,
)
from core.permissions.organization import (
    IsOrganizationAdmin, IsOrganizationMember, IsOrganizationOwner,
)
from core.pagination import StandardPagination

from services.invite_token_service import verify_invite_token

logger = logging.getLogger(__name__)


class OrganizationAPI(viewsets.ModelViewSet):
    """
    Organization API (v1)
    """
    queryset = Organization.objects.all()
    pagination_class = StandardPagination()
    filterset_class = OrganizationMembershipFilter
    search_fields = ["name"]

    def get_permissions(self):
        if self.action in ["list", "create"]:
            permissions = [IsAuthenticated]

        elif self.action in ["update", "send_invite", "add_member", "update_member"]:
            permissions = [IsAuthenticated, IsOrganizationOwner | IsOrganizationAdmin]

        elif self.action in ["transfer_owner", "remove_member", "destroy"]:
            permissions = [IsAuthenticated, IsOrganizationOwner]

        elif self.action in ["retrieve", "members", "self_remove_member"]:
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
        else:
            return OrganizationSerializer

    def get_ordering_fields(self):
        if self.action == "members":
            return ["joined_at"]
        return ["created_at"]

    def apply_filters(self, request, queryset):
        self.ordering_fields = self.get_ordering_fields()
        
        django_filter = DjangoFilterBackend()
        queryset = django_filter.filter_queryset(request, queryset, self)
        
        search_filter = SearchFilter()
        queryset = search_filter.filter_queryset(request, queryset, self)
        
        ordering_filter = OrderingFilter()
        queryset = ordering_filter.filter_queryset(request, queryset, self)
        
        return queryset
        
    def list(self, request):
        orgs = self.apply_filters(request, Organization.objects.filter(memberships__user=request.user).distinct())
        
        page = self.pagination_class.paginate_queryset(orgs, request)
        
        return self.pagination_class.get_paginated_response({
            "message": "Success",
            "data": OrganizationSerializer(page, many=True).data}
        )

    def create(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        org = serializer.save()
        return Response({
            "message": "Organization created successfully",
            "data": OrganizationSerializer(org).data},
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request):
        org = get_org(request.query_params.get("org_id"))
        self.check_object_permissions(request, org)
        
        return Response({
            "message": "Success",
            "data": OrganizationSerializer(org).data}, 
            status=status.HTTP_200_OK
        )

    def update(self, request):
        org = get_org(request.query_params.get("org_id"))
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

        return Response({
            "message": "Organization updated successfully", 
            "data": OrganizationSerializer(org).data}, 
            status=status.HTTP_200_OK
        )

    def destroy(self, request):
        org = get_org(request.query_params.get("org_id"))
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
    def members(self, request):
        org = get_org(request.query_params.get("org_id"))
        self.check_object_permissions(request, org)

        members = get_all_org_memberships(org.id)

        page = self.pagination_class.paginate_queryset(members, request)
        
        return self.pagination_class.get_paginated_response({
            "message": "Success",
            "data": OrganizationMembershipSerializer(page, many=True).data}
        )

    @action(detail=True, methods=["delete"])
    def self_remove_member(self, request):
        org = get_org(request.query_params.get("org_id"))
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
    def send_invite(self, request):
        org = get_org(request.query_params.get("org_id"))
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

        return Response({
            "message": "Invite sent successfully",
            "invite_token": invite_token},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def add_member(self, request):
        org = get_org(request.query_params.get("org_id"))
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

        return Response({
            "message": "Member added successfully",
            "data": OrganizationMembershipSerializer(membership).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def update_member(self, request):
        org = get_org(request.query_params.get("org_id"))
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

        return Response({
            "message": "Member updated successfully",
            "data": OrganizationMembershipSerializer(membership).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def transfer_owner(self, request):
        org = get_org(request.query_params.get("org_id"))
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
    def remove_member(self, request):
        org = get_org(request.query_params.get("org_id"))
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
