from django.urls import path

from .views import ProjectView, ProjectMembershipView, ProjectUpdateView, ProjectOwnerView

urlpatterns = [
    path('get-user-projects/', ProjectView.as_view({'get': 'get_projects'}), name='project-list'),
    path('create-project/', ProjectView.as_view({'post': 'create_project'}), name='project-create'),
    path('get-project-details/', ProjectMembershipView.as_view({'get': 'retrieve'}), name='project-details'),
    path('get-project-members/', ProjectMembershipView.as_view({'get': 'list'}), name='project-members'),
    path('self-remove-member/', ProjectMembershipView.as_view({'delete': 'self_remove_member'}), name='self-remove'),
    path('update-project/', ProjectUpdateView.as_view({'put': 'update_project'}), name='project-update'),
    path('send-invite/', ProjectUpdateView.as_view({'post': 'send_invite'}), name='project-send-invite'),
    path('add-project-member/', ProjectUpdateView.as_view({'post': 'add_member'}), name='project-add-member'),
    path('update-member/', ProjectUpdateView.as_view({'put': 'update_member'}), name='project-update-member'),
    path('remove-member/', ProjectUpdateView.as_view({'delete': 'remove_member'}), name='project-remove-member'),
    path('transfer-owner/', ProjectOwnerView.as_view({'put': 'transfer_ownership'}), name='project-transfer-ownership'),
    path('delete-project/', ProjectOwnerView.as_view({'delete': 'delete_project'}), name='peoject-delete'),
]
