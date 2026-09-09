package com.docquery.service.gemini;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

@Service
public class GeminiApiClient {

    private static final Logger log = LoggerFactory.getLogger(GeminiApiClient.class);
    private static final String BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/";

    @Value("${gemini.api.key:}")
    private String apiKey;

    @Value("${gemini.embedding.model:text-embedding-004}")
    private String embeddingModel;

    @Value("${gemini.chat.model:gemini-1.5-flash}")
    private String chatModel;

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    public GeminiApiClient(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_2)
                .connectTimeout(Duration.ofSeconds(20))
                .build();
    }

    public void setApiKey(String key) {
        this.apiKey = key;
    }

    public String getApiKey() {
        return this.apiKey;
    }

    public boolean hasApiKey() {
        return apiKey != null && !apiKey.trim().isEmpty();
    }

    private String getEffectiveKey() {
        if (!hasApiKey()) {
            // Check system environment variable dynamically as fallback
            String envKey = System.getenv("GEMINI_API_KEY");
            if (envKey != null && !envKey.trim().isEmpty()) {
                return envKey.trim();
            }
            throw new IllegalStateException("Gemini API key is not configured. Please set GEMINI_API_KEY in application.properties, environment variables, or through the UI.");
        }
        return apiKey.trim();
    }

    /**
     * Embed a single text string (e.g. user question).
     */
    public float[] embedText(String text) throws Exception {
        String key = getEffectiveKey();
        String url = BASE_URL + embeddingModel + ":embedContent?key=" + key;

        ObjectNode root = objectMapper.createObjectNode();
        root.put("model", "models/" + embeddingModel);
        ObjectNode contentNode = root.putObject("content");
        ArrayNode partsArray = contentNode.putArray("parts");
        partsArray.addObject().put("text", text);

        String requestJson = objectMapper.writeValueAsString(root);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofSeconds(30))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestJson, StandardCharsets.UTF_8))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            log.error("Gemini embedding error: HTTP {} - {}", response.statusCode(), response.body());
            throw new RuntimeException("Gemini Embedding API failed: " + parseErrorMessage(response.body(), response.statusCode()));
        }

        JsonNode resNode = objectMapper.readTree(response.body());
        JsonNode valuesNode = resNode.path("embedding").path("values");
        if (valuesNode.isMissingNode() || !valuesNode.isArray()) {
            throw new RuntimeException("Unexpected response from Gemini Embedding API: " + response.body());
        }

        float[] embedding = new float[valuesNode.size()];
        for (int i = 0; i < valuesNode.size(); i++) {
            embedding[i] = (float) valuesNode.get(i).asDouble();
        }
        return embedding;
    }

    /**
     * Batch embed a list of texts (chunks).
     */
    public List<float[]> batchEmbedTexts(List<String> texts) throws Exception {
        List<float[]> results = new ArrayList<>();
        if (texts == null || texts.isEmpty()) {
            return results;
        }

        String key = getEffectiveKey();
        int batchSize = 40; // Gemini supports up to 100 per batch; 40 is safe and fast

        for (int i = 0; i < texts.size(); i += batchSize) {
            int end = Math.min(i + batchSize, texts.size());
            List<String> subList = texts.subList(i, end);

            String url = BASE_URL + embeddingModel + ":batchEmbedContents?key=" + key;

            ObjectNode root = objectMapper.createObjectNode();
            ArrayNode requestsArray = root.putArray("requests");

            for (String text : subList) {
                ObjectNode item = requestsArray.addObject();
                item.put("model", "models/" + embeddingModel);
                ObjectNode content = item.putObject("content");
                ArrayNode parts = content.putArray("parts");
                parts.addObject().put("text", text);
            }

            String requestJson = objectMapper.writeValueAsString(root);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .timeout(Duration.ofSeconds(60))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(requestJson, StandardCharsets.UTF_8))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                log.error("Gemini batch embed error: HTTP {} - {}", response.statusCode(), response.body());
                throw new RuntimeException("Gemini Batch Embedding API failed: " + parseErrorMessage(response.body(), response.statusCode()));
            }

            JsonNode resNode = objectMapper.readTree(response.body());
            JsonNode embeddingsArray = resNode.path("embeddings");
            for (JsonNode embItem : embeddingsArray) {
                JsonNode vals = embItem.path("values");
                float[] emb = new float[vals.size()];
                for (int v = 0; v < vals.size(); v++) {
                    emb[v] = (float) vals.get(v).asDouble();
                }
                results.add(emb);
            }
        }

        return results;
    }

    /**
     * Generate content non-streaming.
     */
    public String generateContent(String systemInstruction, String prompt) throws Exception {
        String key = getEffectiveKey();
        String url = BASE_URL + chatModel + ":generateContent?key=" + key;

        String requestJson = buildChatRequestBody(systemInstruction, prompt);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofSeconds(60))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestJson, StandardCharsets.UTF_8))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            log.error("Gemini chat error: HTTP {} - {}", response.statusCode(), response.body());
            throw new RuntimeException("Gemini Generation API failed: " + parseErrorMessage(response.body(), response.statusCode()));
        }

        JsonNode resNode = objectMapper.readTree(response.body());
        return extractTextFromCandidates(resNode);
    }

    /**
     * Stream content generation via Server-Sent Events (SSE).
     */
    public void streamGenerateContent(String systemInstruction, String prompt, Consumer<String> tokenConsumer) throws Exception {
        String key = getEffectiveKey();
        String url = BASE_URL + chatModel + ":streamGenerateContent?alt=sse&key=" + key;

        String requestJson = buildChatRequestBody(systemInstruction, prompt);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofSeconds(90))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestJson, StandardCharsets.UTF_8))
                .build();

        HttpResponse<java.io.InputStream> response = httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());

        if (response.statusCode() != 200) {
            String errBody = new String(response.body().readAllBytes(), StandardCharsets.UTF_8);
            log.error("Gemini stream error: HTTP {} - {}", response.statusCode(), errBody);
            throw new RuntimeException("Gemini Streaming API failed: " + parseErrorMessage(errBody, response.statusCode()));
        }

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(response.body(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.startsWith("data: ")) {
                    String jsonChunk = line.substring(6).trim();
                    if (!jsonChunk.isEmpty()) {
                        try {
                            JsonNode node = objectMapper.readTree(jsonChunk);
                            String text = extractTextFromCandidates(node);
                            if (text != null && !text.isEmpty()) {
                                tokenConsumer.accept(text);
                            }
                        } catch (Exception e) {
                            log.debug("Error parsing SSE chunk: {}", jsonChunk);
                        }
                    }
                }
            }
        }
    }

    private String buildChatRequestBody(String systemInstruction, String prompt) throws Exception {
        ObjectNode root = objectMapper.createObjectNode();

        if (systemInstruction != null && !systemInstruction.isBlank()) {
            ObjectNode sysNode = root.putObject("systemInstruction");
            ArrayNode sysParts = sysNode.putArray("parts");
            sysParts.addObject().put("text", systemInstruction);
        }

        ArrayNode contents = root.putArray("contents");
        ObjectNode userMessage = contents.addObject();
        userMessage.put("role", "user");
        ArrayNode userParts = userMessage.putArray("parts");
        userParts.addObject().put("text", prompt);

        ObjectNode genConfig = root.putObject("generationConfig");
        genConfig.put("temperature", 0.2);
        genConfig.put("topK", 40);
        genConfig.put("topP", 0.95);

        return objectMapper.writeValueAsString(root);
    }

    private String extractTextFromCandidates(JsonNode node) {
        JsonNode candidates = node.path("candidates");
        if (candidates.isArray() && candidates.size() > 0) {
            JsonNode parts = candidates.get(0).path("content").path("parts");
            if (parts.isArray() && parts.size() > 0) {
                StringBuilder sb = new StringBuilder();
                for (JsonNode part : parts) {
                    if (part.has("text")) {
                        sb.append(part.get("text").asText());
                    }
                }
                return sb.toString();
            }
        }
        return "";
    }

    private String parseErrorMessage(String responseBody, int statusCode) {
        try {
            JsonNode node = objectMapper.readTree(responseBody);
            String message = node.path("error").path("message").asText();
            if (!message.isBlank()) {
                return message + " (HTTP " + statusCode + ")";
            }
        } catch (Exception ignored) {}
        return "HTTP status " + statusCode + ": " + responseBody;
    }
}
