from django.urls import path

from .api import OrganizationAPI


urlpatterns = [
    path("get-org/", OrganizationAPI.as_view({'get': 'list'}), name="get_org"),
    path("create-org/", OrganizationAPI.as_view({'post': 'create'}), name="create_org"),
    path("get-org-details/", OrganizationAPI.as_view({"get": "retrieve"}), name="get_org_details"),
    path("get-org-members/", OrganizationAPI.as_view({"get": "list"}), name="get_org_members"),
    path("self-remove-member/", OrganizationAPI.as_view({"delete": "self_remove_member"}), name="self_remove_member"),
    path("update-org/", OrganizationAPI.as_view({"put": "update_org"}), name="update_org"),
    path("sent-invite/", OrganizationAPI.as_view({"post": "send_invite"}), name="send_invite"),
    path("add-org-member/", OrganizationAPI.as_view({"post": "add_member"}), name="add_org_member"),
    path("update-member/", OrganizationAPI.as_view({"put": "update_member"}), name="update_org_member"),
    path("update-owner/", OrganizationAPI.as_view({"put": "transfer_owner"}), name="update_org_owner"),
    path("remove-member/", OrganizationAPI.as_view({"delete": "remove_member"}), name="remove_member"),
    path("delete-org/", OrganizationAPI.as_view({"delete": "delete_org"}), name="delete_org"),
]