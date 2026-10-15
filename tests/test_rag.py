"""Automated tests for PyMuPDF extraction, chunking, semantic similarity retrieval, and RAG."""

import os
import pymupdf as fitz  # PyMuPDF
import pytest
from pathlib import Path
from services.rag_service import rag_service


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Generate a clean 2-page academic lecture notes PDF for testing."""
    pdf_file = tmp_path / "test_algorithms_notes.pdf"
    doc = fitz.open()

    # Page 1: Binary Search Trees
    page1 = doc.new_page()
    page1.insert_text(
        fitz.Point(50, 72),
        "Chapter 1: Binary Search Trees (BST)\n\n"
        "A Binary Search Tree is a node-based binary tree data structure with the property that "
        "the left subtree of a node contains only keys lesser than the node's key, and the right "
        "subtree contains only keys greater than the node's key. The average time complexity for "
        "search, insertion, and deletion operations is O(log n).",
        fontsize=12,
    )

    # Page 2: Hash Tables and Collisions
    page2 = doc.new_page()
    page2.insert_text(
        fitz.Point(50, 72),
        "Chapter 2: Hash Tables and Collision Resolution\n\n"
        "A Hash Table maps keys to values using a hash function. When two distinct keys hash to the "
        "same bucket index, a hash collision occurs. The two primary techniques for collision "
        "resolution are Separate Chaining and Open Addressing with linear or quadratic probing.",
        fontsize=12,
    )

    doc.save(str(pdf_file))
    doc.close()
    return str(pdf_file)


def test_extract_text_from_pdf_page_count_and_content(sample_pdf_path):
    """Test PyMuPDF extracts text per page and tracks page numbers accurately."""
    result = rag_service.extract_text_from_pdf(sample_pdf_path)

    assert result["page_count"] == 2
    assert len(result["pages"]) == 2
    assert result["pages"][0]["page"] == 1
    assert "Binary Search Tree" in result["pages"][0]["text"]
    assert result["pages"][1]["page"] == 2
    assert "Hash Tables" in result["pages"][1]["text"]


def test_chunking_with_page_metadata():
    """Test text chunking preserves page numbers and text blocks."""
    mock_pages = [
        {"page": 1, "text": "This is page one introductory material for computer science."},
        {"page": 2, "text": "This is page two advanced concepts and algorithms."},
    ]
    chunks = rag_service.chunk_document(mock_pages)

    assert len(chunks) >= 2
    assert chunks[0]["page"] == 1
    assert "computer science" in chunks[0]["text"]
    assert any(c["page"] == 2 for c in chunks)


def test_cosine_similarity_retrieval():
    """Test semantic retrieval returns the most relevant chunk with highest score."""
    test_chunks = [
        {"id": 0, "page": 1, "text": "Binary search trees maintain sorted order for fast O(log n) lookups."},
        {"id": 1, "page": 2, "text": "Hash collisions can be handled using open addressing or separate chaining."},
        {"id": 2, "page": 3, "text": "Dynamic programming solves problems by breaking them into overlapping subproblems."},
    ]

    # Query about collisions
    retrieved = rag_service.retrieve_relevant_chunks("How are hash collisions resolved?", test_chunks, top_k=2)

    assert len(retrieved) > 0
    # Top match should be chunk id 1 (Hash collisions)
    assert retrieved[0]["id"] == 1
    assert retrieved[0]["page"] == 2
    assert "Hash collisions" in retrieved[0]["text"]


def test_irrelevant_query_returns_not_enough_info():
    """Test that queries completely unrelated to the notes return informative message."""
    test_chunks = [
        {"id": 0, "page": 1, "text": "Data structures like arrays, stacks, and queues organize computer memory."},
    ]

    result = rag_service.answer_question(
        query="What is the capital city of France in 1850?",
        chunks=test_chunks,
    )

    assert "The uploaded notes do not contain enough information to answer this question." in result["answer"]
