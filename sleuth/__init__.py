import os
from threading import current_thread
import logging
from logging import Formatter
from flask import current_app
import b3

_log_format = '%(asctime)s %(levelname_spring)+5s %(tracing_information)s' \
              '%(process_id)s --- [%(thread_name)+15s] %(logger_name)-40s : %(message)s'
_python_record_factory = None


def _python3_record_factory(*args, **kwargs):
    """Python 3 approach to custom logging, using `logging.getLogRecord(...)`

    Inspireb by: https://docs.python.org/3/howto/logging-cookbook.html#customizing-logrecord

    :return: A log record augmented with the values required by LOG_FORMAT, as per `_update_record(...)`
    """
    record = _python_record_factory(*args, **kwargs)
    _update_record(record)
    return record


class Python2Formatter(Formatter):
    """ Python 2 approach to custom logging, using `logging.getLogRecord(...)`

    Inspired by: http://masnun.com/2015/11/04/python-writing-custom-log-handler-and-formatter.html

    Formats a log record with the values required by LOG_FORMAT, as added by `_update_record(...)`
    """

    def __init__(self):
        super(self.__class__, self).__init__(fmt=_log_format)

    def format(self, record):
        _update_record(record)
        return super(self.__class__, self).format(record)


def _update_record(record):
    """Collates values needed by LOG_FORMAT

    This adds additional information to the log record to implement the logging standard.

    :return: A log record augmented with the values required by LOG_FORMAT:
     * levelname_spring: specifically, "WARN" instead of "WARNING"
     * process_id
     * thread_name
     * logger_name
     * tracing_information: if B3 values have not been collected this will be an empty string
    """

    # Standard fields
    record.levelname_spring = "WARN" if record.levelname == "WARNING" else record.levelname
    record.process_id = str(os.getpid())
    record.thread_name = (current_thread().getName())[:15]
    record.logger_name = record.name[:40]
    record.tracing_information = ""

    # Optional distributed tracing information
    tracing_information = _tracing_information()
    if tracing_information:
        record.tracing_information = "[" + ",".join(tracing_information) + "] "


def _tracing_information():
    """Gets B3 distributed tracing information, if available.
     This is returned as a list, ready to be formatted into Spring Cloud Sleuth compatible format.
     """

    # We'll collate trace information if the B3 headers have been collected:
    values = b3.values()
    if values[b3.b3_trace_id]:
        # Trace information would normally be sent to Zipkin if either of sampled or debug ("flags") is set to 1
        # However we're not currently using Zipkin, so it's always false
        # exported = "true" if values[b3.b3_sampled] == '1' or values[b3.b3_flags] == '1' else "false"

        return [
            current_app.name if current_app.name else " - ",
            values[b3.b3_trace_id],
            values[b3.b3_span_id],
            "false",
        ]


# Set up the log format
logging.basicConfig(format=_log_format)

if hasattr(logging, "getLogRecordFactory"):
    # Python 3 solution
    # getLogRecordFactory was introduced in Python 3
    _python_record_factory = logging.getLogRecordFactory()
    logging.setLogRecordFactory(_python3_record_factory)
else:
    # Python 2 fallback
    # # set the formatter for all handlers on the root logger.
    for handler in logging.getLogger().handlers:
        handler.setFormatter(Python2Formatter())
