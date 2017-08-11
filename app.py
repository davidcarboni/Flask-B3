from flask import Flask, jsonify
import logging
import b3


app = Flask("test")

# Before and after request to process B3 values and log span boundaries
app.before_request(b3.start_span)
app.after_request(b3.end_span)

# Set up logging to display trace information
log = logging.getLogger(__name__)


@app.route("/")
def home():
    print(logging.getLevelName(log.getEffectiveLevel()))
    log.warning("Starting with b3 values: {}".format(b3.values()))

    with b3.SubSpan() as headers:
        # Pretend to call a downstream service in the sub-span
        log.warning("Calling downstream service with b3 values: {}".format(b3.values()))

    log.warning("Finishing with b3 values: {}".format(b3.values()))

    return jsonify(b3.values())

app.run(debug=True)
