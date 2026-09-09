package com.docquery.model;

import java.util.List;

public class ParsedDocument {
    private String fileName;
    private int pageCount;
    private List<PageText> pages;

    public ParsedDocument() {}

    public ParsedDocument(String fileName, int pageCount, List<PageText> pages) {
        this.fileName = fileName;
        this.pageCount = pageCount;
        this.pages = pages;
    }

    public String getFileName() {
        return fileName;
    }

    public void setFileName(String fileName) {
        this.fileName = fileName;
    }

    public int getPageCount() {
        return pageCount;
    }

    public void setPageCount(int pageCount) {
        this.pageCount = pageCount;
    }

    public List<PageText> getPages() {
        return pages;
    }

    public void setPages(List<PageText> pages) {
        this.pages = pages;
    }
}
