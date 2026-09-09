package com.docquery.model;

import java.util.ArrayList;
import java.util.List;

public class ChatRequest {
    private String documentId;
    private String question;
    private List<ChatMessage> history = new ArrayList<>();
    private boolean stream = false;

    public ChatRequest() {}

    public ChatRequest(String documentId, String question, List<ChatMessage> history, boolean stream) {
        this.documentId = documentId;
        this.question = question;
        this.history = history != null ? history : new ArrayList<>();
        this.stream = stream;
    }

    public String getDocumentId() {
        return documentId;
    }

    public void setDocumentId(String documentId) {
        this.documentId = documentId;
    }

    public String getQuestion() {
        return question;
    }

    public void setQuestion(String question) {
        this.question = question;
    }

    public List<ChatMessage> getHistory() {
        return history;
    }

    public void setHistory(List<ChatMessage> history) {
        this.history = history;
    }

    public boolean isStream() {
        return stream;
    }

    public void setStream(boolean stream) {
        this.stream = stream;
    }
}
