"""
Task endpoints: create (+ subtasks), list/filter, my-tasks, retrieve, update, delete.

Governance defaults used throughout: create/update/delete need MANAGER unless
the project lowers `*_task_min_role` (floor CONTRIBUTOR); the creator and the
assignee of a task may always update it.
"""
from app.projects.services.project_team_service import assign_team
from app.tasks.models import Task
from .helpers import TaskAPITestCase, ids, kurl, results


class TaskCreateTests(TaskAPITestCase):
    def test_owner_creates_a_task(self):
        resp = self.create(self.owner, "Ship it", description="soon")
        self.assertOK(resp, 201)
        data = resp.data["data"]
        self.assertEqual((data["title"], data["status"], data["priority"]), ("Ship it", "TO_DO", "MEDIUM"))
        self.assertEqual(data["created_by_email"], self.owner.email)
        self.assertEqual(data["project_name"], self.project.name)
        task = Task.objects.get(id=data["id"])
        self.assertEqual((task.project, task.created_by), (self.project, self.owner))

    def test_manager_can_create_by_default(self):
        self.assertOK(self.create(self.manager), 201)

    def test_contributor_is_blocked_until_the_project_lowers_the_threshold(self):
        self.assertDenied(self.create(self.contributor))
        self.set_settings(self.project, create_task_min_role="CONTRIBUTOR")
        self.assertOK(self.create(self.contributor), 201)

    def test_lead_follows_the_threshold_too(self):
        self.assertDenied(self.create(self.lead))
        self.set_settings(self.project, create_task_min_role="LEAD")
        self.assertOK(self.create(self.lead), 201)
        self.assertDenied(self.create(self.contributor))

    def test_viewer_can_never_create_even_with_the_lowest_threshold(self):
        self.set_settings(self.project, create_task_min_role="CONTRIBUTOR")
        self.assertDenied(self.create(self.viewer))

    def test_non_member_is_refused(self):
        self.assertDenied(self.create(self.outsider))

    def test_the_project_can_switch_task_creation_off_for_everyone_but_the_owner(self):
        self.set_settings(self.project, allow_task_creation=False)
        self.assertDenied(self.create(self.manager))
        self.assertOK(self.create(self.owner), 201)

    def test_validation(self):
        self.assertOK(self.post(self.owner, "create-task", {"project_id": str(self.project.id)}), 400)       # no title
        self.assertOK(self.post(self.owner, "create-task", {"title": "x"}), 400)                              # no project
        self.assertOK(self.post(self.owner, "create-task",
                                {"title": "x", "project_id": "00000000-0000-0000-0000-000000000000"}), 404)
        self.assertOK(self.post(self.owner, "create-task", {"title": "x", "project_id": "not-a-uuid"}), 404)

    def test_cannot_create_in_a_deleted_project(self):
        self.project.is_deleted = True
        self.project.save()
        self.assertOK(self.create(self.owner), 404)

    def test_requires_authentication(self):
        resp = self.anon().post(kurl("create-task"), {"title": "x", "project_id": str(self.project.id)}, format="json")
        self.assertDenied(resp, 401)

    def test_team_derived_contributor_can_create_when_the_threshold_allows(self):
        team = self.make_team(self.make_user())
        member = self.make_user()
        self.add_team_member(team, member)
        assign_team(project=self.project, team=team, role="CONTRIBUTOR", is_owning=True, assigned_by=self.owner)
        self.assertDenied(self.create(member))
        self.set_settings(self.project, create_task_min_role="CONTRIBUTOR")
        self.assertOK(self.create(member), 201)

    def test_team_with_a_viewer_link_cannot_create(self):
        team = self.make_team(self.make_user())
        member = self.make_user()
        self.add_team_member(team, member)
        assign_team(project=self.project, team=team, role="VIEWER", is_owning=True, assigned_by=self.owner)
        self.set_settings(self.project, create_task_min_role="CONTRIBUTOR")
        self.assertDenied(self.create(member))


