from flask import Flask
import logging
import sleuth
import b3


app = Flask("test")

# Before and after request to process B3 values and log span boundaries
app.before_request(b3.start_span)
app.after_request(b3.end_span)

# Set up logging to display trace information
logging.getLogger().setLevel(logging.DEBUG)
log = logging.getLogger(__name__)


@app.route("/")
def home():
    log.info("Starting")

    with b3.SubSpan() as headers:
        # Pretend to call a downstream service in the sub-span
        log.info("Calling downstream with headers: {}".format(headers))

    log.info("Finishing")

    return "Ohai!"

app.run(debug=True)
