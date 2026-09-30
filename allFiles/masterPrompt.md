MASTER IMPLEMENTATION PROMPT
=============================

You are modifying my existing Automated Meeting Minutes Generator project.

IMPORTANT:
Do NOT rebuild the application from scratch.
First inspect the entire existing repository and understand the current frontend, backend, AssemblyAI transcription logic, LLM generation logic, and existing functionality.

Then implement the architecture below while preserving working functionality.

==================================================
1. PROJECT GOAL
==================================================

Turn the existing Automated Meeting Minutes Generator into a production-ready application capable of processing:

- short meetings
- 40–90+ minute meetings
- audio files
- existing text transcripts

The system must generate structured Meeting Minutes containing:

1. Summary
2. Key Points
3. Decisions
4. Action Items
5. Next Meeting Scheduled

The system must NOT send an entire long raw transcript directly to Groq.

The system must use:

PRIMARY FINAL MODEL:
Gemini 3.5 Flash

FALLBACK FINAL MODEL:
Groq

If Gemini fails for ANY reasonable API/runtime/output reason, automatically use Groq.

The user should not have to manually select the fallback.

==================================================
2. REQUIRED DEPLOYMENT ARCHITECTURE
==================================================

The application MUST be compatible with Vercel.

Use a serverless architecture.

Use Supabase PostgreSQL as the persistent database.

Use Supabase Storage if persistent audio storage is required.

DO NOT use:

- SQLite
- local JSON database
- local persistent filesystem
- long-running Flask/Django server processes
- in-memory database as the source of truth

The repository should become approximately:

automated-meeting-minutes/
│
├── api/
│   ├── transcribe.py
│   ├── generate_mom.py
│   ├── meetings.py
│   └── health.py
│
├── lib/
│   ├── assemblyai.py
│   ├── gemini.py
│   ├── groq.py
│   ├── llm_pipeline.py
│   ├── chunking.py
│   └── supabase.py
│
├── public/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── tests/
│   ├── test_chunking.py
│   ├── test_generator.py
│   └── test_fallback.py
│
├── supabase/
│   └── schema.sql
│
├── .env.example
├── .gitignore
├── requirements.txt
├── vercel.json
└── README.md

Adapt this structure to the existing project rather than blindly deleting existing files.

==================================================
3. EXISTING FRONTEND
==================================================

Preserve the existing frontend design and functionality as much as possible.

The frontend must allow the user to:

- upload audio
- provide a transcript directly
- start processing
- see processing status
- view generated Meeting Minutes
- see whether processing succeeded
- see the generated MoM

Do not unnecessarily redesign the UI.

==================================================
4. AUDIO PIPELINE
==================================================

For audio:

User
 ↓
Vercel API
 ↓
AssemblyAI
 ↓
Transcript
 ↓
Long-transcript processing
 ↓
Intermediate structured information
 ↓
Final MoM
 ↓
Supabase

For text:

User
 ↓
Vercel API
 ↓
Long-transcript processing
 ↓
Intermediate structured information
 ↓
Final MoM
 ↓
Supabase

==================================================
5. ASSEMBLYAI TRANSCRIPTION
==================================================

Use AssemblyAI as the transcription provider.

Whenever supported, enable speaker identification / speaker labels.

Preserve:

- speaker
- start timestamp
- end timestamp
- utterance text

Internally represent utterances approximately as:

{
    "speaker": "Speaker A",
    "start": 12000,
    "end": 15000,
    "text": "We should launch this next month."
}

Do NOT destroy speaker/timestamp information during preprocessing.

Read:

ASSEMBLYAI_API_KEY

from environment variables.

Never hardcode API keys.

==================================================
6. LONG TRANSCRIPT PROBLEM
==================================================

The current implementation uses simple character-based chunking.

Improve it.

Do NOT blindly split every N characters.

Prefer splitting at:

1. speaker utterance boundaries
2. paragraph boundaries
3. natural/topic boundaries when possible

Target approximately 10–15 minutes of meeting content per segment.

Exact segment size does not matter.

Semantic coherence matters more.

Example:

40-minute meeting

