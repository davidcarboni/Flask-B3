from flask import g
from binascii import hexlify
import os

debug = False


def b3_values():
    """Get the full set of B3 values.
    :return: A dict containing the values "X-B3-TraceId", "X-B3-ParentSpanId", "X-B3-SpanId", "X-B3-Sampled" and
    "X-B3-Flags" for the current span.
    """
    return {
        'X-B3-TraceId': g.get('X-B3-TraceId'),
        'X-B3-ParentSpanId': g.get('X-B3-ParentSpanId'),
        'X-B3-SpanId': g.get('X-B3-SpanId'),
        'X-B3-Sampled': g.get('X-B3-Sampled'),
        'X-B3-Flags': g.get('X-B3-Flags'),
    }


def collect_request_headers(header_values):
    """Collects B3 headers and sets up values for this request as needed.
    The collected/computed values are stored on the application context g using the defined http header names as keys.
    :param header_values: The request headers
    """
    global debug

    # Collect (or generate) a trace ID
    setattr(g, 'X-B3-TraceId', header_values.get('X-B3-TraceId') or _generate_identifier())

    # Parent span, if present
    setattr(g, 'X-B3-ParentSpanId', header_values.get('X-B3-ParentSpanId'))

    # Collect (or set) the span ID
    setattr(g, 'X-B3-SpanId', header_values.get('X-B3-SpanId') or g.get('X-B3-TraceId'))

    # Collect the "sampled" flag, if present
    # We'll propagate the sampled value unchanged if it's set.
    # We're not currently recording traces so if it's present,
    # follow the standard and propagate it, otherwise it's ok to leave it out, rather than set it to "0".
    # This allows downstream services to make the decision if they want to.
    setattr(g, 'X-B3-Sampled', header_values.get('X-B3-Sampled'))

    # Set or update the debug setting
    # We'll set it to "1" if debug=True, otherwise we'll propagate it if present.
    setattr(g, 'X-B3-Flags', "1" if debug else header_values.get('X-B3-Flags'))


def add_request_headers(header_values):
    """ Adds the required headers to the given header dict.
    For the specification, see: https://github.com/openzipkin/b3-propagation
    :param header_values: The headers dict. Headers will be added to this as needed.
    """
    b3 = b3_values()
    # Propagate the trace ID
    header_values['X-B3-TraceId'] = b3['X-B3-TraceId']
    # New span for the outgoing request
    header_values['X-B3-SpanId'] = _generate_identifier()
    # Note the parent span as the current span
    header_values['X-B3-ParentSpanId'] = b3['X-B3-SpanId']
    # Propagate-if-set:
    if b3['X-B3-Sampled']:
        header_values['X-B3-Sampled'] = b3['X-B3-Sampled']
    if b3['X-B3-Flags']:
        header_values['X-B3-Flags'] = b3['X-B3-Flags']


def _generate_identifier():
    """
    Generates a new, random identifier in B3 format.
    :return: A 64-bit random identifier, rendered as a hex String.
    """
    bit_length = 64
    byte_length = int(bit_length / 8)
    identifier = os.urandom(byte_length)
    return hexlify(identifier).decode("ascii")