class SubtaskTests(TaskAPITestCase):
    def setUp(self):
        super().setUp()
        self.parent = self.make_task(created_by=self.manager, title="Parent", assigned_to=self.contributor)

    def subtask(self, user, parent=None, project=None):
        return self.create(user, "Sub", project=project, parent_id=str((parent or self.parent).id))

    def test_the_project_owner_can_add_a_subtask_to_anyones_task(self):
        """REGRESSION: the old OR-chain of `!=` checks refused everyone who wasn't creator AND assignee AND project owner."""
        resp = self.subtask(self.owner)
        self.assertOK(resp, 201)
        self.assertEqual(str(resp.data["data"]["parent"]), str(self.parent.id))
        self.assertEqual(resp.data["data"]["parent_task"], "Parent")

    def test_the_parents_assignee_can_add_a_subtask_even_below_the_create_threshold(self):
        self.assertOK(self.subtask(self.contributor), 201)

    def test_the_parents_creator_can_add_a_subtask(self):
        self.assertOK(self.subtask(self.manager), 201)

    def test_an_unrelated_contributor_cannot(self):
        other = self.make_user()
        self.add_project_member(self.project, other, "CONTRIBUTOR")
        self.assertDenied(self.subtask(other))

    def test_an_unrelated_contributor_can_once_the_threshold_is_lowered(self):
        other = self.make_user()
        self.add_project_member(self.project, other, "CONTRIBUTOR")
        self.set_settings(self.project, create_task_min_role="CONTRIBUTOR")
        self.assertOK(self.subtask(other), 201)

    def test_a_viewer_assignee_still_cannot_create(self):
        parent = self.make_task(created_by=self.manager, assigned_to=self.viewer)
        self.assertOK(self.subtask(self.viewer, parent=parent), 400)   # read-only roles can never create work items
        self.assertEqual(Task.objects.filter(parent=parent).count(), 0)

    def test_subtasks_cannot_be_nested(self):
        child = self.make_task(created_by=self.manager, parent=self.parent, title="child")
        resp = self.subtask(self.owner, parent=child)
        self.assertOK(resp, 400)
        self.assertIn("nested", str(resp.data))

    def test_parent_must_belong_to_the_same_project(self):
        other_project = self.make_project(self.owner)
        foreign_parent = self.make_task(project=other_project, title="foreign")
        resp = self.subtask(self.owner, parent=foreign_parent)
        self.assertOK(resp, 400)
        self.assertEqual(Task.objects.filter(parent__isnull=False).count(), 0)

    def test_unknown_or_deleted_parent_is_404(self):
        self.assertOK(self.create(self.owner, parent_id="00000000-0000-0000-0000-000000000000"), 404)
        self.parent.is_deleted = True
        self.parent.save()
        self.assertOK(self.subtask(self.owner), 404)

    def test_outsider_is_refused(self):
        self.assertDenied(self.subtask(self.outsider))