→ Segment 1
→ Segment 2
→ Segment 3
→ Segment 4

Do not cut an utterance in half.

==================================================
7. INTERMEDIATE PROCESSING
==================================================

Do NOT ask the intermediate model to create the final polished MoM.

The intermediate stage should extract compact structured information.

Each segment should produce:

{
    "key_points": [],
    "decisions": [],
    "action_items": [],
    "open_questions": [],
    "important_context": []
}

Rules:

- Never invent information.
- Never invent people.
- Never invent deadlines.
- Never invent decisions.
- Preserve explicit speaker names.
- Preserve explicit deadlines.
- Preserve action-item owners.
- Preserve unresolved questions.
- Keep output compact.
- Avoid unnecessary prose.

The purpose of this stage is REDUCTION.

Example:

RAW 15-MINUTE TRANSCRIPT
        ↓
SMALL STRUCTURED RESULT
        ↓
few hundred / few thousand tokens

This prevents the final model from receiving the entire raw meeting transcript.

==================================================
8. ASSEMBLYAI LLM CAPABILITIES
==================================================

Where practical, use AssemblyAI's available LLM/Gateway capabilities for intermediate transcript processing.

The conceptual flow should be:

AssemblyAI
 ↓
Transcript
 ↓
Intermediate long-transcript processing
 ↓
Structured segment results
 ↓
Final LLM

Do NOT assume that AssemblyAI must perform every LLM task.

If the required AssemblyAI LLM functionality is unavailable for the configured account/API, implement a clean fallback using the existing LLM infrastructure.

The application must remain functional.

==================================================
9. INTERMEDIATE REQUEST CONCURRENCY
==================================================

Do NOT launch unlimited parallel API requests.

The current problem involves token-per-minute/API rate limits.

Use bounded concurrency.

Default:

MAX_CONCURRENT_REQUESTS=2

Make this configurable through environment variables.

Implement:

- retry
- exponential backoff
- timeout
- rate-limit detection
- graceful failure

Do NOT use extremely high concurrency.

Do NOT create a request storm.

==================================================
10. FINAL MODEL
==================================================

The final MoM generation must use:

PRIMARY:
Gemini 3.5 Flash

Environment variable:

GEMINI_API_KEY

Do NOT hardcode the key.

The final Gemini request should receive:

- meeting metadata
- compact intermediate results
- relevant previous meeting context

It should NOT receive the complete raw 40–90 minute transcript unless absolutely necessary.

==================================================
11. GROQ FALLBACK
==================================================

Groq is the automatic fallback.

Environment variable:

GROQ_API_KEY

Flow:

Try Gemini
    ↓
Success?
 ┌──YES─────────────┐
 ↓                  │
Return result       │
                    │
NO                  │
 ↓                  │
Try Groq            │
 ↓                  │
Return result ───────┘

Gemini failure includes:

- HTTP/API failure
- timeout
- rate limit
- authentication failure
- malformed output
- invalid JSON
- schema validation failure
- empty response
- unexpected exception

If Gemini fails:

1. Log the failure internally.
2. Do NOT expose sensitive API details to the user.
3. Automatically call Groq.
4. Validate Groq output.
5. Return the Groq result.

Do NOT call Gemini and Groq simultaneously.

Do NOT call Groq if Gemini succeeds.

==================================================
12. FINAL MOM SCHEMA
==================================================

The final output MUST contain:

{
    "summary": "...",

    "key_points": [
        "..."
    ],

    "decisions": [
        {
            "decision": "...",
            "context": "..."
        }
    ],

    "action_items": [
        {
            "task": "...",
            "owner": null,
            "deadline": null
        }
    ],

    "next_meeting_scheduled": null
}

Rules:

If no decisions exist:

"decisions": []

If no action items exist:

"action_items": []

If no next meeting is mentioned:

"next_meeting_scheduled": null

Never invent missing information.

==================================================
13. FINAL SYNTHESIS PROMPT
==================================================

The final LLM must:

- combine information from all segments
- remove duplicate key points
- merge duplicate action items
- merge related decisions
- preserve important context
- preserve explicit owners
- preserve explicit deadlines
- identify the next meeting only if explicitly stated
- use previous meeting context only when relevant
- remain factual and neutral
- never hallucinate
- never invent names
- never invent dates
- never invent decisions

