# Role & Objective
You are an Elite Data Scientist and a Senior AI Software Engineer executing an end-to-end benchmarking experiment. Your mission is to measure the financial and accuracy trade-offs between three distinct LLM chat history management strategies under specific prompt caching regimes. 

You will write the necessary code, build an automated evaluation runner, validate your work locally, run the entire test matrix across values of n (n=10, n=100, n=1000) using `gpt-4o` and `claude-3-5-haiku`, log everything with pristine tracing metrics, and prepare the data for analysis.

Execute this assignment sequentially using autonomous loops (`/loop`) without manual intervention, maintaining rigorous code quality and architectural discipline.

---

## Technical Constraints & Specifications

### 1. SDK Implementations (No Gateways)
*   **OpenAI SDK:** Use the native python `openai` library. OpenAI handles prompt caching automatically on prefixes >= 1,024 tokens. You MUST include the `prompt_cache_key` and `prompt_cache_retention: "24h"` parameters to stabilize routing and maximize retention between test rounds.
*   **Anthropic SDK:** Use the native python `anthropic` library. Anthropic prompt caching is explicit. You MUST dynamically compute the token size of your static context block, select appropriate boundaries, and manually attach the `"type": "ephemeral"` cache control block to up to 4 breakpoints (e.g., the system prompt, or the end of a stable history block).

### 2. Chat History Management Strategies
You will construct a unified history management class (or modules) implementing three specific pruning configurations:

*   **Strategy A: Pristine Cache / Append-Only (Baseline)**
    *   No history pruning occurs during the conversation turn phase. Every single turn is appended to the bottom. This strategy is designed to yield a high cache hit rate but will result in linearly growing context sizes.
*   **Strategy B: Naive Pruning (Front Slashing)**
    *   Takes an integer parameter `n`. The array stores up to a maximum of `n` messages. When message `n+1` arrives, the earliest message (at index 0 of the conversation text window, right after the system prompt) is instantly dropped. This guarantees a bounded context window but purposefully breaks prefix matching for prompt caching.
*   **Strategy C: Summarization Pruning (Compaction)**
    *   Takes an integer parameter `n`. The history is allowed to grow normally. However, the moment the history length hits `n` messages, a separate background LLM compilation call is made to a fast model (e.g., Haiku) with a specialized system prompt: *"Summarize the core facts, answers, and context established in the following conversation history into a dense, highly structured bulleted summary. Preserve all unique identifiers, user opinions, and specific question answers."*
    *   The raw historical text block of those `n` messages is deleted, and the resulting dense summary string is injected as a single system message or static user message right below the main system prompt. This creates a new stable cache baseline block before tracking subsequent messages.

---

## The Benchmark Experiment Design

You will build an automated user-simulation script that walks each configuration through three steps:

1.  **Phase 1: Setup & Instruction Ingestion**
    *   The script sends a giant setup prompt to the LLM containing a static block of **100 diverse natural-language questions**. 
    *   The prompt tells the LLM: *"You are an interviewer. Read this list of 100 questions. Your task is to ask me these questions one by one, sequentially. Wait for my answer before asking the next question. Do not skip ahead or ask multiple questions at once."*
    *   *Note:* Ensure this initial setup prompt, combined with system instructions, is comfortably over 1,024 tokens to guarantee cache eligibility from turn one.
2.  **Phase 2: Sequential Interview Simulation**
    *   The script acts as the user. It has access to a pre-defined mock data dictionary containing natural-language answers to all 100 questions.
    *   The model asks Question 1 -> The script responds with Answer 1 -> The model asks Question 2 -> The script responds with Answer 2, continuing for all 100 turns.
    *   The history management strategy (A, B, or C) must process the conversation array at *every single turn*.
3.  **Phase 3: The Memory & Accuracy Examination**
    *   After Question 100 is answered, the script sends the definitive evaluation challenge.
    *   It re-presents the questionnaire as a strict **Multiple-Choice Quiz** focused heavily on the questions from the *beginning* and *middle* of the test sequence (e.g., Questions 5, 25, 50, 75).
    *   The model must choose between options (a, b, c, or none of the above), where only one choice matches the user's original answer.
    *   The model MUST respond in a strict JSON format: `{"question_id": X, "selected_option": "a", "reasoning": "..."}`.

---

## Execution Framework (Phased Plan)

Execute the task following these strict developmental phases. Do not proceed to the next phase until the current phase is fully written, executed, and verified.

### Phase 1: Core Architecture & Logging Setup
1.  Create a clean project directory.
2.  Write the logging and tracing framework. Every API interaction must log to a local SQLite database or structured JSONL file. You MUST extract and log:
    *   Timestamp, Model Name, Strategy Name, and current Value of `n`.
    *   `input_tokens` (uncached/fresh processing).
    *   `cached_tokens` (cache hits from OpenAI `prompt_tokens_details` or Anthropic `cache_read_input_tokens`).
    *   `output_tokens` (completion tokens generated).
    *   Calculated financial cost of the transaction based on actual 2026 price listings for cached vs uncached tokens.
    *   The complete payload sent and received.

### Phase 2: Implementation of History Managers & Mock Data
1.  Implement the three chat history pruning strategies inside a clean module.
2.  Generate a static asset containing 100 distinct questions along with realistic, varied natural-language answers.
3.  Write the evaluation multiple-choice questionnaire matching those 100 answers.

### Phase 3: Unit Testing & Integrity Validation
1.  Write a miniature integration test script (e.g., running 3 questions with `n=2`) to verify that:
    *   Strategy B cleanly drops old messages.
    *   Strategy C correctly calls the compaction LLM sub-routine and replaces historical blocks with a summary.
    *   The Anthropic `cache_control` blocks and OpenAI `prompt_cache_key` parameters are accurately mapped in the payload.
2.  Run these tests and check your log files to guarantee that token parsing and tracking behave perfectly.

### Phase 4: Automated Benchmark Execution
Run the full testing matrix using a runner loop. 
*   **Models to test:** `gpt-4o`, `claude-3-5-haiku`
*   **Strategies to test:** Strategy A (Baseline), Strategy B (Naive), Strategy C (Compacted)
*   **Variables of n to test:** `n = 10`, `n = 100`, `n = 1000`
*   Use your automated loop capabilities (`/loop`) to execute these paths sequentially. Wrap API calls in robust try/except blocks to gracefully handle rate-limiting, back-offs, or network drops.

### Phase 5: Final Report & Dataset Synthesis
1.  When the benchmark runs wrap up, write a script to query your database/logs and aggregate the results into a markdown-compatible summary table.
2.  Group the final data by Model, Strategy, and Variable `n` to display:
    *   **Total Cumulative Cost ($)**
    *   **Total Cache Hit Ratio (%)** (Total Cached Tokens / Total Input Tokens)
    *   **Final Retrieval Accuracy (%)** (Parsed from the final JSON multiple-choice answers)
3.  Output a concise paragraph summarizing which configuration provides the optimal financial efficiency-to-accuracy balance.

Begin with **Phase 1**. Do not ask me for permission between phases—use your subagents and loop command to execute this end-to-end.