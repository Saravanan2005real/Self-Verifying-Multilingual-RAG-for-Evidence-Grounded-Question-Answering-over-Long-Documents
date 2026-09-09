package com.docquery;

import com.docquery.model.DocumentChunk;
import com.docquery.model.ScoredChunk;
import com.docquery.service.vector.InMemoryVectorStoreService;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class VectorStoreTest {

    @Test
    public void testVectorStoreCosineSimilarityRanking() {
        InMemoryVectorStoreService store = new InMemoryVectorStoreService();

        DocumentChunk c1 = new DocumentChunk("c1", "doc1", 0, 1, 1, "Apples and oranges are fruits", 5);
        DocumentChunk c2 = new DocumentChunk("c2", "doc1", 1, 2, 2, "Quantum computing and physics", 5);

        // Vector 1 is close to query [1.0, 0.0]
        float[] emb1 = new float[]{0.95f, 0.05f};
        // Vector 2 is orthogonal [0.0, 1.0]
        float[] emb2 = new float[]{0.05f, 0.95f};

        store.store("doc1", List.of(c1, c2), List.of(emb1, emb2));

        float[] query = new float[]{1.0f, 0.0f};
        List<ScoredChunk> results = store.query("doc1", query, 2);

        assertEquals(2, results.size());
        assertEquals("c1", results.get(0).getChunk().getId());
        assertTrue(results.get(0).getScore() > results.get(1).getScore());
    }
}
