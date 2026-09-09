import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

export default function UploadDropzone({ onUploadSuccess, isUploading, uploadProgress }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = (file) => {
    setErrorMessage(null);

    const validExtensions = ['.pdf', '.docx', '.doc'];
    const fileName = file.name.toLowerCase();
    const isValidExtension = validExtensions.some(ext => fileName.endsWith(ext));

    if (!isValidExtension) {
      setErrorMessage(`Unsupported file format. Please upload a PDF (.pdf) or Word document (.docx).`);
      return;
    }

    const maxSize = 30 * 1024 * 1024; // 30 MB
    if (file.size > maxSize) {
      setErrorMessage(`File is too large (${(file.size / (1024 * 1024)).toFixed(1)}MB). Maximum allowed size is 30MB.`);
      return;
    }

    if (onUploadSuccess) {
      onUploadSuccess(file);
    }
  };

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-10 text-center transition-all cursor-pointer select-none ${
          isDragOver
            ? 'border-emerald-500 bg-emerald-50/50 scale-[1.01]'
            : 'border-gray-300 hover:border-emerald-400 hover:bg-gray-50/50 bg-white shadow-xs'
        } ${isUploading ? 'opacity-70 pointer-events-none' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleFileChange}
          className="hidden"
          disabled={isUploading}
        />

        {isUploading ? (
          <div className="flex flex-col items-center justify-center py-4 space-y-3">
            <div className="relative">
              <Loader2 className="w-10 h-10 text-emerald-600 animate-spin" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-gray-800">
                {uploadProgress || 'Processing document...'}
              </p>
              <p className="text-xs text-gray-500">
                Extracting text, chunking & generating Gemini embeddings
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shadow-xs border border-emerald-100">
              <UploadCloud className="w-7 h-7" />
            </div>

            <div className="space-y-1">
              <p className="text-sm sm:text-base font-semibold text-gray-800">
                Click to upload or drag & drop
              </p>
              <p className="text-xs text-gray-500">
                PDF or Word (.docx, .doc) up to 30MB
              </p>
            </div>

            <div className="inline-flex items-center gap-2 pt-1 text-[11px] font-medium text-emerald-700 bg-emerald-50/80 px-2.5 py-1 rounded-full border border-emerald-200/50">
              <FileText className="w-3.5 h-3.5" />
              <span>Full RAG extraction with page citations</span>
            </div>
          </div>
        )}
      </div>

      {/* Error alert if any */}
      {errorMessage && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2.5 text-xs text-red-700 animate-fade-in">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-600" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
}
