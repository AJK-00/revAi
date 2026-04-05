"""
memory_manager.py
-----------------
Conversation memory with sliding window + LLM summarization.

Strategy:
  - Keep the last N turns in full (recent context)
  - Summarize older turns into a compact memory block
  - Inject both into every LLM prompt
  - Result: unlimited effective memory without hitting token limits
"""

import os
from dotenv import load_dotenv

load_dotenv()

import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

_summarizer = genai.GenerativeModel(
    "models/gemini-2.5-flash",
    generation_config=genai.types.GenerationConfig(
        temperature=0.1,
        max_output_tokens=512,
    )
)

# How many recent turns to keep verbatim
RECENT_TURNS  = 4
# Summarize when history exceeds this many turns
SUMMARY_AFTER = 8


def build_memory_block(history: list) -> dict:
    """
    Given a full history list of {user, assistant} dicts,
    return a memory block:
      {
        summary:     str  — compressed summary of older turns
        recent:      list — last RECENT_TURNS turns verbatim
        full_prompt: str  — formatted string ready to inject into LLM
      }
    """
    if not history:
        return {"summary": "", "recent": [], "full_prompt": ""}

    if len(history) <= RECENT_TURNS:
        # All turns fit verbatim
        recent = history
        summary = ""
    else:
        # Split: old turns get summarized, recent stays verbatim
        old_turns  = history[:-RECENT_TURNS]
        recent     = history[-RECENT_TURNS:]
        summary    = _summarize_turns(old_turns)

    full_prompt = _format_memory(summary, recent)
    return {
        "summary":     summary,
        "recent":      recent,
        "full_prompt": full_prompt,
    }


def should_summarize(history: list) -> bool:
    """Returns True when history is long enough to warrant summarization."""
    return len(history) > SUMMARY_AFTER


def _summarize_turns(turns: list) -> str:
    """Call Gemini to compress a list of conversation turns into a summary."""
    if not turns:
        return ""

    conversation_text = "\n".join(
        f"User: {t['user']}\nAssistant: {t['assistant']}"
        for t in turns
    )

    prompt = f"""Summarize the following conversation history into a concise memory block.
Capture: key topics discussed, decisions made, files/repos mentioned, important facts established.
Be brief but complete. Write in third person (e.g. "The user asked about X...").

Conversation:
{conversation_text}

Concise memory summary:"""

    try:
        response = _summarizer.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[memory] Summarization failed: {e}")
        # Fallback: just concatenate truncated turns
        return " | ".join(
            f"User asked: {t['user'][:50]}" for t in turns[:3]
        )


def _format_memory(summary: str, recent: list) -> str:
    """Format memory block as a string for LLM prompt injection."""
    parts = []

    if summary:
        parts.append(f"[Conversation Memory]\n{summary}")

    if recent:
        recent_text = "\n".join(
            f"User: {t['user']}\nAssistant: {t['assistant']}"
            for t in recent
        )
        parts.append(f"[Recent Conversation]\n{recent_text}")

    return "\n\n".join(parts)


def append_turn(history: list, user_msg: str, assistant_msg: str) -> list:
    """
    Add a new turn to history.
    If history is very long, trigger summarization to keep it manageable.
    Returns the updated history list.
    """
    history.append({"user": user_msg, "assistant": assistant_msg})

    # Auto-compress if too long (keep memory lean)
    if len(history) > SUMMARY_AFTER * 2:
        print("[memory] Auto-compressing history...")
        old   = history[:-RECENT_TURNS]
        recent = history[-RECENT_TURNS:]
        compressed_summary = _summarize_turns(old)
        # Replace old turns with a single summary entry
        history = [
            {"user": "[memory summary]", "assistant": compressed_summary},
            *recent,
        ]

    return history