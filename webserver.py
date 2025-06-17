from flask import Flask, jsonify
import threading

app = Flask('')
bot_instance = None  # Store a reference to the bot

@app.route('/')
def home():
    return "I'm alive!"

@app.route('/health')
def health():
    global bot_instance
    if bot_instance and hasattr(bot_instance, 'is_ready') and bot_instance.is_ready():
        return jsonify({"status": "ok", "bot": "ready"}), 200
    else:
        return jsonify({"status": "degraded", "bot": "not ready"}), 503

def keep_alive(bot):
    global bot_instance
    bot_instance = bot
    # Run Flask in a separate thread so it doesn't block the bot
    thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    thread.daemon = True
    thread.start()

@app.before_request
def skip_logging_for_health():
    # Suppress logs for /health endpoint and HEAD requests (UptimeRobot uses HEAD)
    if request.path == "/health":
        # Werkzeug (Flask’s dev server) logs using 'werkzeug' logger
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
    else:
        logging.getLogger('werkzeug').setLevel(logging.INFO)
