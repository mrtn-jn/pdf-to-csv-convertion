import { FileValidation } from '@/types';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB in bytes
const ALLOWED_TYPES = ['application/pdf'];

export function validatePdfFile(file: File): FileValidation {
  // Check file type
  if (!ALLOWED_TYPES.includes(file.type)) {
    return {
      isValid: false,
      error: 'Please select a PDF file only.'
    };
  }

  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    return {
      isValid: false,
      error: 'File size must be less than 10MB.'
    };
  }

  // Additional check for file extension
  const fileName = file.name.toLowerCase();
  if (!fileName.endsWith('.pdf')) {
    return {
      isValid: false,
      error: 'File must have a .pdf extension.'
    };
  }

  return {
    isValid: true
  };
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}