import pytest
from app.ai.query_router import query_router, QueryIntent

def test_page_query_retrieval():
    res = query_router.analyze("about the content in page 10")
    assert res.intent == QueryIntent.PAGE_QUERY
    assert res.page_numbers == [10]

def test_multi_page_query_retrieval():
    res = query_router.analyze("compare the content of page 10 and page 12")
    assert res.intent == QueryIntent.MULTI_PAGE_QUERY
    assert res.page_numbers == [10, 12]

    res2 = query_router.analyze("compare pages 10, 12 and 15")
    assert res2.intent == QueryIntent.MULTI_PAGE_QUERY
    assert res2.page_numbers == [10, 12, 15]

def test_page_range_query_retrieval():
    res = query_router.analyze("summarize pages 10 to 12")
    assert res.intent == QueryIntent.MULTI_PAGE_QUERY
    assert res.page_numbers == [10, 11, 12]

    res2 = query_router.analyze("summarize pages 10-12")
    assert res2.intent == QueryIntent.MULTI_PAGE_QUERY
    assert res2.page_numbers == [10, 11, 12]

def test_document_summary_query():
    res = query_router.analyze("summarize the document")
    assert res.intent == QueryIntent.DOCUMENT_SUMMARY
    assert res.page_numbers is None
    assert res.is_broad is True

def test_general_semantic_query():
    res = query_router.analyze("explain the methodology in detail")
    assert res.intent == QueryIntent.GENERAL_SEMANTIC
    assert res.page_numbers is None
    assert res.is_broad is False
