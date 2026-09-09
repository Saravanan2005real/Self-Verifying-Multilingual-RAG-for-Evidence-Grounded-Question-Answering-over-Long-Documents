package com.docquery;

import com.docquery.model.DocumentChunk;
import com.docquery.model.PageText;
import com.docquery.model.ParsedDocument;
import com.docquery.service.chunking.TextChunker;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class TextChunkerTest {

    @Test
    public void testChunkDocumentWithOverlapAndPages() {
        TextChunker chunker = new TextChunker();

        StringBuilder p1 = new StringBuilder();
        for (int i = 0; i < 300; i++) {
            p1.append("word").append(i).append(" ");
        }

        StringBuilder p2 = new StringBuilder();
        for (int i = 300; i < 700; i++) {
            p2.append("term").append(i).append(" ");
        }

        ParsedDocument doc = new ParsedDocument("test.pdf", 2, List.of(
                new PageText(1, p1.toString()),
                new PageText(2, p2.toString())
        ));

        List<DocumentChunk> chunks = chunker.chunkDocument("doc_1", doc, 450, 60);

        assertFalse(chunks.isEmpty());
        assertEquals(2, chunks.size());

        DocumentChunk first = chunks.get(0);
        assertEquals(0, first.getChunkIndex());
        assertEquals(1, first.getStartPage());
        assertEquals(2, first.getEndPage());
        assertEquals(450, first.getWordCount());
        assertTrue(first.getPageDisplay().contains("Pages 1-2"));

        DocumentChunk second = chunks.get(1);
        assertEquals(1, second.getChunkIndex());
        assertEquals(2, second.getStartPage());
        assertEquals(2, second.getEndPage());
        assertEquals("Page 2", second.getPageDisplay());
    }
}
