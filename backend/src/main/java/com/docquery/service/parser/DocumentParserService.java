package com.docquery.service.parser;

import com.docquery.model.ParsedDocument;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.util.List;

@Service
public class DocumentParserService {

    private final List<DocumentParser> parsers;

    public DocumentParserService(List<DocumentParser> parsers) {
        this.parsers = parsers;
    }

    public ParsedDocument parse(InputStream inputStream, String fileName, String contentType) throws IOException {
        for (DocumentParser parser : parsers) {
            if (parser.supports(fileName, contentType)) {
                return parser.parse(inputStream, fileName);
            }
        }
        throw new IllegalArgumentException("Unsupported document format: '" + fileName +
                "'. Supported formats are PDF (.pdf) and Word documents (.docx, .doc).");
    }

    public boolean isSupported(String fileName, String contentType) {
        for (DocumentParser parser : parsers) {
            if (parser.supports(fileName, contentType)) {
                return true;
            }
        }
        return false;
    }
}
