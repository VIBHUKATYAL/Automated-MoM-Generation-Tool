from flask import Flask, request, jsonify
from lib.supabase import get_supabase
from lib.llm_pipeline import process_entire_transcript

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['POST'])
def generate_mom(path):
    data = request.json or {}
    meeting_id = data.get('id')
    if not meeting_id:
        return jsonify({"error": "Missing id parameter"}), 400
        
    sb = get_supabase()
    res = sb.table("meetings").select("original_transcript", "processing_status").eq("id", meeting_id).execute()
    
    if not res.data:
        return jsonify({"error": "Meeting not found"}), 404
        
    meeting = res.data[0]
    
    if meeting.get("processing_status") != "transcribed":
        return jsonify({"error": f"Meeting status is {meeting.get('processing_status')}, not ready for MoM"}), 400
        
    transcript = meeting.get("original_transcript")
    if not transcript:
        return jsonify({"error": "Transcript is empty"}), 400
        
    # Mark as processing
    sb.table("meetings").update({"processing_status": "generating"}).eq("id", meeting_id).execute()
    
    try:
        final_mom = process_entire_transcript(transcript)
        
        # Save to DB
        sb.table("meetings").update({
            "processing_status": "completed",
            "summary": final_mom.summary,
            "key_points": final_mom.key_points,
            "decisions": [d for d in final_mom.decisions],
            "action_items": [a for a in final_mom.action_items],
            "next_meeting_scheduled": final_mom.next_meeting_scheduled
        }).eq("id", meeting_id).execute()
        
        return jsonify({
            "status": "completed",
            "meeting_id": meeting_id,
            "result": final_mom.model_dump()
        })
        
    except Exception as e:
        sb.table("meetings").update({
            "processing_status": "failed",
            "error_message": str(e)
        }).eq("id", meeting_id).execute()
        return jsonify({"error": str(e)}), 500
