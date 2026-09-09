package com.docquery.model;

import java.time.Instant;

public class DocumentMetadata {
    private String documentId;
    private String fileName;
    private long fileSize;
    private String fileType;
    private int pageCount;
    private int chunkCount;
    private Instant uploadedAt;

    public DocumentMetadata() {}

    public DocumentMetadata(String documentId, String fileName, long fileSize, String fileType, int pageCount, int chunkCount, Instant uploadedAt) {
        this.documentId = documentId;
        this.fileName = fileName;
        this.fileSize = fileSize;
        this.fileType = fileType;
        this.pageCount = pageCount;
        this.chunkCount = chunkCount;
        this.uploadedAt = uploadedAt;
    }

    public String getDocumentId() {
        return documentId;
    }

    public void setDocumentId(String documentId) {
        this.documentId = documentId;
    }

    public String getFileName() {
        return fileName;
    }

    public void setFileName(String fileName) {
        this.fileName = fileName;
    }

    public long getFileSize() {
        return fileSize;
    }

    public void setFileSize(long fileSize) {
        this.fileSize = fileSize;
    }

    public String getFileType() {
        return fileType;
    }

    public void setFileType(String fileType) {
        this.fileType = fileType;
    }

    public int getPageCount() {
        return pageCount;
    }

    public void setPageCount(int pageCount) {
        this.pageCount = pageCount;
    }

    public int getChunkCount() {
        return chunkCount;
    }

    public void setChunkCount(int chunkCount) {
        this.chunkCount = chunkCount;
    }

    public Instant getUploadedAt() {
        return uploadedAt;
    }

    public void setUploadedAt(Instant uploadedAt) {
        this.uploadedAt = uploadedAt;
    }
}
