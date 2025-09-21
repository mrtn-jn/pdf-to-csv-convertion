'use client';

import React, { useState } from 'react';
import { AlertCircle, FileText } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import PdfUploadZone from '@/components/PdfUploadZone';
import CsvPreview from '@/components/CsvPreview';
import { UploadState, ApiResponse } from '@/types';
import { validatePdfFile } from '@/utils/fileValidation';

export default function Home() {
  const [uploadState, setUploadState] = useState<UploadState>({
    file: null,
    isUploading: false,
    uploadProgress: 0,
    isProcessing: false,
    csvData: null,
    error: null,
    success: false
  });

  const resetUpload = () => {
    setUploadState({
      file: null,
      isUploading: false,
      uploadProgress: 0,
      isProcessing: false,
      csvData: null,
      error: null,
      success: false
    });
  };

  const handleFileSelect = async (file: File) => {
    const validation = validatePdfFile(file);
    if (!validation.isValid) {
      setUploadState(prev => ({
        ...prev,
        error: validation.error || 'Invalid file',
        file: null
      }));
      return;
    }

    setUploadState(prev => ({
      ...prev,
      file,
      error: null,
      success: false
    }));

    await uploadFile(file);
  };

  const uploadFile = async (file: File) => {
    setUploadState(prev => ({
      ...prev,
      isUploading: true,
      uploadProgress: 0,
      error: null
    }));

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/upload-pdf', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Server error: ${response.status}`);
      }

      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadState(prev => {
          if (prev.uploadProgress >= 90) {
            clearInterval(progressInterval);
            return { ...prev, uploadProgress: 100, isProcessing: true };
          }
          return { ...prev, uploadProgress: prev.uploadProgress + 10 };
        });
      }, 200);

      const result: ApiResponse = await response.json();

      if (result.success && result.data) {
        // Transform backend data structure to CSV array format
        const csvArray = result.data && result.data.headers && result.data.rows 
          ? [result.data.headers, ...result.data.rows] 
          : null;
        
        setUploadState(prev => ({
          ...prev,
          isUploading: false,
          isProcessing: false,
          uploadProgress: 100,
          csvData: csvArray,
          success: true,
          error: null
        }));
      } else {
        throw new Error(result.message || 'Failed to process PDF');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadState(prev => ({
        ...prev,
        isUploading: false,
        isProcessing: false,
        uploadProgress: 0,
        error: error instanceof Error ? error.message : 'Upload failed. Please try again.',
        success: false
      }));
    }
  };

  const handleRemoveFile = () => {
    setUploadState(prev => ({
      ...prev,
      file: null,
      error: null
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-4">
            <FileText className="h-12 w-12 text-blue-600 mr-3" />
            <h1 className="text-4xl font-bold text-gray-900">PDF to CSV Converter</h1>
          </div>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Transform your PDF documents into structured CSV data.
            Simply upload your PDF file and get a downloadable CSV with all extracted information.
          </p>
        </div>

        {/* Main Content */}
        <div className="max-w-2xl mx-auto">
          {uploadState.success && uploadState.csvData ? (
            <CsvPreview
              data={uploadState.csvData}
              filename={uploadState.file?.name?.replace('.pdf', '.csv')}
              onReset={resetUpload}
            />
          ) : (
            <>
              <PdfUploadZone
                onFileSelect={handleFileSelect}
                isUploading={uploadState.isUploading || uploadState.isProcessing}
                uploadProgress={uploadState.uploadProgress}
                error={uploadState.error}
                selectedFile={uploadState.file}
                onRemoveFile={handleRemoveFile}
              />

              {/* Processing State */}
              {uploadState.isProcessing && (
                <div className="mt-6">
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Processing your PDF file... This may take a few moments depending on the file size and complexity.
                    </AlertDescription>
                  </Alert>
                </div>
              )}

              {/* Instructions */}
              {!uploadState.file && !uploadState.error && (
                <div className="mt-8 space-y-6">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                    <h3 className="font-semibold text-blue-900 mb-3">How it works:</h3>
                    <ol className="text-sm text-blue-800 space-y-2 list-decimal list-inside">
                      <li>Upload your PDF file using the drag-and-drop area above</li>
                      <li>Our system will automatically extract tabular data from your PDF</li>
                      <li>Preview the extracted data in a formatted table</li>
                      <li>Download your data as a CSV file for use in Excel, Google Sheets, or other applications</li>
                    </ol>
                  </div>

                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
                    <h3 className="font-semibold text-gray-900 mb-3">Supported files:</h3>
                    <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                      <li>PDF files with tables or structured data</li>
                      <li>Maximum file size: 10MB</li>
                      <li>Best results with PDFs containing clear table structures</li>
                    </ul>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <footer className="text-center mt-16 py-8 border-t border-gray-200">
          <p className="text-sm text-gray-500">
            Secure PDF processing with privacy protection. Your files are processed locally and not stored.
          </p>
        </footer>
      </div>
    </div>
  );
}
