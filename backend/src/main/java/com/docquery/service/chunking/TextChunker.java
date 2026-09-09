package com.docquery.service.chunking;

import com.docquery.model.DocumentChunk;
import com.docquery.model.PageText;
import com.docquery.model.ParsedDocument;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class TextChunker {

    private static final Logger log = LoggerFactory.getLogger(TextChunker.class);

    private static final int DEFAULT_CHUNK_SIZE = 450; // words per chunk (~500 words)
    private static final int DEFAULT_OVERLAP = 60;      // words overlap

    private static class WordInfo {
        final String word;
        final int pageNumber;

        WordInfo(String word, int pageNumber) {
            this.word = word;
            this.pageNumber = pageNumber;
        }
    }

    public List<DocumentChunk> chunkDocument(String documentId, ParsedDocument document) {
        return chunkDocument(documentId, document, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP);
    }

    public List<DocumentChunk> chunkDocument(String documentId, ParsedDocument document, int chunkSize, int overlap) {
        List<WordInfo> allWords = new ArrayList<>();

        for (PageText page : document.getPages()) {
            if (page.getText() == null || page.getText().isBlank()) {
                continue;
            }
            String[] tokens = page.getText().split("\\s+");
            for (String token : tokens) {
                if (!token.isBlank()) {
                    allWords.add(new WordInfo(token, page.getPageNumber()));
                }
            }
        }

        List<DocumentChunk> chunks = new ArrayList<>();
        if (allWords.isEmpty()) {
            log.warn("Document {} contains no readable words.", documentId);
            return chunks;
        }

        int startIdx = 0;
        int chunkIndex = 0;

        while (startIdx < allWords.size()) {
            int endIdx = Math.min(startIdx + chunkSize, allWords.size());

            StringBuilder sb = new StringBuilder();
            int startPage = allWords.get(startIdx).pageNumber;
            int endPage = allWords.get(endIdx - 1).pageNumber;

            for (int i = startIdx; i < endIdx; i++) {
                if (i > startIdx) {
                    sb.append(" ");
                }
                sb.append(allWords.get(i).word);
            }

            String content = sb.toString().trim();
            int wordCount = endIdx - startIdx;
            String chunkId = documentId + "_chunk_" + chunkIndex;

            chunks.add(new DocumentChunk(
                    chunkId,
                    documentId,
                    chunkIndex,
                    startPage,
                    endPage,
                    content,
                    wordCount
            ));

            chunkIndex++;

            if (endIdx >= allWords.size()) {
                break;
            }

            // Advance with overlap
            startIdx += Math.max(1, chunkSize - overlap);
        }

        log.info("Chunked document {} ({} total words) into {} chunks", documentId, allWords.size(), chunks.size());
        return chunks;
    }
}
