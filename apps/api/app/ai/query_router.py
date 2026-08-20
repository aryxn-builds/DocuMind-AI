import re
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class QueryIntent(str, Enum):
    PAGE_QUERY = "PAGE_QUERY"
    MULTI_PAGE_QUERY = "MULTI_PAGE_QUERY"
    DOCUMENT_SUMMARY = "DOCUMENT_SUMMARY"
    GENERAL_SEMANTIC = "GENERAL_SEMANTIC"

class QueryAnalysis(BaseModel):
    intent: QueryIntent
    page_numbers: Optional[List[int]] = None
    is_broad: bool = False

class QueryRouter:
    def analyze(self, query: str) -> QueryAnalysis:
        # Check for explicit page requests
        # Pattern captures sequences of numbers, commas, "and", "to", "-" following "page" or "pages"
        pages = set()
        pattern = r'\bpages?\s+((?:\d+\s*(?:,|and|to|-)\s*)*\d+)'
        
        for match in re.finditer(pattern, query, re.IGNORECASE):
            sequence = match.group(1)
            # Split by comma or 'and'
            parts = re.split(r',|\band\b', sequence, flags=re.IGNORECASE)
            
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                    
                # Check for range: "10 to 12" or "10-12"
                range_match = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)', part, re.IGNORECASE)
                if range_match:
                    start = int(range_match.group(1))
                    end = int(range_match.group(2))
                    # Prevent overly massive ranges just in case
                    if start <= end and end - start < 1000:
                        pages.update(range(start, end + 1))
                else:
                    # Single number
                    num_match = re.search(r'\d+', part)
                    if num_match:
                        pages.add(int(num_match.group()))
        
        page_numbers = sorted(list(pages))
        
        if page_numbers:
            if len(page_numbers) == 1:
                return QueryAnalysis(intent=QueryIntent.PAGE_QUERY, page_numbers=page_numbers)
            else:
                return QueryAnalysis(intent=QueryIntent.MULTI_PAGE_QUERY, page_numbers=page_numbers)

        # Check for broad/summary intent if no pages specified
        if re.search(r'\b(summarize|overview|entire|main points|tl;dr)\b', query, re.IGNORECASE):
            return QueryAnalysis(intent=QueryIntent.DOCUMENT_SUMMARY, is_broad=True)
                
        # Default fallback
        return QueryAnalysis(intent=QueryIntent.GENERAL_SEMANTIC, is_broad=False)

query_router = QueryRouter()
