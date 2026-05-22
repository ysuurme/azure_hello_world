import os
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT
from src.utils.m_log import f_log


def knowledge_base_retrieve(query: str, search_client: Any = None) -> list[dict[str, Any]]:
    """
    Simulates Context-Aware Search across Azure AI Search by scanning local capabilities/.
    Reads markdown files as raw capability context.
    """
    f_log(f"Executing local semantic hybrid search for: {query}", c_type="retrieve")
    
    cap_dir = PROJECT_ROOT / "capabilities"
    results = []
    
    if cap_dir.exists() and cap_dir.is_dir():
        for md_file in cap_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                # Basic keyword matching (mocking semantic search)
                if any(word.lower() in content.lower() for word in query.split()):
                    results.append({"id": md_file.name, "content": content[:500] + "..."})
            except Exception as e:
                f_log(f"Failed to read capability file {md_file.name}: {e}", c_type="error")
                
    if not results:
        f_log("No specific capabilities matched. Returning default WAF guidance.", c_type="warning")
        results = [
            {"id": "default-waf", "content": "WAF Resiliency best practices suggest multi-region deployments."}
        ]
        
    return results
