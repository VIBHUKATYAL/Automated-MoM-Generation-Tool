from flask import Flask, jsonify
from lib.supabase import get_supabase

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'OPTIONS'])
def get_history(path):
    sb = get_supabase()
    try:
        res = sb.table("meetings").select("id, created_at, title, mom_json").eq("processing_status", "completed").order("created_at", desc=True).limit(20).execute()
        return jsonify({"success": True, "history": res.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
