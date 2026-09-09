package com.docquery.service.vector;

import com.docquery.model.DocumentChunk;
import com.docquery.model.ScoredChunk;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Service
public class ChromaVectorStoreService implements VectorStoreService {

    private static final Logger log = LoggerFactory.getLogger(ChromaVectorStoreService.class);

    @Value("${chroma.url:http://localhost:8000}")
    private String chromaUrl;

    @Value("${chroma.collection:docquery_docs}")
    private String collectionName;

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private String cachedCollectionId = null;

    public ChromaVectorStoreService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(4))
                .build();
    }

    @Override
    public boolean isAvailable() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(chromaUrl + "/api/v1/heartbeat"))
                    .timeout(Duration.ofSeconds(3))
                    .GET()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            return response.statusCode() == 200;
        } catch (Exception e) {
            log.debug("ChromaDB is not reachable at {}: {}", chromaUrl, e.getMessage());
            return false;
        }
    }

    private synchronized String getOrCreateCollectionId() throws Exception {
        if (cachedCollectionId != null) {
            return cachedCollectionId;
        }

        // Try getting existing collection
        try {
            HttpRequest getReq = HttpRequest.newBuilder()
                    .uri(URI.create(chromaUrl + "/api/v1/collections/" + collectionName))
                    .timeout(Duration.ofSeconds(5))
                    .GET()
                    .build();
            HttpResponse<String> getRes = httpClient.send(getReq, HttpResponse.BodyHandlers.ofString());
            if (getRes.statusCode() == 200) {
                JsonNode node = objectMapper.readTree(getRes.body());
                cachedCollectionId = node.path("id").asText();
                return cachedCollectionId;
            }
        } catch (Exception ignored) {}

        // Create collection if not found
        ObjectNode createBody = objectMapper.createObjectNode();
        createBody.put("name", collectionName);
        ObjectNode meta = createBody.putObject("metadata");
        meta.put("hnsw:space", "cosine");

        HttpRequest createReq = HttpRequest.newBuilder()
                .uri(URI.create(chromaUrl + "/api/v1/collections"))
                .timeout(Duration.ofSeconds(5))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(createBody), StandardCharsets.UTF_8))
                .build();

        HttpResponse<String> createRes = httpClient.send(createReq, HttpResponse.BodyHandlers.ofString());
        if (createRes.statusCode() == 200 || createRes.statusCode() == 201) {
            JsonNode node = objectMapper.readTree(createRes.body());
            cachedCollectionId = node.path("id").asText();
            log.info("Created ChromaDB collection '{}' with ID: {}", collectionName, cachedCollectionId);
            return cachedCollectionId;
        } else {
            throw new RuntimeException("Failed to create ChromaDB collection: " + createRes.body());
        }
    }

    @Override
    public void store(String documentId, List<DocumentChunk> chunks, List<float[]> embeddings) {
        if (chunks.isEmpty()) return;

        try {
            String colId = getOrCreateCollectionId();
            String url = chromaUrl + "/api/v1/collections/" + colId + "/add";

            ObjectNode root = objectMapper.createObjectNode();
            ArrayNode idsNode = root.putArray("ids");
            ArrayNode docsNode = root.putArray("documents");
            ArrayNode metaNode = root.putArray("metadatas");
            ArrayNode embNode = root.putArray("embeddings");

            for (int i = 0; i < chunks.size(); i++) {
                DocumentChunk c = chunks.get(i);
                idsNode.add(c.getId());
                docsNode.add(c.getContent());

                ObjectNode m = metaNode.addObject();
                m.put("documentId", c.getDocumentId());
                m.put("chunkIndex", c.getChunkIndex());
                m.put("startPage", c.getStartPage());
                m.put("endPage", c.getEndPage());
                m.put("wordCount", c.getWordCount());

                ArrayNode singleEmb = embNode.addArray();
                for (float v : embeddings.get(i)) {
                    singleEmb.add(v);
                }
            }

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .timeout(Duration.ofSeconds(30))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(root), StandardCharsets.UTF_8))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200 && response.statusCode() != 201) {
                throw new RuntimeException("ChromaDB /add error (" + response.statusCode() + "): " + response.body());
            }

            log.info("Successfully stored {} chunks in ChromaDB collection '{}'", chunks.size(), collectionName);
        } catch (Exception e) {
            log.error("Failed to store chunks in ChromaDB: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }

    @Override
    public List<ScoredChunk> query(String documentId, float[] queryEmbedding, int topK) {
        try {
            String colId = getOrCreateCollectionId();
            String url = chromaUrl + "/api/v1/collections/" + colId + "/query";

            ObjectNode root = objectMapper.createObjectNode();
            ArrayNode qEmbArray = root.putArray("query_embeddings");
            ArrayNode firstEmb = qEmbArray.addArray();
            for (float v : queryEmbedding) {
                firstEmb.add(v);
            }

            root.put("n_results", topK);

            ObjectNode where = root.putObject("where");
            where.put("documentId", documentId);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .timeout(Duration.ofSeconds(15))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(root), StandardCharsets.UTF_8))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                throw new RuntimeException("ChromaDB /query error (" + response.statusCode() + "): " + response.body());
            }

            JsonNode resNode = objectMapper.readTree(response.body());
            List<ScoredChunk> results = new ArrayList<>();

            JsonNode idsArray = resNode.path("ids").path(0);
            JsonNode distancesArray = resNode.path("distances").path(0);
            JsonNode metadatasArray = resNode.path("metadatas").path(0);
            JsonNode documentsArray = resNode.path("documents").path(0);

            if (idsArray.isArray()) {
                for (int i = 0; i < idsArray.size(); i++) {
                    String id = idsArray.get(i).asText();
                    double distance = distancesArray.get(i).asDouble();
                    JsonNode meta = metadatasArray.get(i);
                    String content = documentsArray.get(i).asText();

                    int startPage = meta.path("startPage").asInt(1);
                    int endPage = meta.path("endPage").asInt(1);
                    int chunkIndex = meta.path("chunkIndex").asInt(0);
                    int wordCount = meta.path("wordCount").asInt(0);

                    DocumentChunk chunk = new DocumentChunk(
                            id,
                            documentId,
                            chunkIndex,
                            startPage,
                            endPage,
                            content,
                            wordCount
                    );

                    // Cosine distance in Chroma: dist = 1 - cosine_sim -> sim = 1 - dist
                    double similarity = Math.max(0.0, Math.min(1.0, 1.0 - distance));
                    results.add(new ScoredChunk(chunk, similarity));
                }
            }

            return results;
        } catch (Exception e) {
            log.error("Failed to query ChromaDB: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }

    @Override
    public void delete(String documentId) {
        try {
            String colId = getOrCreateCollectionId();
            String url = chromaUrl + "/api/v1/collections/" + colId + "/delete";

            ObjectNode root = objectMapper.createObjectNode();
            ObjectNode where = root.putObject("where");
            where.put("documentId", documentId);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .timeout(Duration.ofSeconds(10))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(root), StandardCharsets.UTF_8))
                    .build();

            httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            log.info("Deleted chunks for document '{}' from ChromaDB", documentId);
        } catch (Exception e) {
            log.warn("Failed to delete chunks from ChromaDB: {}", e.getMessage());
        }
    }

    @Override
    public String getStoreType() {
        return "CHROMADB";
    }
}
