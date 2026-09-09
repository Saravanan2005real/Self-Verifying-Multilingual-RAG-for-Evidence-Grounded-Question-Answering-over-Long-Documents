package com.docquery.service.vector;

import com.docquery.model.DocumentChunk;
import com.docquery.model.ScoredChunk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@Primary
public class CompositeVectorStoreService implements VectorStoreService {

    private static final Logger log = LoggerFactory.getLogger(CompositeVectorStoreService.class);

    private final ChromaVectorStoreService chromaService;
    private final InMemoryVectorStoreService inMemoryService;

    public CompositeVectorStoreService(ChromaVectorStoreService chromaService, InMemoryVectorStoreService inMemoryService) {
        this.chromaService = chromaService;
        this.inMemoryService = inMemoryService;
    }

    @Override
    public void store(String documentId, List<DocumentChunk> chunks, List<float[]> embeddings) {
        // Always store in in-memory cache for ultra-fast local retrieval and resilience
        inMemoryService.store(documentId, chunks, embeddings);

        // Also store in ChromaDB if available
        if (chromaService.isAvailable()) {
            try {
                chromaService.store(documentId, chunks, embeddings);
                log.info("Indexed chunks into both ChromaDB and In-Memory cache for doc '{}'", documentId);
            } catch (Exception e) {
                log.warn("Failed to sync to ChromaDB, in-memory store remains active: {}", e.getMessage());
            }
        } else {
            log.info("ChromaDB is offline. Indexed into In-Memory store for doc '{}'", documentId);
        }
    }

    @Override
    public List<ScoredChunk> query(String documentId, float[] queryEmbedding, int topK) {
        if (chromaService.isAvailable()) {
            try {
                List<ScoredChunk> results = chromaService.query(documentId, queryEmbedding, topK);
                if (results != null && !results.isEmpty()) {
                    return results;
                }
            } catch (Exception e) {
                log.warn("ChromaDB query failed, falling back to In-Memory store: {}", e.getMessage());
            }
        }

        return inMemoryService.query(documentId, queryEmbedding, topK);
    }

    @Override
    public void delete(String documentId) {
        inMemoryService.delete(documentId);
        if (chromaService.isAvailable()) {
            try {
                chromaService.delete(documentId);
            } catch (Exception ignored) {}
        }
    }

    @Override
    public boolean isAvailable() {
        return true;
    }

    @Override
    public String getStoreType() {
        if (chromaService.isAvailable()) {
            return "ChromaDB (Active) + In-Memory Fallback";
        }
        return "In-Memory Vector Store (ChromaDB Offline)";
    }
}
