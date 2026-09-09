package com.docquery.service.vector;

import com.docquery.model.DocumentChunk;
import com.docquery.model.ScoredChunk;

import java.util.List;

public interface VectorStoreService {
    void store(String documentId, List<DocumentChunk> chunks, List<float[]> embeddings);
    List<ScoredChunk> query(String documentId, float[] queryEmbedding, int topK);
    void delete(String documentId);
    boolean isAvailable();
    String getStoreType();
}
