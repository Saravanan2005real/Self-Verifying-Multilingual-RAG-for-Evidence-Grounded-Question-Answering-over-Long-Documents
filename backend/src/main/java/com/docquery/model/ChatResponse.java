package com.docquery.model;

import java.util.ArrayList;
import java.util.List;

public class ChatResponse {
    private String answer;
    private List<Citation> citations = new ArrayList<>();
    private String documentId;

    public ChatResponse() {}

    public ChatResponse(String answer, List<Citation> citations, String documentId) {
        this.answer = answer;
        this.citations = citations != null ? citations : new ArrayList<>();
        this.documentId = documentId;
    }

    public String getAnswer() {
        return answer;
    }

    public void setAnswer(String answer) {
        this.answer = answer;
    }

    public List<Citation> getCitations() {
        return citations;
    }

    public void setCitations(List<Citation> citations) {
        this.citations = citations;
    }

    public String getDocumentId() {
        return documentId;
    }

    public void setDocumentId(String documentId) {
        this.documentId = documentId;
    }
}