class TaskListTests(TaskAPITestCase):
    def setUp(self):
        super().setUp()
        self.t1 = self.make_task(title="Fix login bug", status="TO_DO", priority="HIGH", assigned_to=self.contributor, due_date="2030-01-02")
        self.t2 = self.make_task(title="Write docs", status="DONE", priority="LOW", due_date="2030-01-01")
        self.t3 = self.make_task(title="Refactor", status="IN_PROGRESS", priority="HIGH", parent=self.t1)

    def list(self, user=None, **query):
        return self.get(user or self.owner, "get-project-tasks", project_id=self.project.id, **query)

    def test_lists_live_tasks_of_the_project_only(self):
        gone = self.make_task(title="gone")
        gone.is_deleted = True
        gone.save()
        other = self.make_task(project=self.make_project(self.owner), title="elsewhere")
        resp = self.list()
        self.assertOK(resp)
        self.assertEqual(ids(resp), {str(self.t1.id), str(self.t2.id), str(self.t3.id)})
        self.assertNotIn(str(other.id), ids(resp))

    def test_filters(self):
        self.assertEqual(ids(self.list(status="DONE")), {str(self.t2.id)})
        self.assertEqual(ids(self.list(priority="HIGH")), {str(self.t1.id), str(self.t3.id)})
        self.assertEqual(ids(self.list(assigned_to=self.contributor.id)), {str(self.t1.id)})
        self.assertEqual(ids(self.list(parent=self.t1.id)), {str(self.t3.id)})
        self.assertEqual(ids(self.list(status="IN_PROGRESS", priority="HIGH")), {str(self.t3.id)})

    def test_search(self):
        self.assertEqual(ids(self.list(search="login")), {str(self.t1.id)})
        self.assertEqual(ids(self.list(search="DOCS")), {str(self.t2.id)})

    def test_ordering(self):
        asc = [i["title"] for i in results(self.list(ordering="due_date")) if i["due_date"]]
        self.assertEqual(asc, ["Write docs", "Fix login bug"])
        desc = [i["title"] for i in results(self.list(ordering="-due_date")) if i["due_date"]]
        self.assertEqual(desc, ["Fix login bug", "Write docs"])

    def test_pagination(self):
        resp = self.list(page_size=2)
        self.assertEqual(resp.data["count"], 3)
        self.assertEqual(len(results(resp)), 2)
        self.assertIsNotNone(resp.data["next"])

    def test_every_member_role_can_list_but_outsiders_cannot(self):
        for user in (self.manager, self.lead, self.contributor, self.viewer):
            self.assertOK(self.list(user))
        self.assertDenied(self.list(self.outsider))

    def test_project_id_validation(self):
        self.assertOK(self.get(self.owner, "get-project-tasks"), 400)
        self.assertOK(self.get(self.owner, "get-project-tasks", project_id="00000000-0000-0000-0000-000000000000"), 404)
        self.assertOK(self.get(self.owner, "get-project-tasks", project_id="not-a-uuid"), 404)

    def test_team_derived_participants_can_list(self):
        team = self.make_team(self.make_user())
        member = self.make_user()
        self.add_team_member(team, member)
        assign_team(project=self.project, team=team, role="VIEWER", is_owning=True, assigned_by=self.owner)
        self.assertOK(self.list(member))

    def test_requires_authentication(self):
        self.assertDenied(self.anon().get(kurl("get-project-tasks", project_id=self.project.id)), 401)


class MyTasksTests(TaskAPITestCase):
    def test_lists_only_tasks_assigned_to_me(self):
        mine = self.make_task(title="mine", assigned_to=self.contributor, status="TO_DO")
        done = self.make_task(title="done", assigned_to=self.contributor, status="DONE")
        self.make_task(title="not mine", assigned_to=self.lead)
        self.make_task(title="unassigned")
        resp = self.get(self.contributor, "get-my-tasks")
        self.assertOK(resp)
        self.assertEqual(ids(resp), {str(mine.id), str(done.id)})
        self.assertEqual(ids(self.get(self.contributor, "get-my-tasks", status="DONE")), {str(done.id)})

    def test_spans_projects_and_skips_deleted_ones(self):
        other = self.make_project(self.owner)
        self.add_project_member(other, self.contributor, "CONTRIBUTOR")
        a = self.make_task(assigned_to=self.contributor)
        b = self.make_task(project=other, assigned_to=self.contributor)
        dead_project = self.make_project(self.owner)
        self.add_project_member(dead_project, self.contributor, "CONTRIBUTOR")
        self.make_task(project=dead_project, assigned_to=self.contributor)
        dead_project.is_deleted = True
        dead_project.save()
        self.assertEqual(ids(self.get(self.contributor, "get-my-tasks")), {str(a.id), str(b.id)})

    def test_skips_deleted_tasks(self):
        task = self.make_task(assigned_to=self.contributor)
        task.is_deleted = True
        task.save()
        self.assertEqual(ids(self.get(self.contributor, "get-my-tasks")), set())

    def test_requires_authentication(self):
        self.assertDenied(self.anon().get(kurl("get-my-tasks")), 401)


