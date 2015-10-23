#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_task
----------------------------------

Tests for `Task` class.
"""

import unittest
import json
import vcr as vcr_module
import time
import datetime

from .base import TestCase
from .test_helper import vcr, scrub_string

from anydo_api.task import Task
from anydo_api.errors import *


class TestTask(TestCase):

    def __get_task(self, refresh=False):
        user = self.get_me()
        if refresh:
            with vcr.use_cassette('fixtures/vcr_cassettes/tasks_refreshed.json'):
                task = user.tasks(refresh=True)[0]
        else:
            with vcr.use_cassette('fixtures/vcr_cassettes/tasks.json'):
                task = user.tasks()[0]

        return task

    def test_user_has_access_to_its_tasks(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/tasks.json'):
            self.assertIsInstance(user.tasks(), list)

    def test_user_tasks_are_cached_and_not_require_additional_request(self):
        with vcr.use_cassette('fixtures/vcr_cassettes/tasks.json', record_mode='once'):
            user = self.get_me()
            user.tasks()
            user.tasks()

    def test_user_tasks_could_be_refreshed_from_the_server(self):
        with self.assertRaises(vcr_module.errors.CannotOverwriteExistingCassetteException):
            with vcr.use_cassette('fixtures/vcr_cassettes/tasks.json', record_mode='once'):
                user = self.get_me()
                user.tasks(refresh=True)
                user.tasks(refresh=True)

    def test_user_tasks_are_wrapped_as_objects(self):
        task = self.__get_task()
        self.assertIsInstance(task, Task)

    def test_task_has_appropriate_attributes(self):
        task = self.__get_task()

        self.assertEqual(self.get_me()['email'], task.assignedTo)
        self.assertEqual('New First', task.title)

    def test_task_attributes_accessible_directly(self):
        task = self.__get_task()

        self.assertEqual(self.get_me()['email'], task['assignedTo'])
        self.assertEqual('New First', task['title'])

    def test_task_could_be_updated_successfully_by_index(self):
        new_title = 'First'
        task = self.__get_task()

        with vcr.use_cassette('fixtures/vcr_cassettes/task_update_valid.json'):
            task['title'] = new_title
            task.save()
            self.assertEqual(new_title, task['title'])

        task = self.__get_task(refresh=True)
        with vcr.use_cassette('fixtures/vcr_cassettes/task_updated.json'):
            self.assertEqual(new_title, task['title'])

    def test_user_could_be_updated_successfully_by_attribute(self):
        new_title = 'First'
        task = self.__get_task()

        with vcr.use_cassette('fixtures/vcr_cassettes/task_update_valid.json'):
            task.title = new_title
            task.save()
            self.assertEqual(new_title, task.title)

        task = self.__get_task(refresh=True)
        with vcr.use_cassette('fixtures/vcr_cassettes/task_updated.json'):
            self.assertEqual(new_title, task.title)

    def test_can_not_set_unmapped_attributes(self):
        task = self.__get_task()
        with self.assertRaises(AttributeError):
            task['suppa-duppa'] = 1

    def test_unchanged_data_dont_hit_an_api(self):
        task = self.__get_task()
        with vcr.use_cassette('fixtures/vcr_cassettes/fake.json', record_mode='none'):
            title = task.title
            task['title'] = title[:]
            task.save()

    def test_task_creation_returns_task_instance(self):
        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_valid.json'):
            task = Task.create(user=self.get_me(),
                title='Test Task',
                category='Personal',
                priority='Normal',
                status='UNCHECKED'
            )
            self.assertIsInstance(task, Task)

    def test_task_creation_saves_attributers_correctly(self):
        title = 'New Task'
        note = 'Hello world'
        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_valid_with_attributes.json'):
            task = Task.create(user=self.get_me(),
                title=title,
                category='Personal',
                priority='Normal',
                status='UNCHECKED',
                repeatingMethod='TASK_REPEAT_OFF',
                note=note,
            )

        self.assertEqual(title, task.title)
        self.assertEqual(note, task['note'])

    def test_task_creation_checks_required_fields(self):
        with vcr.use_cassette('fixtures/vcr_cassettes/fake.json', record_mode='none'):
            with self.assertRaises(AttributeError):
                Task.create(user=self.get_me(), status='UNCHECKED')

    def test_task_creation_reraises_occured_errors(self):
        # Emulate Server Error bypassing internal validaitons for missed fields
        original = Task.required_attributes
        def fake(): return set()
        Task.required_attributes = staticmethod(fake)

        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_invalid.json'):
            with self.assertRaises(InternalServerError):
                Task.create(user=self.get_me(),
                    status='UNCHECKED',
                )
        Task.required_attributes = staticmethod(original)

    def test_new_task_could_be_deleted_permanently_after_creation(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_for_delete.json'):
            task = Task.create(user=user, title='Delete me', status='UNCHECKED')

        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_after_new_one_created.json'):
            tasks = user.tasks(refresh=True)
            self.assertTrue(task['id'] in map(lambda task: task['id'], tasks))

        with vcr.use_cassette('fixtures/vcr_cassettes/task_destroy_valid.json'):
            task.destroy()

        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_after_new_one_deleted.json'):
            tasks = user.tasks(refresh=True)
            self.assertFalse(task['id'] in map(lambda task: task['id'], tasks))

    def test_new_task_could_be_deleted_permanently_after_creation(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_for_delete2.json'):
            Task.create(user=user, title='Delete me2', status='UNCHECKED')

        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_after_new_one_created2.json'):
            task = user.tasks(refresh=True)[-1]
            self.assertEqual('Delete me2', task.title)

        with vcr.use_cassette('fixtures/vcr_cassettes/task_destroy_valid2.json'):
            task.destroy()

        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_after_new_one_deleted2.json'):
            tasks = user.tasks(refresh=True)
            self.assertFalse(task['id'] in map(lambda task: task['id'], tasks))

    def test_task_could_be_marked_as_checked(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_before_check.json'):
            task = user.tasks()[0]
            self.assertEqual('UNCHECKED', task['status'])

        with vcr.use_cassette('fixtures/vcr_cassettes/task_mark_checked.json'):
            task.check()

        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_after_check.json'):
            task = next((t for t in user.tasks(refresh=True) if t['id'] == task['id']), None)
            self.assertEqual('CHECKED', task['status'])

    def test_task_could_be_marked_as_done(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_before_mark.json'):
            task = user.tasks()[0]
            self.assertEqual('UNCHECKED', task['status'])

        with vcr.use_cassette('fixtures/vcr_cassettes/task_mark_done.json'):
            task.done()

        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_after_done.json'):
            task = next((t for t in user.tasks(refresh=True, include_done=True) if t['id'] == task['id']), None)
            self.assertEqual('DONE', task['status'])

    def test_task_delete_is_an_alias_to_destroy(self):
        self.assertTrue(Task.delete == Task.destroy)

    def test_no_need_to_refresh_tasks_after_creation(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/tasks.json'):
            initial_size = len(user.tasks())

        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_valid.json'):
            new_task = Task.create(user=user, title='New Task')

        self.assertTrue(new_task in user.tasks())

    def test_task_have_subtasks_that_are_tasks_too(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_new_parent.json'):
            parent = Task.create(user=user, title='Parent')

        self.assertEqual([], parent.subtasks())

        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_new_subtask.json'):
            new_task = Task.create(user=parent.user, title='New subtask', parentGlobalTaskId=parent['id'])

        self.assertEqual(new_task, parent.subtasks()[0])

    def test_subtask_could_be_created_directly(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_new_parent.json'):
            parent = Task.create(user=user, title='Parent')

        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_new_subtask.json'):
            new_task = parent.create_subtask(title='New subtask')

        self.assertEqual(new_task, parent.subtasks()[0])

    def test_subtask_could_be_added_as_another_task(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_new_parent.json'):
            parent = Task.create(user=user, title='Parent')

        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_new_subtask.json'):
            subtask = parent.create_subtask(title='New subtask')

        with vcr.use_cassette('fixtures/vcr_cassettes/task_add_subtask.json'):
            parent.add_subtask(subtask)

        self.assertEqual(subtask, parent.subtasks()[0])

    def test_task_has_notes(self):
        task = self.__get_task()
        self.assertEqual([], task.notes())

    def test_text_notes_could_be_added_to_task(self):
        user = self.get_me()
        note = 'first one'

        with vcr.use_cassette('fixtures/vcr_cassettes/task_create_new_for_notes.json'):
            task = Task.create(user=user, title='I have notes')

        with vcr.use_cassette('fixtures/vcr_cassettes/task_add_some_notes.json'):
            task.add_note(note)

        self.assertTrue(note in task.notes())

    def test_tasks_filtered_by_checked_status(self):
        user = self.get_me()

        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_after_check.json'):
            none_checked_tasks = user.tasks(
                refresh=True,
                include_done=False,
                include_deleted=False,
                include_checked=False
            )

            self.assertEqual(None, next((task for task in none_checked_tasks if task['status'] == 'CHECKED'), None))

        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_after_check.json'):
            checked_tasks = user.tasks(
                refresh=True,
                include_done=False,
                include_deleted=False,
                include_unchecked=False
            )
            self.assertEqual(None, next((task for task in checked_tasks if task['status'] == 'UNCHECKED'), None))

    def test_tasks_filtered_by_done_status_without_refresh(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_with_done.json'):
            user.tasks(refresh=True, include_done=True)

        with vcr.use_cassette('fixtures/vcr_cassettes/fake.json', record_mode='none'):
            none_done_tasks = user.tasks(include_done=False)
            self.assertEqual(None, next((task for task in none_done_tasks if task['status'] == 'DONE'), None))

    def test_tasks_filtered_by_deleted_status_without_refresh(self):
        user = self.get_me()
        with vcr.use_cassette('fixtures/vcr_cassettes/tasks_with_deleted.json'):
            user.tasks(refresh=True, include_deleted=True)

        with vcr.use_cassette('fixtures/vcr_cassettes/fake.json', record_mode='none'):
            none_deleted_tasks = user.tasks(include_deleted=False)
            self.assertEqual(None, next((task for task in none_deleted_tasks if task['status'] == 'DELETED'), None))

# refresh task / user ?
# timers validatons
# categoryId='_SJ3OZLSxze2jAe23ZUEPg==',

#                dueDate=1445331600000,#int((time.time() + 3600) * 1000),
#                repeating=False,
#                repeatingMethod='TASK_REPEAT_OFF',
#                latitude=None,
#                longitude=None,
#                shared=False,
#                expanded=False,
#                alert={ 'type': 'NONE' },

if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
