import os
import sys
import unittest
from unittest.mock import patch

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mrc.session_state import (
    is_handsfree_enabled,
    set_handsfree,
    get_all_session_states,
    clear_session_state
)

class TestSessionState(unittest.TestCase):

    def setUp(self):
        self.conv_id = "test-conv-abc-123"
        clear_session_state(self.conv_id)

    def tearDown(self):
        clear_session_state(self.conv_id)

    def test_default_handsfree_state_fallback(self):
        # Default should fallback to config (True by default)
        self.assertTrue(is_handsfree_enabled(self.conv_id))

    def test_explicit_set_handsfree_off(self):
        set_handsfree(self.conv_id, False)
        self.assertFalse(is_handsfree_enabled(self.conv_id))

    def test_explicit_set_handsfree_on(self):
        set_handsfree(self.conv_id, False)
        self.assertFalse(is_handsfree_enabled(self.conv_id))
        set_handsfree(self.conv_id, True)
        self.assertTrue(is_handsfree_enabled(self.conv_id))

    def test_multiple_conversations_isolated(self):
        conv1 = "conv-1"
        conv2 = "conv-2"
        set_handsfree(conv1, True)
        set_handsfree(conv2, False)
        self.assertTrue(is_handsfree_enabled(conv1))
        self.assertFalse(is_handsfree_enabled(conv2))
        clear_session_state(conv1)
        clear_session_state(conv2)
