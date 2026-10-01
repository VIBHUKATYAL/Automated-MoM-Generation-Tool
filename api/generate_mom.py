from flask import Flask, request, jsonify
from lib.supabase import get_supabase
from lib.llm_pipeline import process_entire_transcript

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def generate_mom(path):
    data = request.json or {}
    meeting_id = data.get('id')
    if not meeting_id:
        return jsonify({"error": "Missing id parameter"}), 400
        
    sb = get_supabase()
    res = sb.table("meetings").select("original_transcript", "processing_status", "title").eq("id", meeting_id).execute()
    
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
    
    title = meeting.get("title")
    print(f"Triggering generation for {meeting_id} (Title: {title}).")
    
    try:
        from lib.llm_pipeline import process_entire_transcript, process_single_shot_text
        
        if title == "Text Transcript":
            # Bypass MAP REDUCE for pure text
            final_mom = process_single_shot_text(transcript)
        else:
            # AssemblyAI outputs require mapping
            final_mom = process_entire_transcript(transcript)
        
        import json
        
        # Determine payload type to extract correctly
        if isinstance(final_mom, str):
            mom_dict = json.loads(final_mom)
        elif isinstance(final_mom, dict):
            mom_dict = final_mom
        else:
            mom_dict = final_mom.model_dump()
            
        update_payload = {
            "processing_status": "completed",
            "summary": mom_dict.get("summary", ""),
            "key_points": mom_dict.get("key_points", mom_dict.get("key_topics", [])),
            "decisions": mom_dict.get("decisions", []),
            "action_items": mom_dict.get("action_items", []),
            "next_meeting_scheduled": str(mom_dict.get("next_meeting_scheduled", "")) or str(mom_dict.get("open_questions", ""))
        }
        
        # Inject the dynamically synthesized smart title!
        if mom_dict.get("title"):
            update_payload["title"] = mom_dict.get("title")
            
        sb.table("meetings").update(update_payload).eq("id", meeting_id).execute()
        
        return jsonify({"status": "completed", "meeting_id": meeting_id, "result": mom_dict})
        
    except Exception as e:
        sb.table("meetings").update({
            "processing_status": "failed",
            "error_message": str(e)
        }).eq("id", meeting_id).execute()
        return jsonify({"error": str(e)}), 500
