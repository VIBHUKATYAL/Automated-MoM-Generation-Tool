import os
import tempfile
import json
from flask import Flask, request, jsonify, render_template, Response
from generator import generate_minutes_stream, refine_transcript_stream
from transcription import transcribe_audio_with_diarization
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate_mom', methods=['POST'])
def generate_mom():
    data = request.json
    if not data or 'transcript' not in data:
        return jsonify({'error': 'No transcript provided'}), 400
    
    transcript = data['transcript']
    provider = data.get('provider', os.getenv("PROVIDER", "groq"))
    
    def generate():
        try:
            for progress in generate_minutes_stream(transcript, provider):
                yield f"data: {json.dumps(progress)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
            
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/transcribe_and_generate_mom', methods=['POST'])
def transcribe_and_generate_mom():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    provider = request.form.get('provider', os.getenv("PROVIDER", "groq"))
    
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_path = temp_audio.name
        file.save(temp_path)
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        return jsonify({'error': str(e)}), 500
    
    def generate():
        try:
            yield f"data: {json.dumps({'status': 'transcribing_started'})}\n\n"
            raw_transcript = transcribe_audio_with_diarization(temp_path)
            
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
                
            yield f"data: {json.dumps({'status': 'transcribing_completed'})}\n\n"
            
            refined_transcript = ""
            for progress in refine_transcript_stream(raw_transcript, provider):
                if progress["status"] == "refining_completed":
                    refined_transcript = progress["result"]
                yield f"data: {json.dumps(progress)}\n\n"
                
            for progress in generate_minutes_stream(refined_transcript, provider):
                if progress["status"] == "completed":
                    progress["transcript"] = refined_transcript
                yield f"data: {json.dumps(progress)}\n\n"
                
        except Exception as e:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
            
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
