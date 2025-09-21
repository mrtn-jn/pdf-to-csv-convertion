export interface UploadState {
  file: File | null;
  isUploading: boolean;
  uploadProgress: number;
  isProcessing: boolean;
  csvData: string[][] | null;
  error: string | null;
  success: boolean;
}

export interface ApiResponse {
  success: boolean;
  data?: {
    headers: string[];
    rows: string[][];
    metadata: {
      totalTransactions: number;
      statementPeriod?: string;
      dueDate?: string;
      nextClosing?: string;
      balance?: string;
      bankName: string;
    };
  };
  message?: string;
  filename?: string;
  errors?: string[];
}

export interface FileValidation {
  isValid: boolean;
  error?: string;
}

export const UPLOAD_STATES = {
  IDLE: 'idle',
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  SUCCESS: 'success',
  ERROR: 'error'
} as const;

export type UploadStateType = typeof UPLOAD_STATES[keyof typeof UPLOAD_STATES];