package com.docquery.model;

public class Citation {
    private int startPage;
    private int endPage;
    private String pageDisplay;
    private int chunkIndex;
    private String snippet;
    private double relevanceScore;

    public Citation() {}

    public Citation(int startPage, int endPage, String pageDisplay, int chunkIndex, String snippet, double relevanceScore) {
        this.startPage = startPage;
        this.endPage = endPage;
        this.pageDisplay = pageDisplay;
        this.chunkIndex = chunkIndex;
        this.snippet = snippet;
        this.relevanceScore = relevanceScore;
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

    public String getPageDisplay() {
        return pageDisplay;
    }

    public void setPageDisplay(String pageDisplay) {
        this.pageDisplay = pageDisplay;
    }

    public int getChunkIndex() {
        return chunkIndex;
    }

    public void setChunkIndex(int chunkIndex) {
        this.chunkIndex = chunkIndex;
    }

    public String getSnippet() {
        return snippet;
    }

    public void setSnippet(String snippet) {
        this.snippet = snippet;
    }

    public double getRelevanceScore() {
        return relevanceScore;
    }

    public void setRelevanceScore(double relevanceScore) {
        this.relevanceScore = relevanceScore;
    }
}
