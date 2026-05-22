"""Pure-logic tests for the three history strategies. No API calls, no cost."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.history import (  # noqa: E402
    StrategyA, StrategyB, StrategyC, normalize, make_strategy,
)


def test_strategy_a_grows_unbounded():
    a = StrategyA()
    for i in range(10):
        a.append("user" if i % 2 == 0 else "assistant", f"m{i}")
    assert len(a.history) == 10, "A must keep every message"
    print("PASS test_strategy_a_grows_unbounded")


def test_strategy_b_drops_oldest():
    b = StrategyB(n=4)
    # append 6 messages; only the last 4 should remain
    seq = [("user", "u1"), ("assistant", "a1"), ("user", "u2"),
           ("assistant", "a2"), ("user", "u3"), ("assistant", "a3")]
    for role, content in seq:
        b.append(role, content)
    assert len(b.history) == 4, f"B must cap at n=4, got {len(b.history)}"
    contents = [m["content"] for m in b.history]
    assert contents == ["u2", "a2", "u3", "a3"], f"B must drop oldest, got {contents}"
    assert "u1" not in contents and "a1" not in contents, "B must have dropped u1/a1"
    print("PASS test_strategy_b_drops_oldest")


def test_strategy_b_normalizes_to_user_first():
    b = StrategyB(n=2)
    b.append("user", "u1")
    b.append("assistant", "a1")
    b.append("user", "u2")
    b.append("assistant", "a2")  # window = [u2, a2]? -> last 2 = [u2,a2]
    msgs = b.messages()
    assert msgs[0]["role"] == "user", "normalized messages must start with user"
    print("PASS test_strategy_b_normalizes_to_user_first")


def test_strategy_c_compacts_and_replaces():
    calls = {"count": 0, "last_text": None}

    def fake_compactor(text):
        calls["count"] += 1
        calls["last_text"] = text
        return "DENSE SUMMARY OF EARLIER TURNS"

    c = StrategyC(n=4, compactor=fake_compactor)
    for role, content in [("user", "u1"), ("assistant", "a1"),
                          ("user", "u2"), ("assistant", "a2")]:
        c.append(role, content)
    # hitting n=4 must trigger exactly one compaction and clear raw history
    assert calls["count"] == 1, f"compactor must be called once, got {calls['count']}"
    assert c.history == [], "raw history must be cleared after compaction"
    assert c.summary == "DENSE SUMMARY OF EARLIER TURNS"
    assert c.compaction_count == 1
    # the compactor must have seen the raw turns
    assert "u1" in calls["last_text"] and "a2" in calls["last_text"]
    # messages() must surface the summary as the first (user) message
    msgs = c.messages()
    assert msgs[0]["role"] == "user"
    assert "DENSE SUMMARY" in msgs[0]["content"]
    print("PASS test_strategy_c_compacts_and_replaces")


def test_strategy_c_folds_prior_summary():
    summaries = []

    def fake_compactor(text):
        summaries.append(text)
        return f"SUMMARY#{len(summaries)}"

    c = StrategyC(n=2, compactor=fake_compactor)
    c.append("user", "u1")
    c.append("assistant", "a1")   # hits n=2 -> compaction 1
    c.append("user", "u2")
    c.append("assistant", "a2")   # hits n=2 -> compaction 2, must include prior summary
    assert c.compaction_count == 2
    assert "PREVIOUS SUMMARY" in summaries[1], "2nd compaction must fold the prior summary"
    assert "SUMMARY#1" in summaries[1]
    print("PASS test_strategy_c_folds_prior_summary")


def test_normalize_merges_consecutive_same_role():
    msgs = [
        {"role": "assistant", "content": "leading-assistant-dropped"},
        {"role": "user", "content": "u1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a1"},
    ]
    out = normalize(msgs)
    assert out[0]["role"] == "user", "must drop leading assistant"
    assert out[0]["content"] == "u1\n\nu2", "must merge consecutive user messages"
    assert len(out) == 2 and out[1]["role"] == "assistant"
    print("PASS test_normalize_merges_consecutive_same_role")


def test_factory_and_validation():
    assert isinstance(make_strategy("A"), StrategyA)
    assert isinstance(make_strategy("B", n=5), StrategyB)
    assert isinstance(make_strategy("C", n=5, compactor=lambda t: "s"), StrategyC)
    for bad in (lambda: StrategyB(n=0), lambda: StrategyC(n=2, compactor=None)):
        try:
            bad()
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for invalid strategy config")
    print("PASS test_factory_and_validation")


if __name__ == "__main__":
    test_strategy_a_grows_unbounded()
    test_strategy_b_drops_oldest()
    test_strategy_b_normalizes_to_user_first()
    test_strategy_c_compacts_and_replaces()
    test_strategy_c_folds_prior_summary()
    test_normalize_merges_consecutive_same_role()
    test_factory_and_validation()
    print("\nALL HISTORY TESTS PASSED")
