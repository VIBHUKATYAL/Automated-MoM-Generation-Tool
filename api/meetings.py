from flask import Flask, request, jsonify
from lib.supabase import get_supabase
from lib.assemblyai import get_transcript_status

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET'])
def get_meeting(path):
    meeting_id = request.args.get('id')
    if not meeting_id:
        return jsonify({"error": "Missing id parameter"}), 400
        
    sb = get_supabase()
    res = sb.table("meetings").select("*").eq("id", meeting_id).execute()
    
    if not res.data:
        return jsonify({"error": "Meeting not found"}), 404
        
    meeting = res.data[0]
    
    # If the status is transcribing, we should check AssemblyAI for updates
    if meeting.get("processing_status") == "transcribing":
        raw_id = meeting.get("original_transcript", "")
        if raw_id.startswith("aai_id:"):
            transcript_id = raw_id.split(":")[1]
            aai_status = get_transcript_status(transcript_id)
            
            if aai_status["status"] == "completed":
                # Update DB and state
                sb.table("meetings").update({
                    "processing_status": "transcribed",
                    "original_transcript": aai_status["text"]
                }).eq("id", meeting_id).execute()
                meeting["processing_status"] = "transcribed"
                meeting["original_transcript"] = aai_status["text"]
                
            elif aai_status["status"] == "error":
                sb.table("meetings").update({
                    "processing_status": "failed",
                    "error_message": aai_status["error"]
                }).eq("id", meeting_id).execute()
                meeting["processing_status"] = "failed"
                meeting["error_message"] = aai_status["error"]
                
    return jsonify(meeting)
