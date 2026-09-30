import os
import assemblyai as aai

def transcribe_audio_with_diarization(file_path: str) -> str:
    """
    Transcribes an audio file using AssemblyAI and returns a diarized transcript.
    """
    aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not aai.settings.api_key:
        raise ValueError("ASSEMBLYAI_API_KEY is not set.")

    # Request speaker labels (diarization)
    config = aai.TranscriptionConfig(speaker_labels=True)
    transcriber = aai.Transcriber()
    
    transcript = transcriber.transcribe(
        file_path,
        config=config
    )
    
    if transcript.status == aai.TranscriptStatus.error:
        raise Exception(f"Transcription failed: {transcript.error}")
        
    if not bool(getattr(transcript, 'text', '')):
        raise ValueError(f"AssemblyAI returned 0 words. File size sent: {os.path.getsize(file_path)} bytes.")
        
    diarized_text = ""
    if getattr(transcript, 'utterances', None):
        for utterance in transcript.utterances:
            diarized_text += f"Speaker {utterance.speaker}: {utterance.text}\n"
    else:
        diarized_text = transcript.text

    # Basic backup check
    if not diarized_text.strip():
        raise ValueError("After AssemblyAI parsing, the text was unexpectedly empty.")
        
    print(f"[DEBUG AssemblyAI] Diarized text length: {len(diarized_text)}")
    print(f"[DEBUG AssemblyAI] Raw text length: {len(transcript.text) if hasattr(transcript, 'text') and transcript.text else 0}")
    
    return diarized_text
