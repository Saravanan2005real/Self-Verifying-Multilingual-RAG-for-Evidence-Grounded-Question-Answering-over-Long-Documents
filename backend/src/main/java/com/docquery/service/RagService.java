package com.docquery.service;

import com.docquery.model.*;
import com.docquery.service.chunking.TextChunker;
import com.docquery.service.gemini.GeminiApiClient;
import com.docquery.service.parser.DocumentParserService;
import com.docquery.service.vector.VectorStoreService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Service
public class RagService {

    private static final Logger log = LoggerFactory.getLogger(RagService.class);
    private static final String NOT_FOUND_RESPONSE = "I couldn't find this information in the uploaded document.";

    private final DocumentParserService parserService;
    private final TextChunker textChunker;
    private final GeminiApiClient geminiApiClient;
    private final VectorStoreService vectorStoreService;

    // Document context caches
    private final Map<String, DocumentMetadata> documentRegistry = new ConcurrentHashMap<>();
    private final Map<String, List<DocumentChunk>> chunksRegistry = new ConcurrentHashMap<>();
    private final Map<String, ParsedDocument> parsedDocRegistry = new ConcurrentHashMap<>();

    private static final Set<String> STOP_WORDS = Set.of(
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
            "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
            "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing",
            "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
            "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
            "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
            "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
            "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
            "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
            "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
            "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
            "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd",
            "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
            "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you",
            "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves", "tell", "show", "give", "find"
    );

    public RagService(DocumentParserService parserService,
                      TextChunker textChunker,
                      GeminiApiClient geminiApiClient,
                      VectorStoreService vectorStoreService) {
        this.parserService = parserService;
        this.textChunker = textChunker;
        this.geminiApiClient = geminiApiClient;
        this.vectorStoreService = vectorStoreService;
    }

