'use client';

import React, { useState, useRef, DragEvent } from 'react';
import { Upload, FileText, X } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { validatePdfFile, formatFileSize } from '@/utils/fileValidation';

interface PdfUploadZoneProps {
  onFileSelect: (file: File) => void;
  isUploading: boolean;
  uploadProgress: number;
  error: string | null;
  selectedFile: File | null;
  onRemoveFile: () => void;
}

export default function PdfUploadZone({
  onFileSelect,
  isUploading,
  uploadProgress,
  error,
  selectedFile,
  onRemoveFile
}: PdfUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    // Only hide drag overlay if we're leaving the drop zone entirely
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragOver(false);
    }
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelection(files[0]);
    }
  };

  const handleFileSelection = (file: File) => {
    const validation = validatePdfFile(file);
    if (validation.isValid) {
      onFileSelect(file);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelection(files[0]);
    }
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  if (selectedFile && !isUploading) {
    return (
      <Card className="border-2 border-dashed border-green-300 bg-green-50">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileText className="h-8 w-8 text-green-600" />
              <div>
                <p className="font-medium text-green-800">{selectedFile.name}</p>
                <p className="text-sm text-green-600">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onRemoveFile}
              className="text-green-700 hover:text-green-900 hover:bg-green-100"
              disabled={isUploading}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card
        className={`border-2 border-dashed transition-all duration-200 cursor-pointer ${
          isDragOver
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
        } ${isUploading ? 'pointer-events-none opacity-60' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        <CardContent className="p-8 text-center">
          <div className="flex flex-col items-center space-y-4">
            <div className={`rounded-full p-4 ${isDragOver ? 'bg-blue-100' : 'bg-gray-100'}`}>
              <Upload className={`h-8 w-8 ${isDragOver ? 'text-blue-600' : 'text-gray-600'}`} />
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">
                {isDragOver ? 'Drop your PDF here' : 'Upload PDF File'}
              </h3>
              <p className="text-sm text-gray-600">
                Drag and drop your PDF file here, or click to browse
              </p>
              <p className="text-xs text-gray-500">
                Maximum file size: 10MB
              </p>
            </div>

            {!isDragOver && (
              <Button variant="outline" className="mt-4">
                Choose File
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {isUploading && (
        <div className="space-y-2">
          <Progress value={uploadProgress} className="w-full" />
          <p className="text-sm text-center text-gray-600">
            {uploadProgress < 100 ? `Uploading... ${uploadProgress}%` : 'Processing PDF...'}
          </p>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleFileInputChange}
        className="hidden"
        disabled={isUploading}
      />
    </div>
  );
}