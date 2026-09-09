package com.docquery.model;

import java.time.Instant;

public class UploadResponse {
    private String documentId;
    private String fileName;
    private long fileSize;
    private String fileType;
    private int pageCount;
    private int totalChunks;
    private String message;
    private Instant uploadedAt;

    public UploadResponse() {}

    public UploadResponse(String documentId, String fileName, long fileSize, String fileType, int pageCount, int totalChunks, String message) {
        this.documentId = documentId;
        this.fileName = fileName;
        this.fileSize = fileSize;
        this.fileType = fileType;
        this.pageCount = pageCount;
        this.totalChunks = totalChunks;
        this.message = message;
        this.uploadedAt = Instant.now();
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

    public int getTotalChunks() {
        return totalChunks;
    }

    public void setTotalChunks(int totalChunks) {
        this.totalChunks = totalChunks;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Instant getUploadedAt() {
        return uploadedAt;
    }

    public void setUploadedAt(Instant uploadedAt) {
        this.uploadedAt = uploadedAt;
    }
}
