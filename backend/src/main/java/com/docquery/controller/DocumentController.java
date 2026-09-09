package com.docquery.controller;

import com.docquery.model.*;
import com.docquery.service.RagService;
import com.docquery.service.gemini.GeminiApiClient;
import com.docquery.service.vector.VectorStoreService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@RestController
public class DocumentController {

    private static final Logger log = LoggerFactory.getLogger(DocumentController.class);

    private final RagService ragService;
    private final GeminiApiClient geminiApiClient;
    private final VectorStoreService vectorStoreService;
    private final ObjectMapper objectMapper;
    private final ExecutorService executorService = Executors.newCachedThreadPool();

    public DocumentController(RagService ragService,
                              GeminiApiClient geminiApiClient,
                              VectorStoreService vectorStoreService,
                              ObjectMapper objectMapper) {
        this.ragService = ragService;
        this.geminiApiClient = geminiApiClient;
        this.vectorStoreService = vectorStoreService;
        this.objectMapper = objectMapper;
    }

    /**
     * Upload document (PDF / DOCX)
     * Maps to both /upload and /api/upload
     */
    @PostMapping(value = {"/upload", "/api/upload"}, consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<UploadResponse> uploadFile(@RequestParam("file") MultipartFile file) throws Exception {
        log.info("Received file upload request: {}", file.getOriginalFilename());
        UploadResponse response = ragService.processUpload(file);
        return ResponseEntity.ok(response);
    }

    /**
     * Standard Non-Streaming Chat
     * Maps to both /chat and /api/chat
     */
    @PostMapping(value = {"/chat", "/api/chat"}, consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<ChatResponse> chat(@RequestBody ChatRequest request) throws Exception {
        log.info("Received chat query for document: {}", request.getDocumentId());
        ChatResponse response = ragService.chat(request);
        return ResponseEntity.ok(response);
    }

    /**
     * Streaming Chat via Server-Sent Events (SSE)
     */
    @PostMapping(value = "/api/chat/stream", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamChat(@RequestBody ChatRequest request) {
        log.info("Received streaming chat query for document: {}", request.getDocumentId());

        // 3-minute timeout for streaming
        SseEmitter emitter = new SseEmitter(180_000L);

        executorService.execute(() -> {
            try {
                ragService.streamChat(
                        request,
                        token -> {
                            try {
                                Map<String, String> data = Map.of("token", token);
                                emitter.send(SseEmitter.event()
                                        .name("token")
                                        .data(objectMapper.writeValueAsString(data)));
                            } catch (IOException e) {
                                log.debug("Error sending token to SSE client: {}", e.getMessage());
                            }
                        },
                        citations -> {
                            try {
                                emitter.send(SseEmitter.event()
                                        .name("citations")
                                        .data(objectMapper.writeValueAsString(citations)));
                                emitter.send(SseEmitter.event()
                                        .name("done")
                                        .data("[DONE]"));
                                emitter.complete();
                            } catch (IOException e) {
                                log.debug("Error sending citations to SSE client: {}", e.getMessage());
                                emitter.completeWithError(e);
                            }
                        }
                );
            } catch (Exception e) {
                log.error("Error during streaming chat: {}", e.getMessage());
                try {
                    Map<String, String> err = Map.of("error", e.getMessage());
                    emitter.send(SseEmitter.event().name("error").data(objectMapper.writeValueAsString(err)));
                    emitter.completeWithError(e);
                } catch (Exception ignored) {}
            }
        });

        return emitter;
    }

    /**
     * System status and configuration check
     */
    @GetMapping("/api/status")
    public ResponseEntity<Map<String, Object>> getStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("hasApiKey", true);
        status.put("mode", "Local Document Intelligence (Zero API Required)");
        status.put("vectorStoreType", "Local In-Memory Document Index");
        status.put("documentsCount", ragService.getAllDocuments().size());
        status.put("documents", ragService.getAllDocuments());
        return ResponseEntity.ok(status);
    }

    /**
     * Update Gemini API key at runtime if needed
     */
    @PostMapping("/api/config/key")
    public ResponseEntity<Map<String, String>> setApiKey(@RequestBody Map<String, String> body) {
        String key = body.get("apiKey");
        if (key != null && !key.trim().isEmpty()) {
            geminiApiClient.setApiKey(key.trim());
            return ResponseEntity.ok(Map.of("message", "API key configured successfully."));
        }
        return ResponseEntity.badRequest().body(Map.of("error", "API key cannot be empty."));
    }

    /**
     * Get metadata for specific document
     */
    @GetMapping("/api/documents/{id}")
    public ResponseEntity<?> getDocument(@PathVariable("id") String id) {
        DocumentMetadata meta = ragService.getDocumentMetadata(id);
        if (meta != null) {
            return ResponseEntity.ok(meta);
        }
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", "Document not found."));
    }

    /**
     * Global exception handler for clean error responses
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleBadRequest(IllegalArgumentException e) {
        log.warn("Bad request: {}", e.getMessage());
        return ResponseEntity.badRequest().body(Map.of("error", e.getMessage(), "status", 400));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGeneralError(Exception e) {
        log.error("Internal error processing request", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", e.getMessage() != null ? e.getMessage() : "Internal server error", "status", 500));
    }
}
