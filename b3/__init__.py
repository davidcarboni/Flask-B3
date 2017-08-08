from flask import g, request
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
    "X-B3-Flags" for the current span or subspan. NB some of the values are likely be None,
    but all keys will be present.
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


def start_span(request_headers=None):
    """Collects incoming B3 headers and sets up values for this request as needed.
    The collected/computed values are stored on the application context g using the defined http header names as keys.
    :param request_headers: Incoming request headers can be passed explicitly.
    If not passed, Flask request.headers will be used. This enables you to pass this function to Flask.before_request().
    :param headers: The request headers dict
    """
    global debug
    try:
        headers = request_headers if request_headers else request.headers
    except RuntimeError:
        # We're probably working outside the Application Context at this point, likely on startup:
        # https://stackoverflow.com/questions/31444036/runtimeerror-working-outside-of-application-context
        # We return a dict of empty values so the expected keys are present.
        headers = {}

    trace_id = headers.get(b3_trace_id)
    parent_span_id = headers.get(b3_parent_span_id)
    span_id = headers.get(b3_span_id)
    sampled = headers.get(b3_sampled)
    flags = headers.get(b3_flags)
    root_span = not trace_id

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

    _info("Server receive. Starting span" if trace_id else "Root span")
    _log.debug("Resolved B3 values: {values}".format(values=values()))


def end_span(response=None):
    """Logs the end of a span.
    This function can be passed to Flask.after_request() if you'd like a log message to confirm the end of a span.
    :param response: If this furction is passed to Flask.after_request(), this will be passed by the framework.
    :return: the response parameter is returned as passed.
    """
    end_subspan()
    _info("Server send. Closing span")
    return response


def start_subspan(headers=None):
    """ Sets up a new span to contact a downstream service.
    This is used when making a downstream service call. It returns a dict containing the required sub-span headers.
    Each downstream call you make is handled as a new span, so call this every time you need to contact another service.

    This temporarily updates what's returned by values() to match the sub-span, so it can can also be used when calling
    e.g. a database that doesn't support B3. You'll still be able to record the client side of an interaction,
    even if the downstream server doesn't use the propagated trace information.

    You'll need to call end_subspan when you're done:

        headers_b3 = start_subspan([headers])
        try:

            ... log.debug("Client start: calling downstream service")
            ... requests.get(<downstream service>, headers=headers_b3)
            ... log.debug("Client receive: downstream service responded")

        finally:
            end_subspan()

    For the specification, see: https://github.com/openzipkin/b3-propagation
    :param headers: The headers dict. Headers will be added to this as needed.
    :return: A dict containing header values for a downstream request.
    This can be passed directly to e.g. requests.get(...).
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

    # Set up headers
    # NB dict() ensures we don't alter the value passed in. Maybe that's too conservative?
    result = dict(headers or {})
    result.update({
        b3_trace_id: g.subspan[b3_trace_id],
        b3_span_id: g.subspan[b3_span_id],
        b3_parent_span_id: g.subspan[b3_parent_span_id],
    })

    # Propagate only if set:
    if g.subspan[b3_sampled]:
        result[b3_sampled] = g.subspan[b3_sampled]
    if g.subspan[b3_flags]:
        result[b3_flags] = g.subspan[b3_flags]

    _info("Client start. Starting sub-span")
    _log.debug("B3 values for sub-span: {b3_headers}".format(b3_headers=values()))
    _log.debug("All headers for downstream request: {b3_headers}".format(b3_headers=result))

    return result


def end_subspan():
    """ Removes the headers for a sub-span.
    You should call this in e.g. a finally block when you have finished making a downstream service call.
    For the specification, see: https://github.com/openzipkin/b3-propagation
    """
    try:
        if g.get("subspan"):
            _info("Client receive. Closing sub-span")
            g.pop("subspan", None)
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


def _info(message):
    """Convenience function to log current span values.
    """
    span = values()
    _log.info(message + ": {span} in trace {trace}. (Parent span: {parent}).".format(
        span=span.get(b3_span_id),
        trace=span.get(b3_trace_id),
        parent=span.get(b3_parent_span_id),
    ))