class TaskRetrieveTests(TaskAPITestCase):
    def setUp(self):
        super().setUp()
        self.task = self.make_task(title="Look at me", assigned_to=self.contributor)

    def test_members_can_read(self):
        for user in (self.owner, self.viewer, self.contributor):
            resp = self.get(user, "get_task_details", task_id=self.task.id)
            self.assertOK(resp)
            self.assertEqual(resp.data["data"]["title"], "Look at me")
            self.assertEqual(resp.data["data"]["assigned_to_email"], self.contributor.email)

    def test_outsider_is_refused(self):
        self.assertDenied(self.get(self.outsider, "get_task_details", task_id=self.task.id))

    def test_unknown_malformed_missing_and_deleted(self):
        self.assertOK(self.get(self.owner, "get_task_details", task_id="00000000-0000-0000-0000-000000000000"), 404)
        self.assertOK(self.get(self.owner, "get_task_details", task_id="not-a-uuid"), 404)
        self.assertOK(self.get(self.owner, "get_task_details"), 400)
        self.task.is_deleted = True
        self.task.save()
        self.assertOK(self.get(self.owner, "get_task_details", task_id=self.task.id), 404)

    def test_requires_authentication(self):
        self.assertDenied(self.anon().get(kurl("get_task_details", task_id=self.task.id)), 401)


class TaskUpdateTests(TaskAPITestCase):
    def setUp(self):
        super().setUp()
        self.task = self.make_task(created_by=self.manager, title="Original", assigned_to=self.contributor)

    def update(self, user, task=None, **data):
        return self.put(user, "update-task", data, task_id=(task or self.task).id)

    def test_owner_updates_every_field(self):
        resp = self.update(self.owner, title="New", description="d", status="IN_PROGRESS", priority="URGENT",
                           task_type="BUG", start_date="2030-01-01", due_date="2030-02-01")
        self.assertOK(resp)
        self.task.refresh_from_db()
        self.assertEqual((self.task.title, self.task.status, self.task.priority, self.task.task_type),
                         ("New", "IN_PROGRESS", "URGENT", "BUG"))
        self.assertEqual(str(self.task.due_date), "2030-02-01")

    def test_manager_can_update_by_default(self):
        self.assertOK(self.update(self.manager, status="DONE"))

    def test_the_assignee_and_the_creator_can_always_update(self):
        self.assertOK(self.update(self.contributor, status="IN_PROGRESS"))      # assignee
        creator_task = self.make_task(created_by=self.contributor, title="mine")
        self.assertOK(self.update(self.contributor, creator_task, status="DONE"))  # creator

    def test_other_contributors_are_blocked_until_the_threshold_is_lowered(self):
        other = self.make_user()
        self.add_project_member(self.project, other, "CONTRIBUTOR")
        self.assertDenied(self.update(other, status="DONE"))
        self.set_settings(self.project, update_task_min_role="CONTRIBUTOR")
        self.assertOK(self.update(other, status="DONE"))

    def test_viewers_and_outsiders_cannot_update(self):
        self.set_settings(self.project, update_task_min_role="CONTRIBUTOR")
        self.assertDenied(self.update(self.viewer, status="DONE"))
        self.assertDenied(self.update(self.outsider, status="DONE"))

    def test_the_project_can_switch_task_updates_off_for_everyone_but_the_owner_creator_and_assignee(self):
        self.set_settings(self.project, allow_task_updates=False)
        other = self.make_user()
        self.add_project_member(self.project, other, "MANAGER")
        self.assertDenied(self.update(other, status="DONE"))
        self.assertOK(self.update(self.owner, status="DONE"))
        self.assertOK(self.update(self.contributor, status="REVIEW"))

    def test_invalid_values_are_rejected(self):
        self.assertOK(self.update(self.owner, status="WHATEVER"), 400)
        self.assertOK(self.update(self.owner, priority="WHATEVER"), 400)
        self.assertOK(self.update(self.owner, task_type="WHATEVER"), 400)
        self.assertOK(self.update(self.owner, due_date="tomorrow"), 400)
        self.assertOK(self.update(self.owner, title=""), 400)

    def test_assignment_rules(self):
        self.assertOK(self.update(self.owner, assigned_to=str(self.lead.id)))                 # contributor+ is fine
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to, self.lead)
        self.assertOK(self.update(self.owner, assigned_to=str(self.viewer.id)), 400)           # read-only role
        self.assertOK(self.update(self.owner, assigned_to=str(self.outsider.id)), 400)         # not on the project
        self.assertOK(self.update(self.owner, assigned_to=None))                               # unassign
        self.task.refresh_from_db()
        self.assertIsNone(self.task.assigned_to)

    def test_a_team_derived_contributor_can_be_assigned(self):
        team = self.make_team(self.make_user())
        member = self.make_user()
        self.add_team_member(team, member)
        assign_team(project=self.project, team=team, role="CONTRIBUTOR", is_owning=True, assigned_by=self.owner)
        self.assertOK(self.update(self.owner, assigned_to=str(member.id)))
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to, member)

    def test_assigning_a_deleted_users_id_or_garbage_is_rejected(self):
        self.assertOK(self.update(self.owner, assigned_to="not-a-uuid"), 400)
        self.assertOK(self.update(self.owner, assigned_to="00000000-0000-0000-0000-000000000000"), 400)

    def test_project_and_parent_cannot_be_changed_through_update(self):
        other = self.make_project(self.owner)
        self.assertOK(self.update(self.owner, project=str(other.id), parent=str(self.task.id)))
        self.task.refresh_from_db()
        self.assertEqual(self.task.project, self.project)
        self.assertIsNone(self.task.parent)

    def test_unknown_and_deleted_tasks_are_404(self):
        self.assertOK(self.put(self.owner, "update-task", {"title": "x"}, task_id="00000000-0000-0000-0000-000000000000"), 404)
        self.task.is_deleted = True
        self.task.save()
        self.assertOK(self.update(self.owner, title="x"), 404)

    def test_requires_authentication(self):
        resp = self.anon().put(kurl("update-task", task_id=self.task.id), {"title": "x"}, format="json")
        self.assertDenied(resp, 401)


