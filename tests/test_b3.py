import unittest
import re
from flask import Flask
import flask_b3.b3


class TestB3(unittest.TestCase):
    def setUp(self):
        self.app = Flask("test")

    def tearDown(self):
        flask_b3.b3.debug = False

    def test_should_generate_root_span_ids(self):
        with self.app.app_context():
            # Given
            # No B3 headers - this is the root span
            flask_b3.b3.collect_request_headers({})

            # When
            # We get the B3 values
            b3 = flask_b3.b3.b3_values()

            # Then
            # A trace ID should have been genenated
            self.assertTrue(b3['X-B3-TraceId'])
            # A span ID should have been generated
            self.assertTrue(b3['X-B3-SpanId'])
            # The IDs should be 16 characters of hex
            self.assertTrue(re.match("[a-fA-F0-9]{16}", b3['X-B3-TraceId']))
            self.assertTrue(re.match("[a-fA-F0-9]{16}", b3['X-B3-SpanId']))

    def test_should_maintain_trace_id(self):
        with self.app.app_context():
            # Given
            # A trace ID in the B3 headers
            trace_id = "Barbapapa"
            flask_b3.b3.collect_request_headers({'X-B3-TraceId': trace_id})

            # When
            # We get b3 values and update onward request headers
            b3 = flask_b3.b3.b3_values()
            headers = {}
            flask_b3.b3.add_request_headers(headers)

            # Then
            # The incoming trace ID should be maintained
            self.assertEqual(trace_id, b3['X-B3-TraceId'])
            self.assertEqual(trace_id, headers['X-B3-TraceId'])

    def test_should_propagate_span_id_as_parent(self):
        with self.app.app_context():
            # Given
            # A trace ID in the B3 headers
            span_id = "Barbabright"
            flask_b3.b3.collect_request_headers({'X-B3-SpanId': span_id})

            # When
            # We update onward request headers
            headers = {}
            flask_b3.b3.add_request_headers(headers)

            # Then
            # The incoming trace ID should be propagated
            self.assertEqual(span_id, headers['X-B3-ParentSpanId'])

    def test_should_propagate_with_new_span_id(self):
        with self.app.app_context():
            # Given
            # A trace ID in the B3 headers
            span_id = "Barbazoo"
            flask_b3.b3.collect_request_headers({'X-B3-SpanId': span_id})

            # When
            # We update onward request headers
            headers = {}
            flask_b3.b3.add_request_headers(headers)

            # Then
            # The incoming trace ID should be propagated
            self.assertNotEqual(span_id, headers['X-B3-SpanId'])
            # The ID should be 16 characters of hex
            self.assertTrue(re.match("[a-fA-F0-9]{16}", headers['X-B3-SpanId']))

    def test_should_not_set_sampled(self):
        with self.app.app_context():
            # Given
            # Sampled is not set in the request headers
            flask_b3.b3.collect_request_headers({})

            # When
            # We get b3 values and update onward request headers
            b3 = flask_b3.b3.b3_values()
            headers = {}
            flask_b3.b3.add_request_headers(headers)

            # Then
            # Sampled should not be set and should remain absent from onward request headers
            self.assertIsNone(b3['X-B3-Sampled'])
            self.assertFalse('X-B3-Sampled' in headers)

    def test_should_maintain_sampled(self):
        with self.app.app_context():
            # Given
            # Sampled is not set in the request headers
            sampled = '0'
            flask_b3.b3.collect_request_headers({'X-B3-Sampled': sampled})

            # When
            # We get b3 values and update onward request headers
            b3 = flask_b3.b3.b3_values()
            headers = {}
            flask_b3.b3.add_request_headers(headers)

            # Then
            # The Sampled value should be maintained
            self.assertEqual(sampled, b3['X-B3-Sampled'])
            self.assertEqual(sampled, headers['X-B3-Sampled'])

    def test_should_maintain_flags_for_debug(self):
        with self.app.app_context():
            # Given
            # Flags is set in the B3 headers
            flags = '1'
            flask_b3.b3.collect_request_headers({'X-B3-Flags': flags})

            # When
            # We get b3 values and update onward request headers
            b3 = flask_b3.b3.b3_values()
            headers = {}
            flask_b3.b3.add_request_headers(headers)

            # Then
            # Flags should be set to 1 to indicate debug
            self.assertEqual(flags, b3['X-B3-Flags'])
            self.assertEqual(flags, headers['X-B3-Flags'])

    def test_should_set_flags_for_debug(self):
        with self.app.app_context():
            # Given
            # We have set debug on
            flask_b3.b3.debug = True
            flask_b3.b3.collect_request_headers({})

            # When
            # We get b3 values and update onward request headers
            b3 = flask_b3.b3.b3_values()
            headers = {}
            flask_b3.b3.add_request_headers(headers)

            # Then
            # Flags should be set to 1 to indicate debug
            self.assertEqual("1", b3['X-B3-Flags'])
            self.assertEqual("1", headers['X-B3-Flags'])


if __name__ == '__main__':
    unittest.main()
