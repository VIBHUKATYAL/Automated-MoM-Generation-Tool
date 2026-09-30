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
    ("system", "You are an expert transcriber. Reduce this transcript segment into compact structured information without losing details. Never invent information.\n\nReturn ONLY valid JSON matching this schema:\n{{\n  \"key_points\": [\"...\"],\n  \"decisions\": [\"...\"],\n  \"action_items\": [\"...\"],\n  \"open_questions\": [\"...\"],\n  \"important_context\": [\"...\"]\n}}\n\nDo not use Markdown. Do not wrap the JSON in ```json. Do not add explanations before or after the JSON."),
    ("human", "{transcript}")
])

# Prompt for merging/reducing structured contexts
reduce_prompt = ChatPromptTemplate.from_messages([
    ("system", "Merge these multiple structured meeting segments into one compacted structured summary. Remove exact duplicates, merge related items, preserve specific deadlines and owners, discard conversational fluff. Never invent information.\n\nReturn ONLY valid JSON matching this schema:\n{{\n  \"key_points\": [\"...\"],\n  \"decisions\": [\"...\"],\n  \"action_items\": [\"...\"],\n  \"open_questions\": [\"...\"],\n  \"important_context\": [\"...\"]\n}}\n\nDo not use Markdown. Do not wrap the JSON in ```json. Do not add explanations before or after the JSON."),
    ("human", "{summaries}")
])

# Prompt for final synthesis
final_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an executive assistant. Convert this structured reduced context into a final cohesive Minutes of Meeting document. KEEP ALL actionable tasks and decisions. Never invent information.\n\nReturn ONLY valid JSON matching this schema:\n{{\n  \"summary\": \"...\",\n  \"key_points\": [\"...\"],\n  \"decisions\": [\n    {{\"decision\": \"...\", \"context\": \"...\"}}\n  ],\n  \"action_items\": [\n    {{\"task\": \"...\", \"owner\": \"...\", \"deadline\": \"...\"}}\n  ],\n  \"next_meeting_scheduled\": \"... or null\"\n}}\n\nDo not use Markdown. Do not wrap the JSON in ```json. Do not add explanations before or after the JSON."),
    ("human", "Historical Meeting Context:\n{context}\n\nReduced Context:\n{reduced_context}")
])

final_retry_prompt = ChatPromptTemplate.from_messages([
    ("system", "Your previous response was not valid JSON. Return ONLY valid JSON matching this schema:\n{{\n  \"summary\": \"...\",\n  \"key_points\": [\"...\"],\n  \"decisions\": [\n    {{\"decision\": \"...\", \"context\": \"...\"}}\n  ],\n  \"action_items\": [\n    {{\"task\": \"...\", \"owner\": \"...\", \"deadline\": \"...\"}}\n  ],\n  \"next_meeting_scheduled\": \"... or null\"\n}}\n\nDo not use Markdown. Do not wrap the JSON in ```json. Do not add explanations before or after the JSON."),
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

def extract_json_content(content) -> dict:
    if isinstance(content, list):
        # Some SDK versions return list of content blocks
        content = " ".join([str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in content])
        
    raw = str(content).strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    return json.loads(raw)

def run_segment_reduction(transcript_segment: str, idx: int) -> str:
    print(f"[MAP] Starting segment {idx}")
    llm = get_groq_llm()
    chain = segment_prompt | llm
    response = chain.invoke({"transcript": transcript_segment})
    
    try:
        data = extract_json_content(response.content)
        result = SegmentReduction.model_validate(data)
        print(f"[MAP] Segment {idx} completed")
        return result.model_dump_json(indent=2)
    except Exception as e:
        print(f"[MAP] Segment {idx} extraction failed: {e}")
        # Return fallback empty state so reduction survives
        return SegmentReduction().model_dump_json(indent=2)

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
    chain = reduce_prompt | llm
    response = chain.invoke({"summaries": merged_text})
    
    try:
        data = extract_json_content(response.content)
        result = SegmentReduction.model_validate(data)
        reduced = result.model_dump_json(indent=2)
    except Exception as e:
        print(f"[REDUCE] Extraction failed: {e}")
        reduced = SegmentReduction().model_dump_json(indent=2)
    
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

def validate_final_json(data: dict) -> bool:
    try:
        m = FinalMeetingMinutes.model_validate(data)
        if not m.summary:
            return False
        return True
    except Exception:
        return False

def execute_final_synthesis(reduced_context: str) -> FinalMeetingMinutes:
    historical_context = "No previous context provided."
    print(f"[FINAL] Context characters: {len(reduced_context)}")
    print(f"[FINAL] Estimated tokens: ~{len(reduced_context) // 4}")
    
    # Primary: Gemini
    gemini = get_gemini_llm()
    chain = final_prompt | gemini
    retry_chain = final_retry_prompt | gemini
    
    print("[FINAL] Gemini request started")
    for attempt in range(2):
        try:
            if attempt == 0:
                response = chain.invoke({"context": historical_context, "reduced_context": reduced_context})
            else:
                print("[FINAL] Gemini retry 1/1")
                response = retry_chain.invoke({"context": historical_context, "reduced_context": reduced_context})
                
            print(f"[FINAL] Gemini raw response received (Attempt {attempt+1})")
            data = extract_json_content(response.content)
            
            if validate_final_json(data):
                print("[FINAL] Gemini JSON validation: PASS")
                return FinalMeetingMinutes.model_validate(data)
            else:
                print("[FINAL] Gemini JSON validation: FAIL")
        except Exception as e:
            print(f"[FINAL] Gemini failed: {e}")
        
    print("[FINAL] Starting Groq fallback")
    groq = get_groq_llm()
    g_chain = final_prompt | groq
    g_retry = final_retry_prompt | groq
    
    for attempt in range(2):
        try:
            if attempt == 0:
                response = g_chain.invoke({"context": historical_context, "reduced_context": reduced_context})
            else:
                response = g_retry.invoke({"context": historical_context, "reduced_context": reduced_context})
                
            print(f"[FINAL] Groq raw response received (Attempt {attempt+1})")
            data = extract_json_content(response.content)
            
            if validate_final_json(data):
                print("[FINAL] Groq JSON validation: PASS")
                return FinalMeetingMinutes.model_validate(data)
            else:
                print("[FINAL] Groq JSON validation: FAIL")
        except Exception as e2:
            print(f"[FINAL] Groq fallback failed: {e2}")

    raise RuntimeError("Both primary and fallback LLMs failed to generate valid JSON MoM")

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