The final output must be valid JSON matching the schema.

==================================================
14. SUPABASE DATABASE
==================================================

Use Supabase PostgreSQL.

Create:

supabase/schema.sql

Use a meetings table approximately like:

CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    title TEXT,

    meeting_date TIMESTAMPTZ,

    participants JSONB,

    original_transcript TEXT,

    processed_transcript TEXT,

    summary TEXT,

    key_points JSONB,

    decisions JSONB,

    action_items JSONB,

    next_meeting_scheduled TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

Adapt the schema if the existing application already has database functionality.

Store every processed meeting.

==================================================
15. MEETING MEMORY
==================================================

The application must support historical meeting context.

When processing a new meeting:

Current Meeting
      ↓
Retrieve relevant previous meeting information
      ↓
Process current meeting
      ↓
Generate final MoM
      ↓
Store current meeting

Do NOT send every previous meeting to the LLM.

Only retrieve relevant previous context.

At minimum, retrieve:

- previous decisions
- previous action items
- relevant summaries
- previous meeting date

This allows future meetings to refer to earlier decisions/action items.

==================================================
16. SUPABASE SECURITY
==================================================

Environment variables:

SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY

The service-role key MUST remain server-side.

NEVER expose it in:

- HTML
- JavaScript
- frontend API responses
- public environment variables

Only server-side Vercel functions may use the service-role key.

==================================================
17. LONG-RUNNING JOB ARCHITECTURE
==================================================

Do NOT force a 40–90 minute meeting to remain inside one HTTP request.

Implement job-based processing.

Preferred architecture:

User uploads audio
        ↓
Create meeting/job record in Supabase
        ↓
Return job ID
        ↓
Process transcription + segmentation + LLM pipeline
        ↓
Update job status
        ↓
Store final MoM
        ↓
Frontend polls job status
        ↓
Display completed MoM

Statuses should include:

queued
transcribing
processing
generating
completed
failed

If the existing application can safely complete shorter requests synchronously, preserve that behavior where appropriate.

The important requirement is that long meetings must not depend on one huge browser request.

==================================================
18. SUPABASE MEETING STATUS
==================================================

If necessary, extend the database:

processing_status TEXT
error_message TEXT

Example:

queued
transcribing
processing
generating
completed
failed

Frontend should periodically check:

GET /api/meetings?id=<meeting_id>

and update the UI.

Do not make aggressive polling.

==================================================
19. API ENDPOINTS
==================================================

Implement clean serverless endpoints such as:

POST /api/transcribe

POST /api/generate_mom

GET /api/meetings

GET /api/meetings?id=<id>

GET /api/health

Adapt names to the existing project if necessary.

==================================================
20. VERCEL COMPATIBILITY
==================================================

Create/update:

vercel.json

Ensure the project works with Vercel's Python serverless functions.

Do not depend on:

- local persistent storage
- background daemon processes
- SQLite
- permanent local files
- processes that must remain alive forever

Use environment variables configured in Vercel.

==================================================
21. FILE STORAGE
==================================================

Do NOT permanently store uploaded audio on the Vercel filesystem.

If audio must be retained:

User
 ↓
Supabase Storage
 ↓
AssemblyAI

Otherwise process the audio and retain only the transcript/database information.

==================================================
22. LOGGING
==================================================

Add useful backend logs.

Example:

[TRANSCRIPTION] Starting AssemblyAI
[TRANSCRIPTION] Completed
[SEGMENTATION] Created 4 segments
[INTERMEDIATE] Processing segment 1/4
[INTERMEDIATE] Processing segment 2/4
[INTERMEDIATE] Processing segment 3/4
[INTERMEDIATE] Processing segment 4/4
[MERGE] Combining intermediate results
[FINAL] Trying Gemini 3.5 Flash
[FINAL] Gemini succeeded
[DATABASE] Meeting stored

Fallback:

[FINAL] Gemini failed
[FINAL] Starting Groq fallback
[FINAL] Groq succeeded
[DATABASE] Meeting stored

