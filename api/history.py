from flask import Flask, jsonify
from lib.supabase import get_supabase

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'OPTIONS'])
def get_history(path):
    sb = get_supabase()
    try:
        res = sb.table("meetings").select("id, created_at, title, summary, key_points, decisions, action_items, next_meeting_scheduled").eq("processing_status", "completed").order("created_at", desc=True).limit(20).execute()
        
        # Reconsolidate into the mom_json unified schema for frontend parsing
        formatted = []
        for m in res.data or []:
            formatted.append({
                "id": m.get("id"),
                "created_at": m.get("created_at"),
                "title": m.get("title"),
                "mom_json": {
                    "title": m.get("title"),
                    "summary": m.get("summary"),
                    "key_points": m.get("key_points"),
                    "decisions": m.get("decisions"),
                    "action_items": m.get("action_items"),
                    "next_meeting_scheduled": m.get("next_meeting_scheduled")
                }
            })
            
        return jsonify({"success": True, "history": formatted})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
