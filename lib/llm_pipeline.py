import os
import concurrent.futures
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
import time

class SegmentReduction(BaseModel):
    key_points: List[str] = Field(default_factory=list, description="Key points discussed in this segment")
    decisions: List[str] = Field(default_factory=list, description="Decisions made in this segment")
    action_items: List[str] = Field(default_factory=list, description="Tasks assigned in this segment, with owners and deadlines")
    open_questions: List[str] = Field(default_factory=list, description="Unresolved questions")
    important_context: List[str] = Field(default_factory=list, description="Crucial background information presented")

class FinalMeetingMinutes(BaseModel):
    summary: str = Field(..., description="High level summary of the entire meeting")
    key_points: List[str] = Field(default_factory=list, description="Combined key points")
    decisions: List[dict] = Field(default_factory=list, description="List of decisions with keys 'decision' and 'context'")
    action_items: List[dict] = Field(default_factory=list, description="List of tasks with keys 'task', 'owner', and 'deadline'")
    next_meeting_scheduled: Optional[str] = Field(None, description="When the next meeting is scheduled, or null if none mentioned")

# Prompt for intermediate segments (reduction/map)
segment_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert transcriber. Reduce this transcript segment into compact structured information without losing details. Never invent information."),
    ("human", "{transcript}")
])

# Prompt for merging/reducing structured contexts
reduce_prompt = ChatPromptTemplate.from_messages([
    ("system", "Merge these multiple structured meeting segments into one compacted structured summary. Remove exact duplicates, merge related items (key points, action items, decisions), preserve specific deadlines and owners, discard conversational fluff. Never invent information."),
    ("human", "{summaries}")
])

# Prompt for final synthesis
final_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an executive assistant. Convert this structured reduced context into a final cohesive Minutes of Meeting document. KEEP ALL actionable tasks and decisions. Never invent information."),
    ("human", "Historical Meeting Context:\n{context}\n\nReduced Context:\n{reduced_context}")
])

MAX_CHARS_PER_CHUNK = 12000 # Targeting 10-15 mins of speech
REDUCE_THRESHOLD = 8000 # If combined json strings exceed 8k chars, trigger another reduce round

def get_groq_llm():
    keys = os.getenv("GROQ_API_KEY", "").split(",")
    key = keys[0].strip() if keys else ""
    return init_chat_model("openai/gpt-oss-20b", model_provider="groq", groq_api_key=key)

def get_gemini_llm():
    return init_chat_model("gemini-3.5-flash", model_provider="google_genai")

def run_segment_reduction(transcript_segment: str, idx: int) -> str:
    print(f"[MAP] Starting segment {idx}")
    llm = get_groq_llm()
    chain = segment_prompt | llm.with_structured_output(SegmentReduction)
    result = chain.invoke({"transcript": transcript_segment})
    print(f"[MAP] Segment {idx} completed")
    return result.model_dump_json(indent=2)

def chunk_transcript(transcript: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chars,
        chunk_overlap=400,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_text(transcript)

def reduce_structures(json_structures: List[str]) -> str:
    merged_text = "\n\n".join([f"--- Block {i+1} ---\n{res}" for i, res in enumerate(json_structures)])
    print(f"[REDUCE] Raw intermediate size: {len(merged_text)} characters")
    
    llm = get_groq_llm()
    chain = reduce_prompt | llm.with_structured_output(SegmentReduction)
    result = chain.invoke({"summaries": merged_text})
    reduced = result.model_dump_json(indent=2)
    
    print(f"[REDUCE] Reduced context size: {len(reduced)} characters")
    return reduced

def recursive_reduce(json_structures: List[str]) -> str:
    if not json_structures:
        return ""
    if len(json_structures) == 1:
        return json_structures[0]
        
    total_len = sum(len(s) for s in json_structures)
    if total_len < REDUCE_THRESHOLD:
        print("[REDUCE] Combined size is small enough, performing single reduction.")
        return reduce_structures(json_structures)
        
    print(f"[REDUCE] Combined size {total_len} exceeds threshold {REDUCE_THRESHOLD}. Performing hierarchical second reduction.")
    
    mid = len(json_structures) // 2
    left_reduced = recursive_reduce(json_structures[:mid])
    right_reduced = recursive_reduce(json_structures[mid:])
    
    return reduce_structures([left_reduced, right_reduced])

def validate_final_json(model_result) -> bool:
    try:
        data = model_result.model_dump()
        if not data.get("summary"):
            return False
        if not isinstance(data.get("action_items"), list):
            return False
        return True
    except Exception:
        return False

def execute_final_synthesis(reduced_context: str) -> FinalMeetingMinutes:
    historical_context = "No previous context provided."
    print(f"[FINAL] Context characters: {len(reduced_context)}")
    print(f"[FINAL] Estimated tokens: ~{len(reduced_context) // 4}")
    
    # Try Gemini Primary with Retry
    for attempt in range(2):
        print(f"[FINAL] Gemini request started (Attempt {attempt+1}/2)")
        try:
            gemini = get_gemini_llm()
            chain = final_prompt | gemini.with_structured_output(FinalMeetingMinutes)
            final_result = chain.invoke({"context": historical_context, "reduced_context": reduced_context})
            
            if validate_final_json(final_result):
                print("[FINAL] Gemini JSON validation: PASS")
                return final_result
            else:
                print(f"[FINAL] Gemini JSON validation: FAIL (Attempt {attempt+1})")
        except Exception as e:
            print(f"[FINAL] Gemini status failed: {e}")
        
        time.sleep(2)
        
    print("[FINAL] Gemini completely failed. Falling back to Groq")
    try:
        groq = get_groq_llm()
        chain = final_prompt | groq.with_structured_output(FinalMeetingMinutes)
        final_result = chain.invoke({"context": historical_context, "reduced_context": reduced_context})
        
        if validate_final_json(final_result):
            print("[FINAL] Groq JSON validation: PASS")
            return final_result
        else:
            print("[FINAL] Groq JSON validation: FAIL")
            raise ValueError("Groq JSON schema invalid")
    except Exception as e2:
        print(f"[FINAL] Groq fallback failed: {e2}")
        raise RuntimeError("Both primary and fallback LLMs failed to generate final synthetic MoM")

def process_entire_transcript(raw_transcript: str) -> FinalMeetingMinutes:
    chunks = chunk_transcript(raw_transcript)
    print(f"[MAP] Segment count: {len(chunks)}")
    
    max_workers = int(os.getenv("MAX_CONCURRENT_REQUESTS", "2"))
    segment_results = [None] * len(chunks)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_segment_reduction, chunk, i+1): i for i, chunk in enumerate(chunks)}
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                segment_results[idx] = future.result()
            except Exception as e:
                print(f"[INTERMEDIATE] Error processing segment {idx+1}: {e}")
                segment_results[idx] = '{"error": "Failed to map segment"}'
                
    valid_results = [res for res in segment_results if res]
    
    # Hierarchical Reduce
    reduced_context = recursive_reduce(valid_results)
    
    # Final Generation
    return execute_final_synthesis(reduced_context)
