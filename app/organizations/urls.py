from django.urls import path

from .views import OrganizationView, OrganizationMembershipView, OrganizationUpdateView, OrganizationDeleteView


urlpatterns = [
    path("get-org/", OrganizationView.as_view(), name="get_org"),
    path("create-org/", OrganizationView.as_view(), name="create_org"),
    path("get-org-details/", OrganizationMembershipView.as_view({"get": "retrieve"}), name="get_org_details"),
    path("get-org-members/", OrganizationMembershipView.as_view({"get": "list"}), name="get_org_members"),
    path("self-remove-member/", OrganizationMembershipView.as_view({"delete": "self_remove_member"}), name="self_remove_member"),
    path("update-org/", OrganizationUpdateView.as_view({"put": "update_org"}), name="update_org"),
    path("sent-invite/", OrganizationUpdateView.as_view({"post": "send_invite"}), name="send_invite"),
    path("add-org-member/", OrganizationUpdateView.as_view({"post": "add_member"}), name="add_org_member"),
    path("update-member/", OrganizationUpdateView.as_view({"put": "update_member"}), name="update_org_member"),
    path("update-owner/", OrganizationUpdateView.as_view({"put": "transfer_owner"}), name="update_org_owner"),
    path("remove-member/", OrganizationDeleteView.as_view({"delete": "remove_member"}), name="remove_member"),
    path("delete-org/", OrganizationDeleteView.as_view({"delete": "delete_org"}), name="delete_org"),
]