'use client';

import React, { useState } from 'react';
import { Download, Eye, EyeOff, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface CsvPreviewProps {
  data: string[][];
  filename?: string;
  onReset: () => void;
}

export default function CsvPreview({ data, filename, onReset }: CsvPreviewProps) {
  const [showPreview, setShowPreview] = useState(true);
  const [currentPage, setCurrentPage] = useState(0);

  const ROWS_PER_PAGE = 10;
  const totalPages = Math.ceil((data.length - 1) / ROWS_PER_PAGE); // -1 to exclude header
  const headers = data[0] || [];

  // Get paginated data (excluding header)
  const dataWithoutHeaders = data.slice(1);
  const paginatedData = dataWithoutHeaders.slice(
    currentPage * ROWS_PER_PAGE,
    (currentPage + 1) * ROWS_PER_PAGE
  );

  const downloadCsv = () => {
    const csvContent = data
      .map(row =>
        row.map(cell => {
          // Escape quotes and wrap in quotes if cell contains comma, quote, or newline
          const escaped = cell.replace(/"/g, '""');
          return /[",\n]/.test(cell) ? `"${escaped}"` : cell;
        }).join(',')
      )
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename || 'converted-data.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <Card className="border-green-200 bg-green-50">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle className="text-green-800 flex items-center space-x-2">
                <span>✓ Conversion Complete</span>
              </CardTitle>
              <p className="text-sm text-green-700">
                Successfully extracted {dataWithoutHeaders.length} rows of data from your PDF
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowPreview(!showPreview)}
                className="text-green-700 border-green-300 hover:bg-green-100"
              >
                {showPreview ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
                {showPreview ? 'Hide' : 'Show'} Preview
              </Button>
              <Button
                onClick={downloadCsv}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                <Download className="h-4 w-4 mr-2" />
                Download CSV
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {showPreview && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Data Preview</CardTitle>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                  disabled={currentPage === 0}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm text-gray-600 px-2">
                  Page {currentPage + 1} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(Math.min(totalPages - 1, currentPage + 1))}
                  disabled={currentPage === totalPages - 1}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              Showing rows {currentPage * ROWS_PER_PAGE + 1}-{Math.min((currentPage + 1) * ROWS_PER_PAGE, dataWithoutHeaders.length)} of {dataWithoutHeaders.length}
            </p>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b bg-gray-50">
                    {headers.map((header, index) => (
                      <th
                        key={index}
                        className="px-4 py-3 text-left text-xs font-medium text-gray-900 uppercase tracking-wider border-r last:border-r-0"
                      >
                        {header || `Column ${index + 1}`}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {paginatedData.map((row, rowIndex) => (
                    <tr
                      key={rowIndex}
                      className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                    >
                      {row.map((cell, cellIndex) => (
                        <td
                          key={cellIndex}
                          className="px-4 py-3 text-sm text-gray-900 border-r last:border-r-0 max-w-xs truncate"
                          title={cell}
                        >
                          {cell}
                        </td>
                      ))}
                      {/* Fill empty cells if row is shorter than headers */}
                      {Array.from({ length: Math.max(0, headers.length - row.length) }).map((_, index) => (
                        <td
                          key={`empty-${index}`}
                          className="px-4 py-3 text-sm text-gray-500 border-r last:border-r-0"
                        >
                          —
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-center">
        <Button
          variant="outline"
          onClick={onReset}
          className="text-gray-700 border-gray-300 hover:bg-gray-50"
        >
          Convert Another PDF
        </Button>
      </div>
    </div>
  );
}