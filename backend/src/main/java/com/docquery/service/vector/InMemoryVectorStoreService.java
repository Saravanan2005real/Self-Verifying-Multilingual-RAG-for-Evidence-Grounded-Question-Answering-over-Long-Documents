package com.docquery.service.vector;

import com.docquery.model.DocumentChunk;
import com.docquery.model.ScoredChunk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
public class InMemoryVectorStoreService implements VectorStoreService {

    private static final Logger log = LoggerFactory.getLogger(InMemoryVectorStoreService.class);

    private static class EmbeddedChunk {
        final DocumentChunk chunk;
        final float[] embedding;
        final double norm;

        EmbeddedChunk(DocumentChunk chunk, float[] embedding) {
            this.chunk = chunk;
            this.embedding = embedding;
            this.norm = computeNorm(embedding);
        }

        private static double computeNorm(float[] v) {
            double sum = 0.0;
            for (float val : v) {
                sum += val * val;
            }
            return Math.sqrt(sum);
        }
    }

    private final Map<String, List<EmbeddedChunk>> store = new ConcurrentHashMap<>();

    @Override
    public void store(String documentId, List<DocumentChunk> chunks, List<float[]> embeddings) {
        if (chunks.size() != embeddings.size()) {
            throw new IllegalArgumentException("Mismatch between chunks count and embeddings count.");
        }

        List<EmbeddedChunk> list = new ArrayList<>(chunks.size());
        for (int i = 0; i < chunks.size(); i++) {
            list.add(new EmbeddedChunk(chunks.get(i), embeddings.get(i)));
        }

        store.put(documentId, list);
        log.info("Stored {} chunks for document '{}' in memory vector store.", chunks.size(), documentId);
    }

    @Override
    public List<ScoredChunk> query(String documentId, float[] queryEmbedding, int topK) {
        List<EmbeddedChunk> docChunks = store.get(documentId);
        if (docChunks == null || docChunks.isEmpty()) {
            log.warn("No chunks found in memory vector store for document '{}'", documentId);
            return Collections.emptyList();
        }

        double queryNorm = 0.0;
        for (float v : queryEmbedding) {
            queryNorm += v * v;
        }
        queryNorm = Math.sqrt(queryNorm);

        if (queryNorm == 0.0) {
            return Collections.emptyList();
        }

        final double qNorm = queryNorm;
        return docChunks.stream()
                .map(ec -> {
                    double similarity = cosineSimilarity(queryEmbedding, qNorm, ec.embedding, ec.norm);
                    return new ScoredChunk(ec.chunk, similarity);
                })
                .sorted(Comparator.comparingDouble(ScoredChunk::getScore).reversed())
                .limit(topK)
                .collect(Collectors.toList());
    }

    private double cosineSimilarity(float[] a, double normA, float[] b, double normB) {
        if (normA == 0.0 || normB == 0.0) return 0.0;
        int len = Math.min(a.length, b.length);
        double dot = 0.0;
        for (int i = 0; i < len; i++) {
            dot += a[i] * b[i];
        }
        return dot / (normA * normB);
    }

    @Override
    public void delete(String documentId) {
        store.remove(documentId);
    }

    @Override
    public boolean isAvailable() {
        return true;
    }

    @Override
    public String getStoreType() {
        return "IN_MEMORY";
    }
}