Do not log API keys.

==================================================
23. ENVIRONMENT VARIABLES
==================================================

Create/update:

.env.example

with:

ASSEMBLYAI_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=

SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

MAX_CONCURRENT_REQUESTS=2

Never commit .env.

.gitignore must include:

.env
__pycache__/
*.pyc
.vercel/

==================================================
24. REQUIREMENTS
==================================================

Update requirements.txt with only the packages actually required.

Remove unused dependencies where possible.

Do not add huge unnecessary frameworks.

==================================================
25. BACKWARD COMPATIBILITY
==================================================

Existing text transcript functionality MUST continue working.

Audio:

Audio
 ↓
AssemblyAI
 ↓
Transcript
 ↓
Pipeline

Text:

Text
 ↓
Pipeline

Do not break the current frontend.

==================================================
26. TESTING
==================================================

After implementation test:

TEST 1:
Short transcript.

Expected:
Successful final MoM.

TEST 2:
40-minute transcript.

Expected:

Transcript
 ↓
Multiple semantic segments
 ↓
Intermediate processing
 ↓
Gemini final MoM
 ↓
Supabase

TEST 3:
Force Gemini failure.

Expected:

Gemini
 ↓
Failure
 ↓
Groq
 ↓
Final MoM

TEST 4:
No decisions.

Expected:

"decisions": []

TEST 5:
No next meeting.

Expected:

"next_meeting_scheduled": null

TEST 6:
Duplicate action item across segments.

Expected:
Action item appears once in final MoM.

TEST 7:
Restart/reload frontend while processing.

Expected:
Frontend can retrieve job status from Supabase.

==================================================
27. DO NOT DO THESE THINGS
==================================================

DO NOT:

- train an LLM from scratch
- send the entire 90-minute transcript to Groq
- blindly send huge transcript chunks
- create unlimited parallel API requests
- call Gemini and Groq simultaneously
- call Groq when Gemini succeeds
- hardcode API keys
- store API keys in frontend code
- use SQLite
- use local persistent storage
- depend on a continuously running server
- break existing frontend functionality
- invent meeting information
- invent action-item owners
- invent deadlines
- invent decisions
- dump all historical meetings into every prompt
- create unnecessary microservices
- create unnecessary files

==================================================
28. IMPORTANT QUALITY REQUIREMENT
==================================================

This is NOT supposed to be a toy implementation.

Design the pipeline so a:

40-minute meeting
60-minute meeting
90-minute meeting

can be processed without sending the complete transcript to the final Groq request.

The architecture must reduce the transcript before final synthesis.

The final model receives structured information, not an enormous raw transcript.

==================================================
29. FINAL VALIDATION
==================================================

After making the changes:

1. Run the application.
2. Test backend endpoints.
3. Test frontend.
4. Test short transcript.
5. Test long transcript.
6. Test AssemblyAI transcription.
7. Test intermediate processing.
8. Test Gemini final generation.
9. Simulate Gemini failure.
10. Verify Groq fallback.
11. Verify Supabase insertion.
12. Verify meeting retrieval.
13. Verify job status updates.
14. Verify no secrets are exposed.
15. Fix errors found during testing.
16. Update README.md.
17. Update requirements.txt.

Do not merely tell me what should be implemented.

ACTUALLY MODIFY THE EXISTING PROJECT AND IMPLEMENT IT.

==================================================
30. FINAL RESPONSE FROM YOU
==================================================

When finished, report only a concise implementation summary:

IMPLEMENTED:
- Long-transcript segmentation
- Intermediate transcript reduction
- Gemini 3.5 Flash final generation
- Automatic Groq fallback
- Supabase persistence
- Vercel serverless architecture
- Job/status processing
- Previous-meeting context

FILES CHANGED:
- list files

TEST RESULTS:
- Short transcript: PASS/FAIL
- Long transcript: PASS/FAIL
- Gemini: PASS/FAIL
- Groq fallback: PASS/FAIL
- Supabase: PASS/FAIL
- Vercel compatibility: PASS/FAIL

If something could not be tested because credentials are unavailable, explicitly say so instead of claiming PASS.