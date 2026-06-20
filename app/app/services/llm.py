from __future__ import annotations

import json
import logging

from ..config import settings

logger = logging.getLogger(__name__)

MOODS = ["happy", "sad", "excited", "confused", "sleepy", "scared", "neutral"]

POPISH_CUES = {
    "happy": "Popo-ki! Po-pi-po!",
    "sad": "Poo-po… po-o.",
    "excited": "Pi-pi-popo-ki-ya!",
    "confused": "Po… po-po?",
    "sleepy": "Pooooo… mmm… po.",
    "scared": "PO!… po… po.",
    "neutral": "Po-po.",
}

_SYSTEM = """You are a mood and intent classifier for Popo, an AI desk companion.
Given a user's spoken message, classify:
1. mood: one of happy/sad/excited/confused/sleepy/scared/neutral
2. intent: a short snake_case label (e.g. emotional_share, question, greeting, focus_request)
3. confidence: float 0.0–1.0

Reply ONLY with valid JSON: {"mood": "...", "intent": "...", "confidence": 0.9}
No explanation, no markdown fences."""


async def classify_mood(transcript: str) -> dict:
    """Call Claude Haiku to classify mood and intent from a transcript.

    Falls back to rule-based classification if the API key is absent or the
    call fails, so the device always gets a valid response.
    """
    if not transcript or not transcript.strip():
        return {"mood": "neutral", "intent": "silence", "confidence": 1.0}

    if not settings.anthropic_api_key:
        return _rule_based(transcript)

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            system=_SYSTEM,
            messages=[{"role": "user", "content": transcript}],
        )
        text = message.content[0].text.strip()
        result = json.loads(text)
        mood = result.get("mood", "neutral")
        if mood not in MOODS:
            mood = "neutral"
        return {
            "mood": mood,
            "intent": result.get("intent", "unknown"),
            "confidence": float(result.get("confidence", 0.8)),
        }
    except Exception as exc:
        logger.warning("LLM classify failed (%s), falling back to rule-based", exc)
        return _rule_based(transcript)


def _rule_based(transcript: str) -> dict:
    t = transcript.lower()
    if any(w in t for w in ("happy", "great", "love", "yay", "wonderful", "awesome")):
        return {"mood": "happy", "intent": "emotional_share", "confidence": 0.7}
    if any(w in t for w in ("sad", "upset", "cry", "depressed", "miss", "lonely")):
        return {"mood": "sad", "intent": "emotional_share", "confidence": 0.7}
    if any(w in t for w in ("excited", "can't wait", "amazing", "wow", "!")):
        return {"mood": "excited", "intent": "emotional_share", "confidence": 0.7}
    if any(w in t for w in ("tired", "sleepy", "exhausted", "bed", "sleep")):
        return {"mood": "sleepy", "intent": "state_report", "confidence": 0.7}
    if any(w in t for w in ("scared", "afraid", "worried", "anxious")):
        return {"mood": "scared", "intent": "emotional_share", "confidence": 0.7}
    if any(w in t for w in ("?", "what", "how", "why", "where", "when", "who")):
        return {"mood": "confused", "intent": "question", "confidence": 0.6}
    return {"mood": "neutral", "intent": "general", "confidence": 0.5}


def get_popish_cue(mood: str) -> str:
    return POPISH_CUES.get(mood, POPISH_CUES["neutral"])
