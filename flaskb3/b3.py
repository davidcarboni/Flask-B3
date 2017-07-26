from flask import g
from binascii import hexlify
import os
import logging

_log = logging.getLogger(__name__)

debug = False

b3_trace_id = 'X-B3-TraceId'
b3_parent_span_id = 'X-B3-ParentSpanId'
b3_span_id = 'X-B3-SpanId'
b3_sampled = 'X-B3-Sampled'
b3_flags = 'X-B3-Flags'
b3_headers = [b3_trace_id, b3_parent_span_id, b3_span_id, b3_sampled, b3_flags]


def values():
    """Get the full set of B3 values.
    :return: A dict containing the keys "X-B3-TraceId", "X-B3-ParentSpanId", "X-B3-SpanId", "X-B3-Sampled" and
    "X-B3-Flags" for the current span. NB some of the values are likely be None.
    """
    result = {}
    for header in b3_headers:
        result[header] = g.get(header)
    return result


def collect_incoming_headers(headers):
    """Collects B3 headers and sets up values for this request as needed.
    The collected/computed values are stored on the application context g using the defined http header names as keys.
    :param headers: The request headers dict
    """
    global debug

    trace_id = headers.get(b3_trace_id)
    parent_span_id = headers.get(b3_parent_span_id)
    span_id = headers.get(b3_span_id)
    sampled = headers.get(b3_sampled)
    flags = headers.get(b3_flags)

    if not trace_id:
        _log.debug("Root span")
    else:
        _log.debug("Span {span} in trace {trace}. Parent span is {parent}.".format(
            span=span_id,
            trace=trace_id,
            parent=parent_span_id))

    # Collect (or generate) a trace ID
    setattr(g, b3_trace_id, trace_id or _generate_identifier())

    # Parent span, if present
    setattr(g, b3_parent_span_id, parent_span_id)

    # Collect (or set) the span ID
    setattr(g, b3_span_id, span_id or g.get(b3_trace_id))

    # Collect the "sampled" flag, if present
    # We'll propagate the sampled value unchanged if it's set.
    # We're not currently recording traces to Zipkin, so if it's present, follow the standard and propagate it,
    # otherwise it's better to leave it out, rather than make it "0".
    # This allows downstream services to make a decision if they need to.
    setattr(g, b3_sampled, sampled)

    # Set or update the debug setting
    # We'll set it to "1" if debug=True, otherwise we'll propagate it if present.
    setattr(g, b3_flags, "1" if debug else flags)

    _log.debug("Resolved B3 values: {values}".format(values=values()))


def add_outgoing_headers(headers):
    """ Adds the required headers to the given header dict.
    For the specification, see: https://github.com/openzipkin/b3-propagation
    :param headers: The headers dict. Headers will be added to this as needed.
    """
    b3 = values()
    # Propagate the trace ID
    headers[b3_trace_id] = b3[b3_trace_id]
    # Start a new span for the outgoing request
    headers[b3_span_id] = _generate_identifier()
    # Set the current span as the parent span
    headers[b3_parent_span_id] = b3[b3_span_id]
    # Propagate-only-if-set:
    if b3[b3_sampled]:
        headers[b3_sampled] = b3[b3_sampled]
    if b3[b3_flags]:
        headers[b3_flags] = b3[b3_flags]

    _log.debug("Resolved B3 values: {b3_headers}".format(
        b3_headers={k: v for k, v in headers.items() if k in b3_headers}))


def _generate_identifier():
    """
    Generates a new, random identifier in B3 format.
    :return: A 64-bit random identifier, rendered as a hex String.
    """
    bit_length = 64
    byte_length = int(bit_length / 8)
    identifier = os.urandom(byte_length)
    return hexlify(identifier).decode('ascii')
