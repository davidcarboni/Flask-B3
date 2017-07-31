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
    try:
        # Check if there's a sub-span in progress, otherwise use the main span:
        span = g.get("subspan") if "subspan" in g else g
        for header in b3_headers:
            result[header] = span.get(header)
    except RuntimeError:
        # We're probably working outside the Application Context at this point, likely on startup:
        # https://stackoverflow.com/questions/31444036/runtimeerror-working-outside-of-application-context
        # We return a dict of empty values so the expected keys are present.
        for header in b3_headers:
            result[header] = None

    return result


def collect_incoming_headers(headers):
    """Collects B3 headers and sets up values for this request as needed.
    The collected/computed values are stored on the application context g using the defined http header names as keys.
    :param headers: The request headers dict
    """
    global debug
    _log.debug("Received incoming headers: " + str(headers))

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


def add_subspan_headers(headers):
    """ Adds the required sub-span headers to the given header dict.
    This is used when making a downstream service call.
    For the specification, see: https://github.com/openzipkin/b3-propagation
    :param headers: The headers dict. Headers will be added to this as needed.
    :return: For convenience, the headers parameter is returned after being updated.
    This allows you to pass the result of this function directly to e.g. requests.get(...).
    """
    b3 = values()
    g.subspan = {

        # Propagate the trace ID
        b3_trace_id: b3[b3_trace_id],

        # Start a new span for the outgoing request
        b3_span_id: _generate_identifier(),

        # Set the current span as the parent span
        b3_parent_span_id: b3[b3_span_id],

        b3_sampled: b3[b3_sampled],
        b3_flags: b3[b3_flags],
    }

    _log.debug("B3 values for outgoing headers: {b3_headers}".format(
        b3_headers=g.subspan))

    # Update headers
    headers[b3_trace_id] = g.subspan[b3_trace_id]
    headers[b3_span_id] = g.subspan[b3_span_id]
    headers[b3_parent_span_id] = g.subspan[b3_parent_span_id]

    # Propagate only if set:
    if g.subspan[b3_sampled]:
        headers[b3_sampled] = g.subspan[b3_sampled]
    if g.subspan[b3_flags]:
        headers[b3_flags] = g.subspan[b3_flags]

    return headers


def remove_subspan_headers():
    """ Removes the headers for a sub-span.
    You should call this in e.g. a finally block when you have finished making a downstream service call.
    For the specification, see: https://github.com/openzipkin/b3-propagation
    """
    try:
        g.pop("subspan", None)
        _log.debug("Returned to span: " + str(values()))
    except RuntimeError:
        # We're probably working outside the Application Context at this point, likely on startup:
        # https://stackoverflow.com/questions/31444036/runtimeerror-working-outside-of-application-context
        pass


def _generate_identifier():
    """
    Generates a new, random identifier in B3 format.
    :return: A 64-bit random identifier, rendered as a hex String.
    """
    bit_length = 64
    byte_length = int(bit_length / 8)
    identifier = os.urandom(byte_length)
    return hexlify(identifier).decode('ascii')
