import os
import assemblyai as aai

def transcribe_audio_async(file_path: str) -> str:
    """Submits file for transcription and returns immediately with transcript ID"""
    aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not aai.settings.api_key:
        raise ValueError("ASSEMBLYAI_API_KEY is not set.")

    config = aai.TranscriptionConfig(speaker_labels=True)
    transcriber = aai.Transcriber()
    transcript = transcriber.submit(
        file_path,
        config=config
    )
    return transcript.id

def get_transcript_status(transcript_id: str) -> dict:
    """Returns the transcript status and the final diarized text if available"""
    aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not aai.settings.api_key:
        raise ValueError("ASSEMBLYAI_API_KEY is not set.")

    transcript = aai.Transcript.get_by_id(transcript_id)
    
    if transcript.status == aai.TranscriptStatus.error:
        return {"status": "error", "error": transcript.error, "text": None}
        
    if transcript.status != aai.TranscriptStatus.completed:
        return {"status": transcript.status, "text": None}
        
    diarized_text = ""
    if getattr(transcript, "utterances", None):
        for utterance in transcript.utterances:
            diarized_text += f"Speaker {utterance.speaker}: {utterance.text}`n"
    else:
        diarized_text = transcript.text or ""
        
    if not diarized_text.strip():
        return {"status": "error", "error": "AssemblyAI returned completely empty text.", "text": None}
        
    return {"status": "completed", "text": diarized_text}
