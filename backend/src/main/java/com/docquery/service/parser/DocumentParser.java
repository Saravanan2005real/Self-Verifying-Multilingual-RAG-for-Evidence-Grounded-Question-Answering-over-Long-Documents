package com.docquery.service.parser;

import com.docquery.model.ParsedDocument;
import java.io.IOException;
import java.io.InputStream;

public interface DocumentParser {
    boolean supports(String fileName, String contentType);
    ParsedDocument parse(InputStream inputStream, String fileName) throws IOException;
}
