from django.urls import path

from api import ProjectAPI

urlpatterns = [
    path('get-user-projects/', ProjectAPI.as_view({'get': 'list'}), name='project-list'),
    path('create-project/', ProjectAPI.as_view({'post': 'create'}), name='project-create'),
    path('get-project-details/', ProjectAPI.as_view({'get': 'retrieve'}), name='project-details'),
    path('get-project-members/', ProjectAPI.as_view({'get': 'members'}), name='project-members'),
    path('self-remove-member/', ProjectAPI.as_view({'post': 'self_remove_member'}), name='self-remove'),
    path('update-project/', ProjectAPI.as_view({'put': 'update'}), name='project-update'),
    path('send-invite/', ProjectAPI.as_view({'post': 'send_invite'}), name='project-send-invite'),
    path('add-project-member/', ProjectAPI.as_view({'post': 'add_member'}), name='project-add-member'),
    path('update-member/', ProjectAPI.as_view({'patch': 'update_member'}), name='project-update-member'),
    path('remove-member/', ProjectAPI.as_view({'delete': 'remove_member'}), name='project-remove-member'),
    path('transfer-owner/', ProjectAPI.as_view({'put': 'transfer_ownership'}), name='project-transfer-ownership'),
    path('delete-project/', ProjectAPI.as_view({'delete': 'destroy'}), name='project-delete'),
]
