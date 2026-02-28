from django.urls import path

from .api import TeamAPI

urlpatterns = [
    path("get-user-teams/", TeamAPI.as_view({"get": "list"}), name="get_user_teams"),
    path("create-team/", TeamAPI.as_view({"post": "create"}), name="create_team"),
    path("get-org-teams/", TeamAPI.as_view({"get": "org_teams"}), name="get_org_teams"),
    path("get-team-details/", TeamAPI.as_view({"get": "retrieve"}), name="get_team_details"),
    path("get-team-members/", TeamAPI.as_view({"get": "members"}), name="get_team_members"),
    path("self-remove-member/", TeamAPI.as_view({"delete": "self_remove_member"}), name="self_remove_member"),
    path("update-team/", TeamAPI.as_view({"put": "update"}), name="update_team"),
    path("sent-invite/", TeamAPI.as_view({"post": "send_invite"}), name="team_send_invite"),
    path("accept-team-invite/", TeamAPI.as_view({"post": "accept_invite"}), name="team_accept_invite"),
    path("update-member/", TeamAPI.as_view({"put": "update_member"}), name="update_team_member"),
    path("remove-member/", TeamAPI.as_view({"delete": "remove_member"}), name="remove_member"),
    path("delete-team/", TeamAPI.as_view({"delete": "destroy"}), name="delete_team"),
    path("transfer-owner/", TeamAPI.as_view({"put": "transfer_owner"}), name="transfer_manager"),
]
