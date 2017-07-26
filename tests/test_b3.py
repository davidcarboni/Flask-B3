import unittest
import re
from flask import Flask
from flaskb3 import b3
from flaskb3.b3 import b3_trace_id, b3_parent_span_id, b3_span_id, b3_sampled,b3_flags


class TestB3(unittest.TestCase):
    def setUp(self):
        self.app = Flask("test")

    def tearDown(self):
        b3.debug = False

    def test_should_generate_root_span_ids(self):
        with self.app.app_context():
            # Given
            # No B3 headers - this is the root span
            b3.collect_incoming_headers({})

            # When
            # We get the B3 values
            values = b3.values()

            # Then
            # Both trace ID and span ID should have been genenated
            self.assertTrue(values[b3_trace_id])
            self.assertTrue(values[b3_span_id])
            # The IDs should be 16 characters of hex
            self.assertTrue(re.match("[a-fA-F0-9]{16}", values[b3_trace_id]))
            self.assertTrue(re.match("[a-fA-F0-9]{16}", values[b3_span_id]))

    def test_should_maintain_trace_id(self):
        with self.app.app_context():
            # Given
            # A trace ID in the B3 headers
            trace_id = "Barbapapa"
            b3.collect_incoming_headers({b3_trace_id: trace_id})

            # When
            # We get b3 values and update onward request headers
            values = b3.values()
            headers = {}
            b3.add_outgoing_headers(headers)

            # Then
            # The incoming trace ID should be maintained
            self.assertEqual(trace_id, values[b3_trace_id])
            self.assertEqual(trace_id, headers[b3_trace_id])

    def test_should_propagate_span_id_as_parent(self):
        with self.app.app_context():
            # Given
            # A trace ID in the B3 headers
            span_id = "Barbabright"
            b3.collect_incoming_headers({b3_span_id: span_id})

            # When
            # We update onward request headers
            headers = {}
            b3.add_outgoing_headers(headers)

            # Then
            # The incoming trace ID should be propagated
            self.assertEqual(span_id, headers[b3_parent_span_id])

    def test_should_propagate_with_new_span_id(self):
        with self.app.app_context():
            # Given
            # A trace ID in the B3 headers
            span_id = "Barbazoo"
            b3.collect_incoming_headers({b3_span_id: span_id})

            # When
            # We update onward request headers
            headers = {}
            b3.add_outgoing_headers(headers)

            # Then
            # The incoming trace ID should be propagated
            self.assertNotEqual(span_id, headers[b3_span_id])
            # The ID should be 16 characters of hex
            self.assertTrue(re.match("[a-fA-F0-9]{16}", headers[b3_span_id]))

    def test_should_not_set_sampled(self):
        with self.app.app_context():
            # Given
            # Sampled is not set in the request headers
            b3.collect_incoming_headers({})

            # When
            # We get b3 values and update onward request headers
            values = b3.values()
            headers = {}
            b3.add_outgoing_headers(headers)

            # Then
            # Sampled should not be set and should
            # remain absent from onward request headers
            self.assertIsNone(values[b3_sampled])
            self.assertFalse(b3_sampled in headers)

    def test_should_maintain_sampled(self):
        with self.app.app_context():
            # Given
            # Sampled is not set in the request headers
            sampled = '0'
            b3.collect_incoming_headers({b3_sampled: sampled})

            # When
            # We get b3 values and update onward request headers
            values = b3.values()
            headers = {}
            b3.add_outgoing_headers(headers)

            # Then
            # The Sampled value should be maintained
            self.assertEqual(sampled, values[b3_sampled])
            self.assertEqual(sampled, headers[b3_sampled])

    def test_should_maintain_flags_for_debug(self):
        with self.app.app_context():
            # Given
            # Flags is set in the B3 headers
            flags = '1'
            b3.collect_incoming_headers({b3_flags: flags})

            # When
            # We get b3 values and update onward request headers
            values = b3.values()
            headers = {}
            b3.add_outgoing_headers(headers)

            # Then
            # Flags should be set to 1 to indicate debug
            self.assertEqual(flags, values[b3.b3_flags])
            self.assertEqual(flags, headers[b3_flags])

    def test_should_set_flags_for_debug(self):
        with self.app.app_context():
            # Given
            # We have set debug on
            b3.debug = True
            b3.collect_incoming_headers({})

            # When
            # We get b3 values and update onward request headers
            values = b3.values()
            headers = {}
            b3.add_outgoing_headers(headers)

            # Then
            # Flags should be set to 1 to indicate debug
            self.assertEqual("1", values[b3_flags])
            self.assertEqual("1", headers[b3_flags])


if __name__ == '__main__':
    unittest.main()
