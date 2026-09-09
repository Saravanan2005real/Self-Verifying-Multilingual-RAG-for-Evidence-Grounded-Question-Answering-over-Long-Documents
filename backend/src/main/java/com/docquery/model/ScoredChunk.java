package com.docquery.model;

public class ScoredChunk {
    private DocumentChunk chunk;
    private double score;

    public ScoredChunk() {}

    public ScoredChunk(DocumentChunk chunk, double score) {
        this.chunk = chunk;
        this.score = score;
    }

    public DocumentChunk getChunk() {
        return chunk;
    }

    public void setChunk(DocumentChunk chunk) {
        this.chunk = chunk;
    }

    public double getScore() {
        return score;
    }

    public void setScore(double score) {
        this.score = score;
    }
}
