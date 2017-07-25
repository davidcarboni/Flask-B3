# Flask B3

Implements B3 propagation for Python/Flask.

## B3

B3 is used by [Zipkin](http://zipkin.io/) for building distributed trace trees.
It's the set of headers and values you need to use when doing distributed tracing.

Specifically, this implements: https://github.com/openzipkin/b3-propagation

## Purpose

This code intentionally implements B3 only. 
It does not send tracing information to a Zipkin server.

There are two use cases:

 * You'd like a B3 implementation to base your own Zipkin instrumentation on.
 * You're interested in distributed logging, but not interested in using Zipkin.

## Motivation

I built this library to enable Python "play nicely" in a distributed tracing environment 
(specifically taking into account [Spring Cloud Sleuth](https://cloud.spring.io/spring-cloud-sleuth/)).

I want to be able to correlate logs across multiple services and
I don't need the full power of Zipkin at this stage.
This provides a relatively low-impact first-step on the distributed tracing journey.

B3 values are made available and headers can be generated for onward requests.
The B3 values can be included in [log lines sent to stdout](https://12factor.net/logs).
Aggregation of logs is externalised, keeping services small and focused.

## Usage

There are three key steps to using flask_b3:

### Collect B3 headers from an incoming request

This could be called from a Flask `before_request()` function, passing in `request.headers`.
This will generate any needed identifiers (e.g. for a root span):

    collect_request_headers(header_values)

### Access B3 values 

When you need to build log messages, 
this gets you a dict with keys that match the B3 header names 
(`X-B3-TraceId`, `X-B3-ParentSpanId`, `X-B3-SpanId`, `X-B3-Sampled` and `X-B3-Flags`): 

    b3_values()

### Add headers to onward requests

If your service needs to call other services, 
you'll need to add B3 headers to the outgoing request.
Pass in a dict of your headers to be updated with B3 headers.
This will generate the right B3 values for a new span in the trace:

    add_request_headers(header_values)

And that's it. The aim is to make it clean and simple to read and propagate B3 headers.

