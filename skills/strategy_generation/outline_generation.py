import logging
from typing import Dict, List, Any

from skills.openai_utils import chat_completion_json

logger = logging.getLogger(__name__)

def generate_topic_outline(topic_title: str, topic_description: str, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates a high-quality blog outline based on a topic cluster and competitor context.
    Ensures the output is "human-like" and comprehensive.
    """
    
    # Process article summaries for context
    context_bits = []
    for art in articles[:5]:
        content_preview = (art.get("content") or "")[:1000]
        context_bits.append(f"Source: {art.get('title')} ({art.get('url')})\nContent: {content_preview}...")
    
    context_str = "\n---\n".join(context_bits)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert Content Strategist and high-end Editorial Director. "
                "Your goal is to create a blog outline that doesn't look like generic AI content. "
                "Focus on narrative flow, uniquely human angles, expert insights, and satisfying user intent depth. "
                "Output MUST be in JSON format."
            )
        },
        {
            "role": "user",
            "content": f"""
Generate a comprehensive, human-like blog post outline for the following strategic pillar:

TOPIC: {topic_title}
STRATEGIC ANGLE: {topic_description}

COMPETITOR CONTEXT (Top ranking articles in this cluster):
{context_str}

The outline should include:
1. A suggested Title (SEO-friendly but high CTR/curiosity).
2. The 'Human Angle' or Narrative Hook (How to start the piece so it feels authentic).
3. A structured set of H2 and H3 headers.
4. 'Expert Insight' callouts for 2-3 sections (specific unique takes that competitors might be missing).
5. Target User Intent (What is the reader trying to solve?).
6. Suggested word count for a 'complete' guide.

JSON Structure:
{{
  "title": "...",
  "narrative_hook": "...",
  "intent": "...",
  "target_word_count": 2500,
  "sections": [
    {{
      "heading": "...",
      "subheadings": ["...", "..."],
      "expert_insight": "Optional unique take"
    }}
  ]
}}
"""
        }
    ]

    try:
        outline = chat_completion_json(messages)
        return outline
    except Exception as exc:
        logger.error(f"Failed to generate outline for {topic_title}: {exc}")
        raise
