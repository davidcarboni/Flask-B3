from flask import Flask
import logging
import flask_sleuth
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
    log.info("Working")

    b3.start_subspan()
    try:
        # Pretend to call a downstream service in the sub-span
        log.info("Calling downstream...")
    finally:
        b3.end_subspan()

    log.info("Finishing")

    return "Ohai!"

app.run(debug=True)
