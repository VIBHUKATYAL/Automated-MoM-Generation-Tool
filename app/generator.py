import os
import concurrent.futures
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# The application is configured solely for Gemini.
PROVIDER = "gemini"
TEMPERATURE = 0.2
MAX_RETRIES = 3

MODELS = {
    "gemini": "gemini-3.5-flash",
    "groq": "openai/gpt-oss-20b",
}

PROVIDER_INFO = {
    "gemini": ("google_genai", "GOOGLE_API_KEY"),
    "groq": ("groq", "GROQ_API_KEY"),
}

class ActionItem(BaseModel):
    task: str = Field(description="The action to be done")
    owner: Optional[str] = Field(default=None, description="Person or team responsible")
    deadline: Optional[str] = Field(default=None, description="Due date or timeframe")


class Decision(BaseModel):
    decision: str = Field(description="A decision that was made")
    context: Optional[str] = Field(default=None, description="Brief context or reasoning")


class MeetingMinutes(BaseModel):
    title: str = Field(description="A short descriptive title for the meeting")
    attendees: List[str] = Field(default_factory=list, description="Names mentioned as present")
    summary: str = Field(description="A concise 3-5 sentence summary of the meeting")
    key_topics: List[str] = Field(description="Main topics discussed, as short bullet points")
    decisions: List[Decision] = Field(default_factory=list, description="Decisions made during the meeting")
    action_items: List[ActionItem] = Field(default_factory=list, description="Concrete follow-up tasks")
    open_questions: List[str] = Field(default_factory=list, description="Unresolved questions")

GROQ_KEYS = []
GROQ_KEY_INDEX = 0

def get_next_groq_key():
    global GROQ_KEYS, GROQ_KEY_INDEX
    if not GROQ_KEYS:
        keys_env = os.getenv("GROQ_API_KEY", "")
        GROQ_KEYS = [k.strip() for k in keys_env.split(",") if k.strip()]
        if not GROQ_KEYS:
            raise ValueError("GROQ_API_KEY not found or empty.")
    
    key = GROQ_KEYS[GROQ_KEY_INDEX % len(GROQ_KEYS)]
    GROQ_KEY_INDEX += 1
    return key


def build_llm(provider: str = PROVIDER):
    if provider not in PROVIDER_INFO:
        raise ValueError(f"Unknown provider '{provider}'")
    model_provider, env_var = PROVIDER_INFO[provider]
    model_name = MODELS[provider]
    kwargs = {"temperature": TEMPERATURE, "max_retries": 0}
    
    if provider == "groq":
        kwargs["api_key"] = get_next_groq_key()
        
    return init_chat_model(model=model_name, model_provider=model_provider, **kwargs)


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

MAX_CHARS_PER_CHUNK = 6000

def chunk_transcript(transcript: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    if len(transcript) <= max_chars:
        return [transcript]
    lines = transcript.splitlines(keepends=True)
    chunks, current = [], ""
    for line in lines:
        if len(current) + len(line) > max_chars and current:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)
    return chunks

def _generate_once(chain, transcript: str) -> MeetingMinutes:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = chain.invoke({"transcript": transcript})
            if isinstance(result, dict):
                result = MeetingMinutes.model_validate(result)
            return result
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt} failed: {e}")
    raise RuntimeError(f"Minutes generation failed after {MAX_RETRIES} attempts: {last_error}")

def generate_minutes_stream(transcript: str, provider: str = PROVIDER):
    """
    Yields dicts representing the progress of generating minutes.
    Can be used for Server-Sent Events (SSE).
    """
    if not transcript.strip():
        raise ValueError("Transcript is empty.")
    
    chunks = chunk_transcript(transcript)
    yield {"status": "started", "chunks": len(chunks)}
    
    def process_chunk(idx, c):
        llm = build_llm(provider)
        chain = prompt | llm.with_structured_output(MeetingMinutes)
        return idx, _generate_once(chain, c)
        
    partials = [None] * len(chunks)
    completed = 0
    
    if len(chunks) == 1:
        # Avoid threads if only 1 chunk
        idx, result = process_chunk(0, chunks[0])
        partials[0] = result
        yield {"status": "progress", "completed": 1, "total": 1, "partial": result.model_dump()}
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(chunks), 3)) as executor:
            futures = {executor.submit(process_chunk, i, c): i for i, c in enumerate(chunks)}
            for future in concurrent.futures.as_completed(futures):
                i = futures[future]
                idx, result = future.result()
                partials[idx] = result
                completed += 1
                yield {"status": "progress", "completed": completed, "total": len(chunks), "partial": result.model_dump()}
    
    yield {"status": "merging"}
    
    if len(chunks) == 1:
        final_result = partials[0]
    else:
        merged_text = "\n\n".join(
            f"Partial summary {i+1}:\n{p.model_dump_json(indent=2)}"
            for i, p in enumerate(partials)
        )
        llm_final = build_llm(provider)
        chain_final = prompt | llm_final.with_structured_output(MeetingMinutes)
        final_result = _generate_once(chain_final, merged_text)
        
    yield {"status": "completed", "result": final_result.model_dump()}

refine_system_prompt = """
You are an expert editor who cleans up raw audio transcripts.
The transcript contains speaker labels (e.g. Speaker A, Speaker B).
Your job is to:
- Fix obvious typos, transcription errors, stutters, and grammatical mistakes based on context.
- Keep the exact meaning and flow of the conversation.
- Retain the speaker labels (Speaker A: ...) exactly as they are.
- Output ONLY the clean transcript text, without any additional comments or introductory text.

CRITICAL INSTRUCTION:
DO NOT SUMMARIZE. You MUST process and return every single line of the conversation. The output length should be nearly identical to the input length. If you condense or skip any part of the transcript, you will break the pipeline.
"""

refine_human_prompt = """
Raw transcript:
{raw_transcript}

Refined clean transcript:
"""

refine_prompt = ChatPromptTemplate.from_messages([
    ("system", refine_system_prompt),
    ("human", refine_human_prompt),
])

def refine_transcript_stream(raw_transcript: str, provider: str = PROVIDER):
    """
    Cleans up the raw transcript using an LLM in chunks sequentially or parallelly,
    yielding progress.
    """
    if not raw_transcript.strip():
        yield {"status": "error", "message": "Transcript is empty"}
        return
        
    chunks = chunk_transcript(raw_transcript)
    refined_chunks = [None] * len(chunks)
    
    def process_refine(idx, c):
        llm = build_llm(provider)
        chain = refine_prompt | llm
        return idx, chain.invoke({"raw_transcript": c}).content.strip()

    completed = 0
    yield {"status": "refining_started", "chunks": len(chunks)}
    
    if len(chunks) == 1:
        idx, result = process_refine(0, chunks[0])
        refined_chunks[0] = result
        yield {"status": "refining_progress", "completed": 1, "total": 1, "text": result}
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(chunks), 3)) as executor:
            futures = {executor.submit(process_refine, i, c): i for i, c in enumerate(chunks)}
            for future in concurrent.futures.as_completed(futures):
                i = futures[future]
                idx, result = future.result()
                refined_chunks[idx] = result
                completed += 1
                yield {"status": "refining_progress", "completed": completed, "total": len(chunks), "text": result}
    
    yield {"status": "refining_completed", "result": "\n".join(refined_chunks)}
