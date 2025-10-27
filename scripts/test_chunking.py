"""
Test script for the new hierarchical chunking implementation.
"""

from pipelines.chunk import HierarchicalChunker


def test_markdown_headers():
    """Test chunking with markdown headers."""
    print("\n" + "="*60)
    print("TEST 1: Markdown Headers")
    print("="*60)

    text = """# Introduction

This is the introduction section. It has some content that explains what this document is about.

## Background

Here is some background information. This section provides context for the reader.

### Details

More detailed information goes here. This is a subsection with additional details.

## Methods

This section describes the methods used in the research.
"""

    chunker = HierarchicalChunker(chunk_tokens=100, overlap_sentences=2)
    chunks = chunker.chunk_text(text)

    print(f"\nGenerated {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ---")
        print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
        print()


def test_numbered_headers():
    """Test chunking with numbered headers."""
    print("\n" + "="*60)
    print("TEST 2: Numbered Headers")
    print("="*60)

    text = """1 Executive Summary

This document presents our findings from the research study.

1.1 Key Findings

The key findings indicate several important trends in the data.

1.2 Recommendations

Based on our analysis, we recommend the following actions.

2 Detailed Analysis

This section provides a detailed analysis of the results.
"""

    chunker = HierarchicalChunker(chunk_tokens=100, overlap_sentences=2)
    chunks = chunker.chunk_text(text)

    print(f"\nGenerated {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ---")
        print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
        print()


def test_allcaps_headers():
    """Test chunking with all caps headers."""
    print("\n" + "="*60)
    print("TEST 3: All Caps Headers")
    print("="*60)

    text = """INTRODUCTION

This is the introduction section with all caps header.

BACKGROUND

Here is some background information with another all caps header.

METHODOLOGY

This section describes the methodology used in the study.
"""

    chunker = HierarchicalChunker(chunk_tokens=100, overlap_sentences=2)
    chunks = chunker.chunk_text(text)

    print(f"\nGenerated {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ---")
        print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
        print()


def test_underlined_headers():
    """Test chunking with underlined headers."""
    print("\n" + "="*60)
    print("TEST 4: Underlined Headers")
    print("="*60)

    text = """Main Title
==========

This is the introduction section with an underlined header.

Subsection Title
----------------

Here is a subsection with a different underline style.

Another Section
===============

This is another major section with an underlined header.
"""

    chunker = HierarchicalChunker(chunk_tokens=100, overlap_sentences=2)
    chunks = chunker.chunk_text(text)

    print(f"\nGenerated {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ---")
        print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
        print()


def test_large_content():
    """Test chunking with large content that needs splitting."""
    print("\n" + "="*60)
    print("TEST 5: Large Content with Paragraph Splitting")
    print("="*60)

    text = """# Long Section

This is a very long section that will need to be split into multiple chunks. """ + \
    """It contains multiple paragraphs of text that exceed the token limit. """ * 20 + """

This is a second paragraph that adds more content. """ + \
    """It continues with additional information that should be in a separate chunk. """ * 15 + """

This is a third paragraph with even more content. """ + \
    """The chunker should handle this appropriately by splitting at paragraph boundaries. """ * 10

    chunker = HierarchicalChunker(chunk_tokens=200, overlap_sentences=2)
    chunks = chunker.chunk_text(text)

    print(f"\nGenerated {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        word_count = len(chunk.split())
        print(f"--- Chunk {i} ({word_count} words) ---")
        print(chunk[:150] + "..." if len(chunk) > 150 else chunk)
        print()


def test_mixed_headers():
    """Test chunking with mixed header styles."""
    print("\n" + "="*60)
    print("TEST 6: Mixed Header Styles")
    print("="*60)

    text = """Main Document Title
===================

This document demonstrates mixed header styles.

# Chapter 1: Introduction

This is the first chapter using markdown headers.

## 1.1 Background

Numbered subsection using markdown header.

IMPORTANT NOTICE

This is an all-caps header for emphasis.

### 1.1.1 Historical Context

A deeper level subsection with more details.

Chapter 2: Methods
------------------

This chapter uses an underlined header style.
"""

    chunker = HierarchicalChunker(chunk_tokens=100, overlap_sentences=2)
    chunks = chunker.chunk_text(text)

    print(f"\nGenerated {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ---")
        print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
        print()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("HIERARCHICAL CHUNKING TESTS")
    print("="*60)

    test_markdown_headers()
    test_numbered_headers()
    test_allcaps_headers()
    test_underlined_headers()
    test_large_content()
    test_mixed_headers()

    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)


if __name__ == "__main__":
    main()
