package com.docquery;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.apache.pdfbox.pdmodel.font.Standard14Fonts;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.io.FileOutputStream;

public class SampleDocumentGenerator {

    @Test
    public void generateSampleDocuments() throws Exception {
        File outDir = new File("../samples");
        outDir.mkdirs();

        // 1. Generate Sample PDF
        File pdfFile = new File(outDir, "acme_company_handbook.pdf");
        try (PDDocument doc = new PDDocument()) {
            // Page 1
            PDPage page1 = new PDPage();
            doc.addPage(page1);
            try (PDPageContentStream cs = new PDPageContentStream(doc, page1)) {
                cs.beginText();
                cs.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA_BOLD), 16);
                cs.newLineAtOffset(50, 720);
                cs.showText("ACME Corporation - Employee Handbook (Page 1)");
                cs.newLineAtOffset(0, -30);

                cs.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA), 12);
                cs.showText("Section 1: Working Hours & Remote Work Policy");
                cs.newLineAtOffset(0, -20);
                cs.showText("Core working hours at ACME are between 10:00 AM and 4:00 PM EST.");
                cs.newLineAtOffset(0, -18);
                cs.showText("All employees are permitted up to 3 days of remote work per week.");
                cs.newLineAtOffset(0, -18);
                cs.showText("Requests for full-time remote work must be approved by the Department VP.");
                cs.newLineAtOffset(0, -30);

                cs.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA_BOLD), 12);
                cs.showText("Section 2: Health and Wellness Benefits");
                cs.newLineAtOffset(0, -20);
                cs.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA), 12);
                cs.showText("ACME provides comprehensive medical, dental, and vision insurance.");
                cs.newLineAtOffset(0, -18);
                cs.showText("A wellness stipend of $500 annually is available for gym memberships.");
                cs.endText();
            }

            // Page 2
            PDPage page2 = new PDPage();
            doc.addPage(page2);
            try (PDPageContentStream cs = new PDPageContentStream(doc, page2)) {
                cs.beginText();
                cs.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA_BOLD), 16);
                cs.newLineAtOffset(50, 720);
                cs.showText("ACME Corporation - Leave Policies (Page 2)");
                cs.newLineAtOffset(0, -30);

                cs.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA), 12);
                cs.showText("Section 3: Paid Time Off (PTO)");
                cs.newLineAtOffset(0, -20);
                cs.showText("Full-time employees receive 25 days of paid time off per calendar year.");
                cs.newLineAtOffset(0, -18);
                cs.showText("Up to 5 unused PTO days can be rolled over to the following year.");
                cs.newLineAtOffset(0, -18);
                cs.showText("PTO requests exceeding 5 consecutive days require 2 weeks advance notice.");
                cs.newLineAtOffset(0, -30);

                cs.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA_BOLD), 12);
                cs.showText("Section 4: Parental Leave");
                cs.newLineAtOffset(0, -20);
                cs.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA), 12);
                cs.showText("New parents are entitled to 16 weeks of fully paid parental leave.");
                cs.newLineAtOffset(0, -18);
                cs.showText("This policy applies equally to birth, adoption, or foster placements.");
                cs.endText();
            }

            doc.save(pdfFile);
            System.out.println("Generated sample PDF at: " + pdfFile.getAbsolutePath());
        }

        // 2. Generate Sample DOCX
        File docxFile = new File(outDir, "project_guidelines.docx");
        try (XWPFDocument docx = new XWPFDocument();
             FileOutputStream fos = new FileOutputStream(docxFile)) {

            XWPFParagraph title = docx.createParagraph();
            XWPFRun r1 = title.createRun();
            r1.setText("Project Mercury: Architecture & Engineering Guidelines");
            r1.setBold(true);
            r1.setFontSize(16);

            XWPFParagraph p1 = docx.createParagraph();
            XWPFRun r2 = p1.createRun();
            r2.setText("1. Coding Standards: All Java services must target Java 17 or higher and follow Clean Code conventions. Unit test coverage must exceed 80%.");

            XWPFParagraph p2 = docx.createParagraph();
            XWPFRun r3 = p2.createRun();
            r3.setText("2. Deployment Pipeline: Deployments occur automatically via GitHub Actions upon merging into the release branch. Production releases are scheduled every Tuesday at 14:00 UTC.");

            XWPFParagraph p3 = docx.createParagraph();
            XWPFRun r4 = p3.createRun();
            r4.setText("3. Security: All database credentials must be fetched from HashiCorp Vault. Hardcoding secrets in source files is strictly prohibited.");

            docx.write(fos);
            System.out.println("Generated sample DOCX at: " + docxFile.getAbsolutePath());
        }
    }
}
