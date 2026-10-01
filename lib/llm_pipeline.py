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

MAX_CHARS_PER_CHUNK = 8000 # Targeting tighter bounds
REDUCE_THRESHOLD = 4000 # More recursive steps to prevent Groq OSS overflow

def get_groq_llm():
    keys = os.getenv("GROQ_API_KEY", "").split(",")
    key = keys[0].strip() if keys else ""
    return init_chat_model("openai/gpt-oss-20b", model_provider="groq", groq_api_key=key)

def get_gemini_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model="gemini-3.5-flash")

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
    
    for attempt in range(3):
        try:
            response = chain.invoke({"transcript": transcript_segment})
            data = extract_json_content(response.content)
            result = SegmentReduction.model_validate(data)
            print(f"[MAP] Segment {idx} completed on try {attempt+1} (Groq)")
            return result.model_dump_json(indent=2)
        except Exception as e:
            print(f"[MAP] Segment {idx} (Groq) extraction failed (Try {attempt+1}/3): {e}")
            if attempt == 2:
                print(f"[MAP] Segment {idx} falling back to Gemini payload processing due to Groq outage.")
                try:
                    gemini = get_gemini_llm()
                    g_chain = segment_prompt | gemini
                    # Force wait before slamming Gemini fallback
                    time.sleep(5)
                    response_g = g_chain.invoke({"transcript": transcript_segment})
                    data_g = extract_json_content(response_g.content)
                    result_g = SegmentReduction.model_validate(data_g)
                    print(f"[MAP] Segment {idx} completed (Gemini Fallback)")
                    return result_g.model_dump_json(indent=2)
                except Exception as e2:
                    raise RuntimeError(f"Segment {idx} completely failed to map on both models: {e2}")
            print(f"[MAP] Throttling for {15*(attempt+1)} seconds to refresh API quotas...")
            time.sleep(15 * (attempt + 1))


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
    
    for attempt in range(3):
        try:
            response = chain.invoke({"summaries": merged_text})
            data = extract_json_content(response.content)
            result = SegmentReduction.model_validate(data)
            reduced = result.model_dump_json(indent=2)
            print(f"[REDUCE] Reduced context size (Try {attempt+1}): {len(reduced)} characters (Groq)")
            return reduced
        except Exception as e:
            print(f"[REDUCE] Extraction failed (Try {attempt+1}/3): {e}")
            if attempt == 2:
                print("[REDUCE] Falling back to Gemini to squash final context payload.")
                try:
                    gemini = get_gemini_llm()
                    g_chain = reduce_prompt | gemini
                    response_g = g_chain.invoke({"summaries": merged_text})
                    data_g = extract_json_content(response_g.content)
                    result_g = SegmentReduction.model_validate(data_g)
                    reduced_g = result_g.model_dump_json(indent=2)
                    print(f"[REDUCE] Reduced context size: {len(reduced_g)} characters (Gemini Fallback)")
                    return reduced_g
                except Exception as e2:
                    raise RuntimeError(f"REDUCE completely failed on both models: {e2}")
            time.sleep(3)

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
    
    # Run sequentially rather than in parallel to strictly avoid triggering Burst Rate limits on free tier accounts
    for i, chunk in enumerate(chunks):
        idx = i + 1
        try:
            # Introduce baseline buffer between segments to avoid fast-fire limits
            if idx > 1:
                time.sleep(5)
            segment_results[i] = run_segment_reduction(chunk, idx)
        except Exception as e:
            print(f"[INTERMEDIATE] Fatal error processing segment {idx}: {e}")
            raise RuntimeError(str(e))
                
    valid_results = [res for res in segment_results if res]
    if not valid_results:
        raise ValueError("No valid structured segments were extracted from the transcript.")
    
    # Hierarchical Reduce
    reduced_context = recursive_reduce(valid_results)
    
    # Final Generation
    return execute_final_synthesis(reduced_context)

# ---------------------------------------------------------
# NATIVE JUPYTER NOTEBOOK IMPLEMENTATION FOR TEXT UPLOADS
# ---------------------------------------------------------
class NotebookActionItem(BaseModel):
    task: str = Field(description="The action to be done")
    owner: Optional[str] = Field(default=None, description="Person or team responsible, if stated in the transcript")
    deadline: Optional[str] = Field(default=None, description="Due date or timeframe, if stated in the transcript")

class NotebookDecision(BaseModel):
    decision: str = Field(description="A decision that was made")
    context: Optional[str] = Field(default=None, description="Brief context or reasoning behind the decision, if given")

class NotebookMeetingMinutes(BaseModel):
    title: str = Field(description="A short descriptive title for the meeting")
    attendees: List[str] = Field(default_factory=list, description="Names mentioned as present, if identifiable from the transcript")
    summary: str = Field(description="A concise 3-5 sentence summary of the meeting")
    key_topics: List[str] = Field(description="Main topics discussed, as short bullet points")
    decisions: List[NotebookDecision] = Field(default_factory=list, description="Decisions made during the meeting")
    action_items: List[NotebookActionItem] = Field(default_factory=list, description="Concrete follow-up tasks")
    open_questions: List[str] = Field(default_factory=list, description="Unresolved questions or items to follow up on")

def _generate_once(transcript: str) -> NotebookMeetingMinutes:
    llm = get_gemini_llm()
    system_prompt = """
    You are an assistant that writes accurate, concise meeting minutes from a transcript.
    
    Rules:
    - Use only information present in the transcript. Do not invent names, dates, or decisions.
    - If attendees are not identifiable, return an empty list rather than guessing.
    - Action items should be concrete and actionable. Include owner and deadline only if explicitly stated or clearly implied; otherwise leave them empty.
    - Keep the summary factual and neutral in tone.
    - List key topics as short phrases, not full sentences.
    - Separate decisions (things agreed/resolved) from action items (things to be done).
    - If nothing fits a field (e.g. no open questions), return an empty list for it.
    """
    human_prompt =  """
    Meeting transcript:
    {transcript}
    
    Generate the meeting minutes.
    """
    prompt = ChatPromptTemplate.from_messages([
        ( "system",system_prompt,),
        ( "human",human_prompt,),
    ])
    
    structured_llm = llm.with_structured_output(NotebookMeetingMinutes)
    chain = prompt | structured_llm
    
    last_error = None
    for attempt in range(1, 4):
        try:
            result = chain.invoke({"transcript": transcript})
            if isinstance(result, dict):
                result = NotebookMeetingMinutes.model_validate(result)
            return result
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt} failed: {e}")
            time.sleep(3)

    raise RuntimeError(f"Minutes generation failed after 3 attempts: {last_error}")


def process_single_shot_text(transcript: str) -> dict:
    """Invokes the native Jupyter Notebook map-reduce chunking specifically mapped to Gemini for text generation."""
    if not transcript.strip():
        raise ValueError("Transcript is empty.")

    chunks = chunk_transcript(transcript, max_chars=12000)

    if len(chunks) == 1:
        return _generate_once(chunks[0]).model_dump()

    print(f"Transcript split into {len(chunks)} chunks; summarizing each...")
    partials = []
    for c in chunks:
        partials.append(_generate_once(c))
        time.sleep(3) # API safeguard

    merged_text = "\n\n".join(
        f"Partial summary {i+1}:\n{p.model_dump_json(indent=2)}"
        for i, p in enumerate(partials)
    )

    return _generate_once(merged_text).model_dump()

