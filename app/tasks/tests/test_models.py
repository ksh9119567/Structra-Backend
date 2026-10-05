from app.tasks.models import Task
from .helpers import TaskAPITestCase


class TaskModelTests(TaskAPITestCase):
    def test_defaults(self):
        task = self.make_task(title="Write docs")
        self.assertEqual((task.status, task.priority, task.task_type), ("TO_DO", "MEDIUM", "FEATURE"))
        self.assertFalse(task.is_deleted)
        self.assertIsNone(task.assigned_to)
        self.assertIsNone(task.parent)
        self.assertEqual(task.description, "")

    def test_str(self):
        task = self.make_task(title="Write docs")
        self.assertEqual(str(task), f"Write docs - {self.project.name}")

    def test_deleting_a_parent_cascades_to_subtasks(self):
        parent = self.make_task()
        self.make_task(parent=parent, title="child")
        parent.delete()
        self.assertEqual(Task.objects.count(), 0)

    def test_assignee_is_cleared_when_the_user_row_goes_away(self):
        task = self.make_task(assigned_to=self.contributor)
        self.contributor.delete()
        task.refresh_from_db()
        self.assertIsNone(task.assigned_to)

    def test_deleting_the_project_deletes_its_tasks(self):
        self.make_task()
        self.project.delete()
        self.assertEqual(Task.objects.count(), 0)
