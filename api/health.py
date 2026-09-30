from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET'])
def health_check(path):
    return jsonify({
        "status": "ok",
        "message": "Automated MoM Generator API is running",
        "version": "1.0.0"
    })
