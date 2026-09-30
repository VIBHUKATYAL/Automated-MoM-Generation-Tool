from flask import Flask, request, jsonify
import tempfile
import os
from lib.assemblyai import transcribe_audio_async
from lib.supabase import get_supabase

# Vercel entrypoint
app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['POST'])
def transcribe(path):
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_path = temp_audio.name
        file.save(temp_path)
        
        # 1. Start AssemblyAI transcription asynchronously
        transcript_id = transcribe_audio_async(temp_path)
        
        # 2. Insert into Supabase
        sb = get_supabase()
        response = sb.table("meetings").insert({
            "title": file.filename,
            "processing_status": "transcribing"
        }).execute()
        
        data = response.data[0]
        meeting_id = data["id"]
        
        # Store transcript ID temporarily in error_message or a new column?
        # Actually, let's keep it in "original_transcript" as a placeholder ID
        sb.table("meetings").update({"original_transcript": f"aai_id:{transcript_id}"}).eq("id", meeting_id).execute()
        
        # Fast response
        return jsonify({
            "meeting_id": meeting_id,
            "status": "transcribing"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
