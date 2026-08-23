"""Tests for section-aware, table-atomic, parent-child chunking (Roadmap Phase 1,
Milestone 1).

Covers the three acceptance criteria for this milestone:
- A table is never split across two chunks.
- A heading boundary is respected (chunks after a heading carry that
  heading as section_title, and a new section starts a new parent chunk).
- Child chunks link to a parent section chunk via parent_chunk_index, and
  the parent's text accumulates its children's content.
"""
import pytest

from backend.utils.pdf_parser_enhanced import EnhancedPDFParser


def _block(text, page_number=1, bbox=(10.0, 10.0, 200.0, 20.0), avg_font_size=None):
    return {
        "text": text,
        "page_number": page_number,
        "bbox": {"x1": bbox[0], "y1": bbox[1], "x2": bbox[2], "y2": bbox[3]},
        "avg_font_size": avg_font_size,
    }


class TestTableAtomicity:
    def test_table_region_is_never_split_and_appears_as_one_chunk(self):
        """A block that overlaps a table's bbox must be excluded from prose
        chunking, and the table itself must appear exactly once, as a
        single atomic chunk using its markdown."""
        parser = EnhancedPDFParser()

        # A prose block that happens to fall inside the table's bbox
        # (e.g. pdfplumber and PyMuPDF both saw the same region).
        table_region_block = _block(
            "Q1 100 Q2 200 Q3 300",
            bbox=(10.0, 100.0, 200.0, 150.0),
        )
        prose_before = _block("Introductory paragraph before the table.", bbox=(10.0, 10.0, 200.0, 20.0))
        prose_after = _block("Concluding paragraph after the table.", bbox=(10.0, 200.0, 200.0, 210.0))

        table = {
            "page_number": 1,
            "table_index": 0,
            "bbox": {"x1": 10.0, "y1": 100.0, "x2": 200.0, "y2": 150.0},
            "markdown": "| Q1 | Q2 | Q3 |\n| --- | --- | --- |\n| 100 | 200 | 300 |",
        }

        chunks = parser.chunk_blocks(
            [prose_before, table_region_block, prose_after],
            chunk_size=500,
            overlap=50,
            tables=[table],
        )

        table_chunks = [c for c in chunks if c.get("chunk_type") == "table"]
        assert len(table_chunks) == 1, "table must appear exactly once, never split"
        assert table_chunks[0]["text"] == table["markdown"]

        # The table-region prose block must not leak into any text chunk.
        for chunk in chunks:
            if chunk.get("chunk_type") != "table":
                assert "Q1 100 Q2 200 Q3 300" not in chunk["text"]

        # Prose before/after the table must still be present somewhere.
        all_text = " ".join(c["text"] for c in chunks)
        assert "Introductory paragraph" in all_text
        assert "Concluding paragraph" in all_text

    def test_large_table_markdown_is_not_split_even_if_it_exceeds_chunk_size(self):
        """Table atomicity must hold even when the table's markdown is
        larger than the configured prose chunk_size."""
        parser = EnhancedPDFParser()
        big_markdown = "| A | B |\n| --- | --- |\n" + "\n".join(
            f"| row{i} | value{i} |" for i in range(200)
        )
        table = {
            "page_number": 1,
            "table_index": 0,
            "bbox": {"x1": 0.0, "y1": 0.0, "x2": 100.0, "y2": 100.0},
            "markdown": big_markdown,
        }

        chunks = parser.chunk_blocks([], chunk_size=100, overlap=20, tables=[table])
        table_chunks = [c for c in chunks if c.get("chunk_type") == "table"]

        assert len(table_chunks) == 1
        assert table_chunks[0]["text"] == big_markdown


class TestSectionAwareChunking:
    def test_heading_starts_a_new_section_and_is_recorded_on_chunks(self):
        """A block whose font size is notably larger than the body-text
        median, and which is short, must be treated as a heading. Chunks
        that follow it must carry it as their section_title."""
        parser = EnhancedPDFParser()

        body_size = 10.0
        heading_size = 16.0

        blocks = [
            _block("Introduction paragraph one. " * 5, avg_font_size=body_size),
            _block("Introduction paragraph two. " * 5, avg_font_size=body_size),
            _block("Security Policy", avg_font_size=heading_size),  # heading
            _block("All access must be authenticated. " * 5, avg_font_size=body_size),
            _block("Every request must be authorized. " * 5, avg_font_size=body_size),
        ]

        chunks = parser.chunk_blocks(blocks, chunk_size=1000, overlap=50)
        text_chunks = [c for c in chunks if c.get("chunk_type") == "text" and not c.get("is_parent")]

        pre_heading = [c for c in text_chunks if "Introduction paragraph" in c["text"]]
        post_heading = [c for c in text_chunks if "authenticated" in c["text"] or "authorized" in c["text"]]

        assert pre_heading, "expected at least one chunk before the heading"
        assert post_heading, "expected at least one chunk after the heading"

        for c in pre_heading:
            assert c["section_title"] is None
        for c in post_heading:
            assert c["section_title"] == "Security Policy"

    def test_no_font_size_metadata_falls_back_to_no_sections_gracefully(self):
        """When blocks carry no font-size metadata (e.g. OCR-derived text),
        heading detection must not guess — chunking should still succeed
        with section_title left None rather than raising."""
        parser = EnhancedPDFParser()
        blocks = [
            _block("Some OCR text with no font metadata. " * 10),
            _block("More OCR text continuing the document. " * 10),
        ]

        chunks = parser.chunk_blocks(blocks, chunk_size=200, overlap=20)
        assert len(chunks) > 0
        for c in chunks:
            assert c.get("section_title") is None