class TaskDeleteTests(TaskAPITestCase):
    def setUp(self):
        super().setUp()
        self.task = self.make_task(created_by=self.manager, title="Doomed", assigned_to=self.contributor)

    def remove(self, user, task=None):
        return self.delete(user, "delete-task", task_id=(task or self.task).id)

    def test_manager_and_owner_can_delete_and_it_is_soft(self):
        self.assertOK(self.remove(self.manager))
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_deleted)
        other = self.make_task(title="other")
        self.assertOK(self.remove(self.owner, other))

    def test_a_deleted_task_disappears_everywhere(self):
        self.assertOK(self.remove(self.owner))
        self.assertEqual(ids(self.get(self.owner, "get-project-tasks", project_id=self.project.id)), set())
        self.assertEqual(ids(self.get(self.contributor, "get-my-tasks")), set())
        self.assertOK(self.get(self.owner, "get_task_details", task_id=self.task.id), 404)
        self.assertOK(self.remove(self.owner), 404)

    def test_lead_contributor_viewer_and_outsider_cannot_delete(self):
        for user in (self.lead, self.contributor, self.viewer, self.outsider):
            self.assertDenied(self.remove(user))
        self.task.refresh_from_db()
        self.assertFalse(self.task.is_deleted)

    def test_the_project_can_switch_deletion_off_for_everyone_but_the_owner(self):
        self.set_settings(self.project, allow_task_deletions=False)
        other_task = self.make_task(created_by=self.owner, title="theirs")
        self.assertDenied(self.remove(self.manager, other_task))
        self.assertOK(self.remove(self.owner, other_task))

    def test_only_the_creator_can_delete_a_subtask(self):
        sub = self.make_task(created_by=self.manager, parent=self.task, title="sub")
        self.assertDenied(self.remove(self.owner, sub))     # even the project owner
        self.assertOK(self.remove(self.manager, sub))

    def test_unknown_task_is_404(self):
        self.assertOK(self.delete(self.owner, "delete-task", task_id="00000000-0000-0000-0000-000000000000"), 404)
        self.assertOK(self.delete(self.owner, "delete-task", task_id="not-a-uuid"), 404)
        self.assertOK(self.delete(self.owner, "delete-task"), 400)

    def test_requires_authentication(self):
        self.assertDenied(self.anon().delete(kurl("delete-task", task_id=self.task.id)), 401)
