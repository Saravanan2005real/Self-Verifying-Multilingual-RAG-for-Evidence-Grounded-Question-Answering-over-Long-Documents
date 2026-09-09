package com.docquery;

import com.docquery.model.ParsedDocument;
import com.docquery.service.parser.DocxDocumentParser;
import com.docquery.service.parser.PdfDocumentParser;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.io.FileInputStream;

import static org.junit.jupiter.api.Assertions.*;

public class DocumentParserTest {

    @Test
    public void testParsePdfDocument() throws Exception {
        PdfDocumentParser parser = new PdfDocumentParser();
        File file = new File("../samples/acme_company_handbook.pdf");
        assertTrue(file.exists(), "Sample PDF file should exist");

        try (FileInputStream fis = new FileInputStream(file)) {
            ParsedDocument doc = parser.parse(fis, file.getName());
            assertNotNull(doc);
            assertEquals(2, doc.getPageCount(), "Should have exactly 2 pages");
            assertEquals(2, doc.getPages().size());

            // Check page 1 content
            String p1 = doc.getPages().get(0).getText();
            assertTrue(p1.contains("ACME Corporation"), "Page 1 should mention ACME Corporation");
            assertTrue(p1.contains("Remote Work Policy"), "Page 1 should mention Remote Work Policy");

            // Check page 2 content
            String p2 = doc.getPages().get(1).getText();
            assertTrue(p2.contains("Paid Time Off (PTO)"), "Page 2 should mention Paid Time Off");
            assertTrue(p2.contains("Parental Leave"), "Page 2 should mention Parental Leave");
        }
    }

    @Test
    public void testParseDocxDocument() throws Exception {
        DocxDocumentParser parser = new DocxDocumentParser();
        File file = new File("../samples/project_guidelines.docx");
        assertTrue(file.exists(), "Sample DOCX file should exist");

        try (FileInputStream fis = new FileInputStream(file)) {
            ParsedDocument doc = parser.parse(fis, file.getName());
            assertNotNull(doc);
            assertTrue(doc.getPageCount() >= 1, "Should have at least 1 page");

            String content = doc.getPages().get(0).getText();
            assertTrue(content.contains("Project Mercury"), "DOCX should contain Project Mercury");
            assertTrue(content.contains("Coding Standards"), "DOCX should contain Coding Standards");
            assertTrue(content.contains("Deployment Pipeline"), "DOCX should contain Deployment Pipeline");
        }
    }
}
