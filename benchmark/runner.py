"""Run one benchmark config end-to-end.

A config is (provider, model, strategy, n). The runner walks the three phases:
  1. Setup       -- the giant static system prompt (100 questions + instructions).
  2. Interview   -- `num_turns` sequential turns; the model asks Qk, we answer with
                    the scripted answer for question k. The history strategy processes
                    the conversation at every turn.
  3. MCQ exam    -- each quiz item is asked in-conversation; the model answers from
                    whatever context the strategy has retained. Answers are graded
                    against the known-correct option.

Every API call is logged. `logger.check_cap()` runs before each paid call, so a run
aborts immediately (via CostCapExceeded) the moment cumulative spend crosses the cap.
"""
from __future__ import annotations

import json
import re
import uuid

from .clients import call_anthropic, call_openai
from .data import QUIZ, answers_by_id, build_interviewer_system_prompt
from .history import COMPACTION_SYSTEM_PROMPT, make_strategy, normalize

KICKOFF = "I am ready to begin. Please ask me question 1."
TURN_MAX_TOKENS = 200       # the interviewer only asks one short question per turn
QUIZ_MAX_TOKENS = 400       # JSON object + one short reasoning sentence
COMPACTOR_MODEL = "claude-haiku-4-5"
COMPACTOR_MAX_TOKENS = 1500


def _make_compactor(anthropic_client, logger, *, run_id, bench_model, strategy_name, n):
    """Strategy C's summarization sub-routine: a logged, cost-counted Haiku call."""

    def compactor(text: str) -> str:
        logger.check_cap()
        res = call_anthropic(
            anthropic_client,
            model=COMPACTOR_MODEL,
            system=COMPACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
            max_tokens=COMPACTOR_MAX_TOKENS,
            cache=False,
        )
        logger.log(
            run_id=run_id, bench_model=bench_model, provider="anthropic",
            model=COMPACTOR_MODEL, strategy=strategy_name, n=n, phase="compaction",
            turn_index=None, usage=res.usage, request=res.request, response=res.response,
        )
        return res.text

    return compactor


def _quiz_prompt(item: dict) -> str:
    o = item["options"]
    return (
        "Memory check. Based strictly on the answers I gave earlier in this interview, "
        "answer the following multiple-choice question. Respond with ONLY a JSON object of "
        'the form {"question_id": <int>, "selected_option": "<a|b|c|d>", '
        '"reasoning": "<one short sentence>"}.\n\n'
        f"(This concerns my answer to interview question {item['question_id']}.)\n"
        f"{item['prompt']}\n"
        f"a) {o['a']}\n"
        f"b) {o['b']}\n"
        f"c) {o['c']}\n"
        f"d) {o['d']}"
    )


def _parse_quiz(text: str) -> tuple[str, dict]:
    """Extract the selected option letter from a model's quiz response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            sel = str(obj.get("selected_option", "")).strip().lower()[:1]
            return sel, obj
        except Exception:
            pass
    fallback = re.search(r"\b([abcd])\b", text.lower())
    return (fallback.group(1) if fallback else ""), {"raw": text}


def run_config(
    *,
    provider: str,
    model: str,
    strategy_name: str,
    n: int | None,
    logger,
    openai_client=None,
    anthropic_client=None,
    num_turns: int = 100,
    quiz: list[dict] = QUIZ,
    verbose: bool = True,
) -> dict:
    run_id = f"{strategy_name}_n{n}_{model}_{uuid.uuid4().hex[:8]}"
    system = build_interviewer_system_prompt()
    answers = answers_by_id()
    cache_key = f"kvbench-{model}-{strategy_name}-n{n}"

    compactor = None
    if strategy_name.upper() == "C":
        compactor = _make_compactor(
            anthropic_client, logger, run_id=run_id, bench_model=model,
            strategy_name=strategy_name, n=n,
        )
    strat = make_strategy(strategy_name, n=n, compactor=compactor)

    def invoke(messages, *, max_tokens, response_format=None):
        logger.check_cap()
        if not messages:  # never send an empty message list
            messages = [{"role": "user", "content": "Please continue."}]
        if provider == "openai":
            return call_openai(
                openai_client, model=model, system=system, messages=messages,
                max_tokens=max_tokens, prompt_cache_key=cache_key,
                response_format=response_format,
            )
        return call_anthropic(
            anthropic_client, model=model, system=system, messages=messages,
            max_tokens=max_tokens,
        )

    def log(res, *, phase, turn_index, extra=None):
        logger.log(
            run_id=run_id, bench_model=model, provider=provider, model=model,
            strategy=strategy_name, n=n, phase=phase, turn_index=turn_index,
            usage=res.usage, request=res.request, response=res.response, extra=extra,
        )

    # --- Phases 1 & 2: setup + sequential interview ---
    strat.append("user", KICKOFF)
    for k in range(1, num_turns + 1):
        res = invoke(strat.messages(), max_tokens=TURN_MAX_TOKENS)
        log(res, phase=("setup" if k == 1 else "turn"), turn_index=k)
        strat.append("assistant", res.text)   # the model's question
        strat.append("user", answers[k])       # our scripted answer
        if verbose and k % 25 == 0:
            print(f"    [{run_id}] turn {k}/{num_turns}  cum=${logger.total_cost():.4f}")

    # --- Phase 3: MCQ memory exam ---
    # Build each call as managed-history + the current question, so the question
    # (and the "json" keyword OpenAI's json_object mode requires) is ALWAYS in the
    # request and is never absorbed by compaction before it's answered. Append to
    # history only afterward, mirroring the interview-turn ordering.
    correct = 0
    json_format = {"type": "json_object"} if provider == "openai" else None
    for item in quiz:
        qprompt = _quiz_prompt(item)
        call_msgs = normalize(strat.messages() + [{"role": "user", "content": qprompt}])
        res = invoke(call_msgs, max_tokens=QUIZ_MAX_TOKENS, response_format=json_format)
        sel, parsed = _parse_quiz(res.text)
        is_correct = sel == item["correct"]
        correct += int(is_correct)
        log(res, phase="quiz", turn_index=item["question_id"], extra={
            "question_id": item["question_id"],
            "selected_option": sel,
            "correct_option": item["correct"],
            "is_correct": is_correct,
        })
        strat.append("user", qprompt)
        strat.append("assistant", res.text)

    graded = len(quiz)
    accuracy = correct / graded if graded else 0.0
    summary = {
        "run_id": run_id,
        "provider": provider,
        "model": model,
        "strategy": strategy_name,
        "n": n,
        "accuracy": accuracy,
        "correct": correct,
        "graded": graded,
        "cost_usd": logger.run_cost(run_id),
        "compactions": getattr(strat, "compaction_count", 0),
    }
    if verbose:
        print(
            f"  DONE [{run_id}] acc={accuracy:.0%} ({correct}/{graded}) "
            f"cost=${summary['cost_usd']:.4f} compactions={summary['compactions']}"
        )
    return summary
