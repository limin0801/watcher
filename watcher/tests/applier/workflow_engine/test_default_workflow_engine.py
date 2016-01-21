# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import abc
import mock

import six
from stevedore import driver
from stevedore import extension

from watcher.applier.actions import base as abase
from watcher.applier.workflow_engine import default as tflow
from watcher.common import utils
from watcher import objects
from watcher.tests.db import base


@six.add_metaclass(abc.ABCMeta)
class FakeAction(abase.BaseAction):
    def precondition(self):
        pass

    def revert(self):
        pass

    def execute(self):
        raise Exception()

    @classmethod
    def namespace(cls):
        return "TESTING"

    @classmethod
    def get_name(cls):
        return 'fake_action'


class TestDefaultWorkFlowEngine(base.DbTestCase):
    def setUp(self):
        super(TestDefaultWorkFlowEngine, self).setUp()
        self.engine = tflow.DefaultWorkFlowEngine()
        self.engine.context = self.context
        self.engine.applier_manager = mock.MagicMock()

    def test_execute(self):
        actions = mock.MagicMock()
        result = self.engine.execute(actions)
        self.assertEqual(result, True)

    def create_action(self, action_type, applies_to, parameters, next):
        action = {
            'uuid': utils.generate_uuid(),
            'action_plan_id': 0,
            'action_type': action_type,
            'applies_to': applies_to,
            'input_parameters': parameters,
            'state': objects.action.Status.PENDING,
            'alarm': None,
            'next': next,
        }
        new_action = objects.Action(self.context, **action)
        new_action.create(self.context)
        new_action.save()
        return new_action

    def check_action_state(self, action, expected_state):
        to_check = objects.Action.get_by_uuid(self.context, action.uuid)
        self.assertEqual(to_check.state, expected_state)

    def check_actions_state(self, actions, expected_state):
        for a in actions:
            self.check_action_state(a, expected_state)

    def test_execute_with_no_actions(self):
        actions = []
        result = self.engine.execute(actions)
        self.assertEqual(result, True)

    def test_execute_with_one_action(self):
        actions = [self.create_action("nop", "", {'message': 'test'}, None)]
        result = self.engine.execute(actions)
        self.assertEqual(result, True)
        self.check_actions_state(actions, objects.action.Status.SUCCEEDED)

    def test_execute_with_two_actions(self):
        actions = []
        next = self.create_action("sleep", "", {'duration': '0'}, None)
        first = self.create_action("nop", "", {'message': 'test'}, next.id)

        actions.append(first)
        actions.append(next)

        result = self.engine.execute(actions)
        self.assertEqual(result, True)
        self.check_actions_state(actions, objects.action.Status.SUCCEEDED)

    def test_execute_with_three_actions(self):
        actions = []
        next2 = self.create_action("nop", "vm1", {'message': 'next'}, None)
        next = self.create_action("sleep", "vm1", {'duration': '0'}, next2.id)
        first = self.create_action("nop", "vm1", {'message': 'hello'}, next.id)
        self.check_action_state(first, objects.action.Status.PENDING)
        self.check_action_state(next, objects.action.Status.PENDING)
        self.check_action_state(next2, objects.action.Status.PENDING)

        actions.append(first)
        actions.append(next)
        actions.append(next2)

        result = self.engine.execute(actions)
        self.assertEqual(result, True)
        self.check_actions_state(actions, objects.action.Status.SUCCEEDED)

    def test_execute_with_exception(self):
        actions = []
        next2 = self.create_action("no_exist",
                                   "vm1", {'message': 'next'}, None)
        next = self.create_action("sleep", "vm1",
                                  {'duration': '0'}, next2.id)
        first = self.create_action("nop", "vm1",
                                   {'message': 'hello'}, next.id)

        self.check_action_state(first, objects.action.Status.PENDING)
        self.check_action_state(next, objects.action.Status.PENDING)
        self.check_action_state(next2, objects.action.Status.PENDING)
        actions.append(first)
        actions.append(next)
        actions.append(next2)

        result = self.engine.execute(actions)
        self.assertEqual(result, False)
        self.check_action_state(first, objects.action.Status.SUCCEEDED)
        self.check_action_state(next, objects.action.Status.SUCCEEDED)
        self.check_action_state(next2, objects.action.Status.FAILED)

    @mock.patch("watcher.common.loader.default.DriverManager")
    def test_execute_with_action_exception(self, m_driver):
        m_driver.return_value = driver.DriverManager.make_test_instance(
            extension=extension.Extension(name=FakeAction.get_name(),
                                          entry_point="%s:%s" % (
                                          FakeAction.__module__,
                                          FakeAction.__name__),
                                          plugin=FakeAction,
                                          obj=None),
            namespace=FakeAction.namespace())
        actions = [self.create_action("dontcare", "vm1", {}, None)]
        result = self.engine.execute(actions)
        self.assertEqual(result, False)
        self.check_action_state(actions[0], objects.action.Status.FAILED)