    /**
     * Upload and parse PDF or DOCX file (No external API needed).
     */
    public UploadResponse processUpload(MultipartFile file) throws Exception {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("Upload error: File is empty or not provided.");
        }

        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null) {
            originalFilename = "document";
        }

        long size = file.getSize();
        if (size > 30 * 1024 * 1024) {
            throw new IllegalArgumentException("File size exceeds 30MB limit: " + (size / (1024 * 1024)) + "MB");
        }

        String contentType = file.getContentType();
        if (!parserService.isSupported(originalFilename, contentType)) {
            throw new IllegalArgumentException("Unsupported file type for '" + originalFilename +
                    "'. Please upload a .pdf or .docx file.");
        }

        String documentId = "doc_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        log.info("Processing upload '{}' ({}) with ID: {}", originalFilename, contentType, documentId);

        // 1. Parse document into pages (PDFBox / POI)
        ParsedDocument parsedDoc;
        try (InputStream is = file.getInputStream()) {
            parsedDoc = parserService.parse(is, originalFilename, contentType);
        }

        // 2. Chunk text (~500 words with overlap)
        List<DocumentChunk> chunks = textChunker.chunkDocument(documentId, parsedDoc);
        if (chunks.isEmpty()) {
            throw new IllegalStateException("Could not extract any readable text from '" + originalFilename + "'.");
        }

        // 3. Store in local registries (instant, no external API required)
        chunksRegistry.put(documentId, chunks);
        parsedDocRegistry.put(documentId, parsedDoc);

        // If Gemini API key is configured, optionally generate embeddings in the background
        if (geminiApiClient.hasApiKey()) {
            try {
                List<String> chunkTexts = chunks.stream().map(DocumentChunk::getContent).toList();
                List<float[]> embeddings = geminiApiClient.batchEmbedTexts(chunkTexts);
                vectorStoreService.store(documentId, chunks, embeddings);
            } catch (Exception e) {
                log.warn("Gemini embedding skipped, using local search engine: {}", e.getMessage());
            }
        }

        // 4. Save metadata
        DocumentMetadata metadata = new DocumentMetadata(
                documentId,
                originalFilename,
                size,
                contentType != null ? contentType : "application/octet-stream",
                parsedDoc.getPageCount(),
                chunks.size(),
                Instant.now()
        );
        documentRegistry.put(documentId, metadata);

        log.info("Indexed document '{}' ({} pages, {} chunks). Ready for local query.", originalFilename, parsedDoc.getPageCount(), chunks.size());

        return new UploadResponse(
                documentId,
                originalFilename,
                size,
                metadata.getFileType(),
                parsedDoc.getPageCount(),
                chunks.size(),
                "Document parsed and indexed successfully. Ready to answer questions!"
        );
    }

    /**
     * Local & Fast RAG Query Engine (No external API required).
     */
    public ChatResponse chat(ChatRequest request) throws Exception {
        validateChatRequest(request);

        String documentId = request.getDocumentId();
        String question = request.getQuestion().trim();

        // If Gemini API key is configured, use Gemini RAG
        if (geminiApiClient.hasApiKey()) {
            try {
                return executeGeminiChat(request);
            } catch (Exception e) {
                log.warn("Gemini API call failed, falling back to local RAG engine: {}", e.getMessage());
            }
        }

        // Local Document Question-Answering
        return executeLocalRag(documentId, question);
    }

    /**
     * Streaming Chat (Works locally or via Gemini).
     */
    public void streamChat(ChatRequest request,
                           Consumer<String> tokenConsumer,
                           Consumer<List<Citation>> citationConsumer) throws Exception {
        validateChatRequest(request);

        String documentId = request.getDocumentId();
        String question = request.getQuestion().trim();

        if (geminiApiClient.hasApiKey()) {
            try {
                executeGeminiStreamChat(request, tokenConsumer, citationConsumer);
                return;
            } catch (Exception e) {
                log.warn("Gemini streaming failed, falling back to local RAG engine: {}", e.getMessage());
            }
        }

        // Local RAG response with realistic streaming simulation
        ChatResponse localResponse = executeLocalRag(documentId, question);
        streamTextTokens(localResponse.getAnswer(), tokenConsumer);
        citationConsumer.accept(localResponse.getCitations());
    }

    private void streamTextTokens(String text, Consumer<String> tokenConsumer) {
        if (text == null || text.isBlank()) {
            tokenConsumer.accept(NOT_FOUND_RESPONSE);
            return;
        }

        String[] tokens = text.split("(?<=\\s)|(?<=[.!?\n])");
        for (String token : tokens) {
            tokenConsumer.accept(token);
            try {
                Thread.sleep(12); // subtle, realistic typing effect
            } catch (InterruptedException ignored) {}
        }
    }

    /**
     * High-accuracy Local Document Search and Synthesis Engine.
     */
    private ChatResponse executeLocalRag(String documentId, String question) {
        List<DocumentChunk> chunks = chunksRegistry.get(documentId);
        ParsedDocument doc = parsedDocRegistry.get(documentId);

        if (chunks == null || chunks.isEmpty()) {
            return new ChatResponse(NOT_FOUND_RESPONSE, Collections.emptyList(), documentId);
        }

        String lowerQuestion = question.toLowerCase();

        // 1. Check if user is asking for a summary
        if (isSummaryRequest(lowerQuestion)) {
            return generateDocumentSummary(doc, chunks, documentId);
        }

        // 2. Tokenize question into keywords
        Set<String> keywords = extractKeywords(lowerQuestion);
        if (keywords.isEmpty()) {
            return new ChatResponse(NOT_FOUND_RESPONSE, Collections.emptyList(), documentId);
        }

        // 3. Search and score sentences across the document
        List<ScoredSentence> scoredSentences = new ArrayList<>();
        for (DocumentChunk chunk : chunks) {
            String[] sentences = chunk.getContent().split("(?<=[.!?])\\s+|(?<=\n)");
            for (String sentence : sentences) {
                String clean = sentence.trim();
                if (clean.length() < 10) continue;

                double score = scoreSentence(clean, keywords, lowerQuestion);
                if (score > 0) {
                    scoredSentences.add(new ScoredSentence(clean, chunk.getStartPage(), chunk.getEndPage(), chunk.getChunkIndex(), score));
                }
            }
        }

        // If no relevant sentences match
        if (scoredSentences.isEmpty()) {
            return new ChatResponse(NOT_FOUND_RESPONSE, Collections.emptyList(), documentId);
        }

        // Sort by relevance score descending
        scoredSentences.sort(Comparator.comparingDouble(ScoredSentence::score).reversed());

        // Deduplicate and select top 3-4 distinct sentences
        List<ScoredSentence> topSentences = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (ScoredSentence s : scoredSentences) {
            String snippetKey = s.sentence.toLowerCase().replaceAll("[^a-z0-9]", "");
            if (seen.add(snippetKey)) {
                topSentences.add(s);
                if (topSentences.size() >= 3) break;
            }
        }

        // 4. Formulate answer and citations
        StringBuilder answerBuilder = new StringBuilder();
        List<Citation> citations = new ArrayList<>();

        ScoredSentence primary = topSentences.get(0);
        String pageRef = primary.startPage == primary.endPage ? "Page " + primary.startPage : "Pages " + primary.startPage + "-" + primary.endPage;

        answerBuilder.append(String.format("Based on [%s] of the document:\n\n", pageRef));

        for (int i = 0; i < topSentences.size(); i++) {
            ScoredSentence s = topSentences.get(i);
            String itemPage = s.startPage == s.endPage ? "Page " + s.startPage : "Pages " + s.startPage + "-" + s.endPage;

            answerBuilder.append(String.format("- **[%s]** %s\n", itemPage, s.sentence));

            // Add citation
            citations.add(new Citation(
                    s.startPage,
                    s.endPage,
                    itemPage,
                    s.chunkIndex,
                    s.sentence,
                    Math.round(s.score * 100.0) / 100.0
            ));
        }

        return new ChatResponse(answerBuilder.toString().trim(), citations, documentId);
    }

    private boolean isSummaryRequest(String query) {
        return query.contains("summarize") || query.contains("summary") ||
                query.contains("overview") || query.contains("main point") ||
                query.contains("key takeaway") || query.contains("what is this document about");
    }

    private ChatResponse generateDocumentSummary(ParsedDocument doc, List<DocumentChunk> chunks, String documentId) {
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("### Document Summary: **%s**\n\n", doc.getFileName()));
        sb.append(String.format("This document contains **%d pages** and **%d sections**.\n\n", doc.getPageCount(), chunks.size()));

        List<Citation> citations = new ArrayList<>();

        for (int i = 0; i < Math.min(doc.getPages().size(), 4); i++) {
            PageText page = doc.getPages().get(i);
            String text = page.getText().trim();
            if (text.isEmpty()) continue;

            String[] lines = text.split("\n+");
            String highlight = "";
            for (String line : lines) {
                if (line.trim().length() > 20) {
                    highlight = line.trim();
                    break;
                }
            }
            if (highlight.isEmpty() && lines.length > 0) highlight = lines[0].trim();

            if (!highlight.isEmpty()) {
                sb.append(String.format("- **Page %d**: %s\n", page.getPageNumber(), highlight));
                citations.add(new Citation(page.getPageNumber(), page.getPageNumber(), "Page " + page.getPageNumber(), i, highlight, 0.95));
            }
        }

        sb.append("\n*You can ask specific questions about rules, numbers, dates, or policies mentioned above!*");

        return new ChatResponse(sb.toString(), citations, documentId);
    }

    private Set<String> extractKeywords(String text) {
        Set<String> keywords = new HashSet<>();
        Matcher matcher = Pattern.compile("[a-zA-Z0-9]+").matcher(text);
        while (matcher.find()) {
            String word = matcher.group().toLowerCase();
            if (word.length() > 2 && !STOP_WORDS.contains(word)) {
                keywords.add(word);
            }
        }
        return keywords;
    }

    private double scoreSentence(String sentence, Set<String> keywords, String rawQuery) {
        String lower = sentence.toLowerCase();
        double score = 0;
        int matched = 0;

        for (String kw : keywords) {
            if (lower.contains(kw)) {
                matched++;
                score += 1.0;
                // bonus for whole word match
                if (Pattern.compile("\\b" + Pattern.quote(kw) + "\\b").matcher(lower).find()) {
                    score += 0.5;
                }
            }
        }

        // Exact phrase match bonus
        if (rawQuery.length() > 6 && lower.contains(rawQuery)) {
            score += 3.0;
        }

        if (matched == 0) return 0.0;
        return score / Math.max(1, keywords.size());
    }

    private record ScoredSentence(String sentence, int startPage, int endPage, int chunkIndex, double score) {}

    private void validateChatRequest(ChatRequest request) {
        if (request == null) {
            throw new IllegalArgumentException("Chat request body cannot be null.");
        }
        if (request.getDocumentId() == null || request.getDocumentId().isBlank()) {
            throw new IllegalArgumentException("Document ID is required. Please upload a document first.");
        }
        if (request.getQuestion() == null || request.getQuestion().isBlank()) {
            throw new IllegalArgumentException("Question cannot be empty.");
        }
    }

    private ChatResponse executeGeminiChat(ChatRequest request) throws Exception {
        String documentId = request.getDocumentId();
        String question = request.getQuestion().trim();
        float[] queryEmbedding = geminiApiClient.embedText(question);
        List<ScoredChunk> scoredChunks = vectorStoreService.query(documentId, queryEmbedding, 4);

        if (scoredChunks.isEmpty()) {
            return new ChatResponse(NOT_FOUND_RESPONSE, Collections.emptyList(), documentId);
        }

        List<Citation> citations = scoredChunks.stream().map(sc -> {
            DocumentChunk c = sc.getChunk();
            String snip = c.getContent().length() > 220 ? c.getContent().substring(0, 217) + "..." : c.getContent();
            return new Citation(c.getStartPage(), c.getEndPage(), c.getPageDisplay(), c.getChunkIndex(), snip, Math.round(sc.getScore() * 1000.0) / 1000.0);
        }).toList();

        String answer = geminiApiClient.generateContent(
                "Answer based strictly on the excerpts. Cite [Page X]. If not found: 'I couldn't find this information in the uploaded document.'",
                "Context:\n" + scoredChunks.stream().map(s -> s.getChunk().getContent()).collect(Collectors.joining("\n---\n")) + "\n\nQuestion: " + question
        );

        return new ChatResponse(answer, citations, documentId);
    }

    private void executeGeminiStreamChat(ChatRequest request, Consumer<String> tokenConsumer, Consumer<List<Citation>> citationConsumer) throws Exception {
        String documentId = request.getDocumentId();
        String question = request.getQuestion().trim();
        float[] queryEmbedding = geminiApiClient.embedText(question);
        List<ScoredChunk> scoredChunks = vectorStoreService.query(documentId, queryEmbedding, 4);

        if (scoredChunks.isEmpty()) {
            tokenConsumer.accept(NOT_FOUND_RESPONSE);
            citationConsumer.accept(Collections.emptyList());
            return;
        }

        List<Citation> citations = scoredChunks.stream().map(sc -> {
            DocumentChunk c = sc.getChunk();
            String snip = c.getContent().length() > 220 ? c.getContent().substring(0, 217) + "..." : c.getContent();
            return new Citation(c.getStartPage(), c.getEndPage(), c.getPageDisplay(), c.getChunkIndex(), snip, Math.round(sc.getScore() * 1000.0) / 1000.0);
        }).toList();

        geminiApiClient.streamGenerateContent(
                "Answer based strictly on the excerpts. Cite [Page X]. If not found: 'I couldn't find this information in the uploaded document.'",
                "Context:\n" + scoredChunks.stream().map(s -> s.getChunk().getContent()).collect(Collectors.joining("\n---\n")) + "\n\nQuestion: " + question,
                tokenConsumer
        );
        citationConsumer.accept(citations);
    }

    public DocumentMetadata getDocumentMetadata(String documentId) {
        return documentRegistry.get(documentId);
    }

    public List<DocumentMetadata> getAllDocuments() {
        return new ArrayList<>(documentRegistry.values());
    }
}
