package com.docquery.service.parser;

import com.docquery.model.PageText;
import com.docquery.model.ParsedDocument;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

@Component
public class PdfDocumentParser implements DocumentParser {

    private static final Logger log = LoggerFactory.getLogger(PdfDocumentParser.class);

    @Override
    public boolean supports(String fileName, String contentType) {
        if (fileName != null && fileName.toLowerCase().endsWith(".pdf")) {
            return true;
        }
        return contentType != null && contentType.equalsIgnoreCase("application/pdf");
    }

    @Override
    public ParsedDocument parse(InputStream inputStream, String fileName) throws IOException {
        byte[] bytes = inputStream.readAllBytes();
        try (PDDocument document = Loader.loadPDF(bytes)) {
            int pageCount = document.getNumberOfPages();
            log.info("Parsing PDF '{}' with {} pages", fileName, pageCount);

            PDFTextStripper stripper = new PDFTextStripper();
            List<PageText> pages = new ArrayList<>();

            for (int page = 1; page <= pageCount; page++) {
                stripper.setStartPage(page);
                stripper.setEndPage(page);
                String pageText = stripper.getText(document);
                if (pageText != null) {
                    pageText = pageText.trim();
                }
                pages.add(new PageText(page, pageText != null ? pageText : ""));
            }

            return new ParsedDocument(fileName, pageCount, pages);
        }
    }
}
