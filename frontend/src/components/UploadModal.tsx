import React, { useState } from 'react';
import { X, Upload, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { uploadEHRFile, IngestionResultData } from '../services/api';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess?: () => void;
}

export default function UploadModal({ isOpen, onClose, onUploadSuccess }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [autoProcess, setAutoProcess] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [result, setResult] = useState<IngestionResultData | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a .json or .csv file to upload');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const res = await uploadEHRFile(file, autoProcess);
      setResult(res.data);
      if (onUploadSuccess) onUploadSuccess();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-slate-700" />
            <h3 className="font-semibold text-slate-900 text-base">Ingest Messy EHR Export</h3>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600 cursor-pointer">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Drop Zone */}
        <div className="border-2 border-dashed border-slate-200 hover:border-slate-400 rounded-xl p-6 text-center space-y-2 cursor-pointer transition-colors bg-slate-50/50">
          <input
            type="file"
            accept=".json,.csv"
            onChange={handleFileChange}
            className="hidden"
            id="ehr-file-upload"
          />
          <label htmlFor="ehr-file-upload" className="cursor-pointer block">
            <Upload className="h-8 w-8 text-slate-400 mx-auto mb-2" />
            <span className="text-sm font-medium text-slate-700">
              {file ? file.name : 'Choose a .json or .csv file'}
            </span>
            <p className="text-xs text-slate-400 mt-1">Accepts raw JSON dumps or CSV scanned notes</p>
          </label>
        </div>

        {/* Auto-Process Checkbox */}
        <div className="flex items-center gap-2 text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
          <input
            type="checkbox"
            id="auto-proc"
            checked={autoProcess}
            onChange={(e) => setAutoProcess(e.target.checked)}
            className="rounded text-slate-900 focus:ring-slate-900"
          />
          <label htmlFor="auto-proc" className="cursor-pointer">
            <span className="font-medium text-slate-800">Auto-trigger FHIR R4 & Semantic Indexing</span>
            <p className="text-[11px] text-slate-400">Normalizes records and indexes into ChromaDB in one step</p>
          </label>
        </div>

        {/* Error / Success states */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {result && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-semibold">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              <span>Ingestion Complete</span>
            </div>
            <p className="text-[11px]">
              Processed {result.ingestion?.total_processed} records ({result.ingestion?.total_cleaned} clean, {result.ingestion?.total_duplicates_dropped} duplicates dropped).
            </p>
            {result.fhir_normalization && (
              <p className="text-[11px] text-emerald-700 font-medium">
                Created {result.fhir_normalization.total_bundles_created} FHIR Bundles ({result.fhir_normalization.total_resources_mapped} resources mapped).
              </p>
            )}
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-800 transition-colors cursor-pointer"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || isUploading}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-medium disabled:opacity-50 transition-colors shadow-sm cursor-pointer"
          >
            {isUploading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            <span>{isUploading ? 'Ingesting...' : 'Start Ingestion'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
