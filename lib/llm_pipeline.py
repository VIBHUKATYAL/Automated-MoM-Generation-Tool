import os
import concurrent.futures
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json

class SegmentReduction(BaseModel):
    key_points: List[str] = Field(default_factory=list, description="Key points discussed in this segment")
    decisions: List[str] = Field(default_factory=list, description="Decisions made in this segment")
    action_items: List[str] = Field(default_factory=list, description="Tasks assigned in this segment, with owners and deadlines")
    open_questions: List[str] = Field(default_factory=list, description="Unresolved questions")
    important_context: List[str] = Field(default_factory=list, description="Crucial background information presented")

class FinalMeetingMinutes(BaseModel):
    summary: str = Field(..., description="High level summary of the entire meeting")
    key_points: List[str] = Field(default_factory=list, description="Combined key points")
    decisions: List[dict] = Field(default_factory=list, description="List of decisions with keys `decision` and `context`")
    action_items: List[dict] = Field(default_factory=list, description="List of tasks with keys `task`, `owner`, and `deadline`")
    next_meeting_scheduled: Optional[str] = Field(None, description="When the next meeting is scheduled, or null if none mentioned")

segment_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert transcriber. Reduce this transcript segment into compact structured information without losing details. Never invent information."),
    ("human", "{transcript}")
])

final_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an executive assistant. Merge the following partial meeting segment structures into a single cohesive Minutes of Meeting document. Remove duplicates but KEEP ALL actionable tasks and decisions. Never invent information."),
    ("human", "Historical Meeting Context:\n{context}\n\nSegment Summaries:\n{summaries}")
])

MAX_CHARS_PER_CHUNK = 8000

def get_groq_llm():
    keys = os.getenv("GROQ_API_KEY", "").split(",")
    # Just use first available key
    key = keys[0].strip() if keys else ""
    return init_chat_model("openai/gpt-oss-20b", model_provider="groq", groq_api_key=key)

def get_gemini_llm():
    return init_chat_model("gemini-3.5-flash", model_provider="google_genai")

def run_segment_reduction(transcript_segment: str) -> str:
    llm = get_groq_llm()
    chain = segment_prompt | llm.with_structured_output(SegmentReduction)
    result = chain.invoke({"transcript": transcript_segment})
    return result.model_dump_json(indent=2)

def chunk_transcript(transcript: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chars,
        chunk_overlap=300,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_text(transcript)

def process_entire_transcript(raw_transcript: str) -> FinalMeetingMinutes:
    chunks = chunk_transcript(raw_transcript)
    max_workers = int(os.getenv("MAX_CONCURRENT_REQUESTS", "2"))
    
    segment_results = [None] * len(chunks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_segment_reduction, chunk): i for i, chunk in enumerate(chunks)}
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                segment_results[idx] = future.result()
            except Exception as e:
                print(f"[INTERMEDIATE] Error processing segment {idx}: {e}")
                segment_results[idx] = "{\"error\": \"Failed to process segment\"}"

    merged_summaries = "\n\n".join([f"--- Segment {i+1} ---\n{res}" for i, res in enumerate(segment_results) if res])
    historical_context = "No previous context provided."
    
    try:
        print("[FINAL] Trying Gemini 3.5 Flash")
        gemini = get_gemini_llm()
        chain = final_prompt | gemini.with_structured_output(FinalMeetingMinutes)
        final_result = chain.invoke({"context": historical_context, "summaries": merged_summaries})
        print("[FINAL] Gemini succeeded")
        return final_result
    except Exception as e:
        print(f"[FINAL] Gemini failed: {e}")
        print("[FINAL] Starting Groq fallback")
        try:
            groq = get_groq_llm()
            chain = final_prompt | groq.with_structured_output(FinalMeetingMinutes)
            final_result = chain.invoke({"context": historical_context, "summaries": merged_summaries})
            print("[FINAL] Groq succeeded")
            return final_result
        except Exception as e2:
            print(f"[FINAL] Groq fallback failed: {e2}")
            raise RuntimeError("Both primary and fallback LLMs failed to generate final synthetic MoM")
