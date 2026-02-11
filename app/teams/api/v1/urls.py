from django.urls import path

from .api import TeamAPI

urlpatterns = [
    path("get-user-teams/", TeamAPI.as_view({"get": "list"}), name="get_user_teams"),
    path("create-team/", TeamAPI.as_view({"post": "create"}), name="create_team"),
    path("get-team-details/", TeamAPI.as_view({"get": "retrieve"}), name="get_team_details"),
    path("get-team-members/", TeamAPI.as_view({"get": "members"}), name="get_team_members"),
    path("self-remove-member/", TeamAPI.as_view({"delete": "self_remove_member"}), name="self_remove_member"),
    path("update-team/", TeamAPI.as_view({"put": "update"}), name="update_team"),
    path("sent-invite/", TeamAPI.as_view({"post": "send_invite"}), name="send_invite"),
    path("add-team-member/", TeamAPI.as_view({"post": "add_member"}), name="add_team_member"),
    path("update-member/", TeamAPI.as_view({"patch": "update_member"}), name="update_team_member"),
    path("remove-member/", TeamAPI.as_view({"delete": "remove_member"}), name="remove_member"),
    path("delete-team/", TeamAPI.as_view({"delete": "destroy"}), name="delete_team"),
    path("transfer-manager/", TeamAPI.as_view({"post": "transfer_manager"}), name="transfer_manager"),
]
