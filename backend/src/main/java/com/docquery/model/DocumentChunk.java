package com.docquery.model;

public class DocumentChunk {
    private String id;
    private String documentId;
    private int chunkIndex;
    private int startPage;
    private int endPage;
    private String content;
    private int wordCount;

    public DocumentChunk() {}

    public DocumentChunk(String id, String documentId, int chunkIndex, int startPage, int endPage, String content, int wordCount) {
        this.id = id;
        this.documentId = documentId;
        this.chunkIndex = chunkIndex;
        this.startPage = startPage;
        this.endPage = endPage;
        this.content = content;
        this.wordCount = wordCount;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getDocumentId() {
        return documentId;
    }

    public void setDocumentId(String documentId) {
        this.documentId = documentId;
    }

    public int getChunkIndex() {
        return chunkIndex;
    }

    public void setChunkIndex(int chunkIndex) {
        this.chunkIndex = chunkIndex;
    }

    public int getStartPage() {
        return startPage;
    }

    public void setStartPage(int startPage) {
        this.startPage = startPage;
    }

    public int getEndPage() {
        return endPage;
    }

    public void setEndPage(int endPage) {
        this.endPage = endPage;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public int getWordCount() {
        return wordCount;
    }

    public void setWordCount(int wordCount) {
        this.wordCount = wordCount;
    }

    public String getPageDisplay() {
        if (startPage == endPage) {
            return "Page " + startPage;
        } else {
            return "Pages " + startPage + "-" + endPage;
        }
    }
}
