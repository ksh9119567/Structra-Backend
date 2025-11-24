from django.urls import path

from .views import TeamView, TeamMembershipView, TeamUpdateView, TeamManagerView


urlpatterns = [
    path("get-user-teams/", TeamView.as_view({"get": "get_user_teams"}), name="get_user_teams"),
    path("create-team/", TeamView.as_view({"post": "create_team"}), name="create_team"),
    path("get-team-details/", TeamMembershipView.as_view({"get": "retrieve"}), name="get_team_details"),
    path("get-team-members/", TeamMembershipView.as_view({"get": "list"}), name="get_team_members"),
    path("self-remove-member/", TeamMembershipView.as_view({"delete": "self_remove_member"}), name="self_remove_member"),
    path("update-team/", TeamUpdateView.as_view({"put": "update_team"}), name="update_team"),
    path("sent-invite/", TeamUpdateView.as_view({"post": "send_invite"}), name="send_invite"),
    path("add-team-member/", TeamUpdateView.as_view({"post": "add_member"}), name="add_team_member"),
    path("update-member/", TeamUpdateView.as_view({"put": "update_member"}), name="update_team_member"),
    path("remove-member/", TeamUpdateView.as_view({"delete": "remove_member"}), name="remove_member"),
    path("delete-team/", TeamUpdateView.as_view({"delete": "delete_team"}), name="delete_team"),
    path("transfer-manager/", TeamManagerView.as_view(), name="transfer_manager"),
]