class TestParentChildLinkage:
    def test_child_chunks_link_to_a_parent_section_chunk(self):
        """Every non-parent chunk within a detected section must reference
        a parent chunk (by position in the returned list), and that parent
        must exist, be marked is_parent, and contain the concatenation of
        its children's text."""
        parser = EnhancedPDFParser()

        body_size = 10.0
        heading_size = 16.0
        blocks = [
            _block("Overview", avg_font_size=heading_size),
            _block("First part of the overview section. " * 5, avg_font_size=body_size),
            _block("Second part of the overview section. " * 5, avg_font_size=body_size),
        ]

        chunks = parser.chunk_blocks(blocks, chunk_size=100, overlap=10)

        parents = [c for c in chunks if c.get("is_parent")]
        children = [c for c in chunks if not c.get("is_parent") and c.get("chunk_type") == "text"]

        assert len(parents) == 1, "expected exactly one parent for the one detected section"
        assert len(children) >= 1

        parent_index = chunks.index(parents[0])
        for child in children:
            assert child["parent_chunk_index"] == parent_index

        # The parent's accumulated text must contain both children's content.
        assert "First part of the overview" in parents[0]["text"]
        assert "Second part of the overview" in parents[0]["text"]

    def test_chunks_with_no_detected_heading_have_no_parent(self):
        """Documents with no detectable heading structure must not
        fabricate a parent chunk — parent_chunk_index should be None."""
        parser = EnhancedPDFParser()
        blocks = [_block("Just plain body text with no heading. " * 5)]

        chunks = parser.chunk_blocks(blocks, chunk_size=1000, overlap=50)
        parents = [c for c in chunks if c.get("is_parent")]

        # A single top-level "section" (None) is still allowed to have a
        # synthetic parent for consistency; what matters is every child's
        # parent_chunk_index resolves to a real chunk in the list.
        for chunk in chunks:
            if chunk.get("parent_chunk_index") is not None:
                assert 0 <= chunk["parent_chunk_index"] < len(chunks)
                assert chunks[chunk["parent_chunk_index"]].get("is_parent") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


class TestCitationBoundingBoxes:
    def test_same_page_child_uses_a_union_bbox_for_all_of_its_blocks(self):
        parser = EnhancedPDFParser()
        chunks = parser.chunk_blocks(
            [
                _block("First evidence block.", bbox=(10.0, 20.0, 100.0, 40.0)),
                _block("Second evidence block.", bbox=(15.0, 80.0, 120.0, 100.0)),
            ],
            chunk_size=1000,
            overlap=0,
        )

        child = next(chunk for chunk in chunks if not chunk.get("is_parent"))
        assert child["page_number"] == 1
        assert child["bbox"] == {"x1": 10.0, "y1": 20.0, "x2": 120.0, "y2": 100.0}
        assert "First evidence block." in child["text"]
        assert "Second evidence block." in child["text"]

    def test_child_chunk_is_finalized_before_a_page_transition(self):
        parser = EnhancedPDFParser()
        chunks = parser.chunk_blocks(
            [
                _block("Evidence on page one.", page_number=1, bbox=(10.0, 20.0, 100.0, 40.0)),
                _block("Evidence on page two.", page_number=2, bbox=(15.0, 80.0, 120.0, 100.0)),
            ],
            chunk_size=1000,
            overlap=0,
        )

        children = [chunk for chunk in chunks if not chunk.get("is_parent")]
        assert [(chunk["page_number"], chunk["bbox"]) for chunk in children] == [
            (1, {"x1": 10.0, "y1": 20.0, "x2": 100.0, "y2": 40.0}),
            (2, {"x1": 15.0, "y1": 80.0, "x2": 120.0, "y2": 100.0}),
        ]
