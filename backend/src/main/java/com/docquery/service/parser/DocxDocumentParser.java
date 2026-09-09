package com.docquery.service.parser;

import com.docquery.model.PageText;
import com.docquery.model.ParsedDocument;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFTable;
import org.apache.poi.xwpf.usermodel.XWPFTableCell;
import org.apache.poi.xwpf.usermodel.XWPFTableRow;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

@Component
public class DocxDocumentParser implements DocumentParser {

    private static final Logger log = LoggerFactory.getLogger(DocxDocumentParser.class);
    private static final int APPROX_WORDS_PER_PAGE = 350;

    @Override
    public boolean supports(String fileName, String contentType) {
        if (fileName != null) {
            String lower = fileName.toLowerCase();
            if (lower.endsWith(".docx") || lower.endsWith(".doc")) {
                return true;
            }
        }
        return contentType != null && (
                contentType.equalsIgnoreCase("application/vnd.openxmlformats-officedocument.wordprocessingml.document") ||
                contentType.equalsIgnoreCase("application/msword")
        );
    }

    @Override
    public ParsedDocument parse(InputStream inputStream, String fileName) throws IOException {
        try (XWPFDocument docx = new XWPFDocument(inputStream)) {
            List<String> textBlocks = new ArrayList<>();

            for (XWPFParagraph paragraph : docx.getParagraphs()) {
                String text = paragraph.getText();
                if (text != null && !text.isBlank()) {
                    textBlocks.add(text.trim());
                }
            }

            for (XWPFTable table : docx.getTables()) {
                StringBuilder tableText = new StringBuilder();
                for (XWPFTableRow row : table.getRows()) {
                    List<String> cellTexts = new ArrayList<>();
                    for (XWPFTableCell cell : row.getTableCells()) {
                        cellTexts.add(cell.getText().trim());
                    }
                    tableText.append(String.join(" | ", cellTexts)).append("\n");
                }
                if (!tableText.isEmpty()) {
                    textBlocks.add(tableText.toString().trim());
                }
            }

            // Group into logical pages
            List<PageText> pages = new ArrayList<>();
            StringBuilder currentPage = new StringBuilder();
            int currentWordCount = 0;
            int pageNum = 1;

            for (String block : textBlocks) {
                int wordsInBlock = countWords(block);
                if (currentWordCount + wordsInBlock > APPROX_WORDS_PER_PAGE && currentWordCount > 0) {
                    pages.add(new PageText(pageNum++, currentPage.toString().trim()));
                    currentPage = new StringBuilder();
                    currentWordCount = 0;
                }

                if (!currentPage.isEmpty()) {
                    currentPage.append("\n\n");
                }
                currentPage.append(block);
                currentWordCount += wordsInBlock;
            }

            if (!currentPage.isEmpty()) {
                pages.add(new PageText(pageNum, currentPage.toString().trim()));
            }

            if (pages.isEmpty()) {
                pages.add(new PageText(1, ""));
            }

            int pageCount = pages.size();
            log.info("Parsed DOCX '{}' into {} logical pages", fileName, pageCount);
            return new ParsedDocument(fileName, pageCount, pages);
        }
    }

    private int countWords(String text) {
        if (text == null || text.isBlank()) {
            return 0;
        }
        return text.trim().split("\\s+").length;
    }
}
