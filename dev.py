from werkzeug.serving import run_simple
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Ensure lib and api folders are in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.transcribe import app as transcribe_app
from api.generate_mom import app as generate_app
from api.meetings import app as meetings_app
from api.health import app as health_app
from flask import Flask, send_from_directory

static_app = Flask(__name__)
@static_app.route('/', defaults={'path': 'index.html'})
@static_app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('public', path)

application = DispatcherMiddleware(static_app, {
    '/api/transcribe': transcribe_app,
    '/api/generate_mom': generate_app,
    '/api/meetings': meetings_app,
    '/api/health': health_app
})

if __name__ == '__main__':
    print("Starting local dev server for Vercel endpoints on http://127.0.0.1:5000")
    run_simple('0.0.0.0', 5000, application, use_reloader=True, use_debugger=True)
