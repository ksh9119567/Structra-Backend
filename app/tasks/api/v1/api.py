import logging

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from tasks.models import Task
from app.tasks.api.v1.serializers import *

from core.permissions.project import *
from core.permissions.combined import *
from services.notification_services import *

logger = logging.getLogger(__name__)


class TaskAPI(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsProjectMember]
    
    pass

