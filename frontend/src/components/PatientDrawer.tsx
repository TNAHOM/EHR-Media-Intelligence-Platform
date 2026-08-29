import { useState, useEffect } from 'react';
import { X, Sparkles, Database, FileText, Loader2, ShieldCheck, CheckCircle2, Copy, Calendar, Tag } from 'lucide-react';
import { fetchPatientSummary, fetchFHIRBundle, SearchResultItem, PatientSummaryData, FHIRBundleData } from '../services/api';

interface PatientDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  selectedRecord: SearchResultItem | null;
}

export default function PatientDrawer({ isOpen, onClose, selectedRecord }: PatientDrawerProps) {
  const [activeTab, setActiveTab] = useState<'record' | 'summary' | 'fhir'>('record');
  const [summaryData, setSummaryData] = useState<PatientSummaryData | null>(null);
  const [fhirData, setFhirData] = useState<FHIRBundleData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const patientMrn = selectedRecord?.patient_mrn;
  const patientName = selectedRecord?.patient_name;

  useEffect(() => {
    if (!isOpen || !patientMrn) return;

    let isMounted = true;

    const loadPatientData = async () => {
      setActiveTab('record'); // Default to the clicked record
      setIsLoading(true);
      setError(null);

      const [sumRes, fhirRes] = await Promise.all([
        fetchPatientSummary(patientMrn).catch((err: Error) => ({ error: err.message })),
        fetchFHIRBundle(patientMrn).catch((err: Error) => ({ error: err.message })),
      ]);

      if (!isMounted) return;

      if ('data' in sumRes && sumRes.data) {
        setSummaryData(sumRes.data);
      } else if ('error' in sumRes && sumRes.error) {
        setError(sumRes.error);
      }

      if ('data' in fhirRes && fhirRes.data) {
        setFhirData(fhirRes.data);
      }
      setIsLoading(false);
    };

    loadPatientData();

    return () => {
      isMounted = false;
    };
  }, [isOpen, patientMrn, selectedRecord?.record_id]);

  if (!isOpen || !selectedRecord) return null;

  const handleCopyJson = () => {
    if (!fhirData) return;
    navigator.clipboard.writeText(JSON.stringify(fhirData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div onClick={onClose} className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity" />

      {/* Drawer Panel */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-2xl bg-white shadow-2xl flex flex-col">
          {/* Drawer Header */}
          <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-slate-900">{patientName}</h2>
                <span className="px-2 py-0.5 text-xs font-mono bg-slate-200/70 text-slate-700 rounded font-medium">
                  {patientMrn}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">HL7 FHIR R4 Patient Chart & AI Insights</p>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-200 px-5 gap-6 text-xs font-medium bg-white">
            <button
              type="button"
              onClick={() => setActiveTab('record')}
              className={`py-3 flex items-center gap-1.5 border-b-2 transition-colors cursor-pointer ${
                activeTab === 'record' ? 'border-slate-900 text-slate-900 font-semibold' : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <FileText className="h-4 w-4 text-teal-600" /> Matched Record
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('summary')}
              className={`py-3 flex items-center gap-1.5 border-b-2 transition-colors cursor-pointer ${
                activeTab === 'summary' ? 'border-indigo-600 text-indigo-600 font-semibold' : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Sparkles className="h-4 w-4 text-indigo-600" /> AI Patient Summary
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('fhir')}
              className={`py-3 flex items-center gap-1.5 border-b-2 transition-colors cursor-pointer ${
                activeTab === 'fhir' ? 'border-indigo-600 text-indigo-600 font-semibold' : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Database className="h-4 w-4 text-slate-600" /> Raw FHIR Bundle
            </button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-5 sm:p-6">
            {isLoading ? (
              <div className="h-64 flex flex-col items-center justify-center gap-3 text-slate-400">
                <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                <span className="text-xs">Loading clinical records...</span>
              </div>
            ) : error ? (
              <div className="p-4 bg-red-50 text-red-700 border border-red-200 rounded-lg text-xs">{error}</div>
            ) : activeTab === 'record' ? (
              /* TAB 1: The Exact Clicked Record */
              <div className="space-y-4">
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="inline-flex items-center gap-1.5 font-medium text-teal-800 bg-teal-50 px-2.5 py-0.5 rounded border border-teal-200">
                      <Tag className="h-3 w-3" /> {selectedRecord.resource_type} • {selectedRecord.record_type}
                    </span>
                    <span className="inline-flex items-center gap-1 text-slate-500">
                      <Calendar className="h-3.5 w-3.5" /> {selectedRecord.record_date}
                    </span>
                  </div>
                  <div className="text-xs font-mono text-slate-400">
                    Record ID: {selectedRecord.record_id}
                    {typeof selectedRecord.relevance_score === 'number' && (
                      <span> • Match Score: {Math.round(selectedRecord.relevance_score * 100)}%</span>
                    )}
                  </div>
                </div>


                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Full Record Content</h4>
                  <div className="p-4 bg-white rounded-xl border border-slate-200 text-sm text-slate-800 leading-relaxed font-mono whitespace-pre-wrap shadow-sm">
                    {selectedRecord.full_content || selectedRecord.snippet}
                  </div>
                </div>
              </div>
            ) : activeTab === 'summary' && summaryData ? (
              /* TAB 2: Whole-Patient AI Summary */
              <div className="space-y-5">
                <div className="flex items-center justify-between p-3 rounded-lg bg-indigo-50/60 border border-indigo-100 text-xs">
                  <span className="inline-flex items-center gap-1.5 text-indigo-700 font-medium">
                    <Sparkles className="h-4 w-4" /> Model: {summaryData.model_used}
                  </span>
                  <span className="text-slate-500">
                    {summaryData.cache_hit ? '⚡ Cached (0ms)' : 'AI Generated'}
                  </span>
                </div>

                <div className="space-y-1.5">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Chief Concern</h4>
                  <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200/80 text-sm text-slate-800 leading-relaxed">
                    {summaryData.chief_concern}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Key Diagnoses</h4>
                  <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200/80 text-sm text-slate-800 leading-relaxed">
                    {summaryData.key_diagnoses}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Recent Media Records</h4>
                  <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200/80 text-sm text-slate-800 leading-relaxed">
                    {summaryData.recent_media_records}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-700">Flagged Anomalies</h4>
                  <div className="p-3.5 bg-amber-50/50 rounded-lg border border-amber-200/80 text-sm text-amber-900 leading-relaxed">
                    {summaryData.flagged_anomalies}
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex items-start gap-2.5 text-[11px] text-slate-400">
                  <ShieldCheck className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                  <p>{summaryData.disclaimer}</p>
                </div>
              </div>
            ) : activeTab === 'fhir' && fhirData ? (
              /* TAB 3: Raw FHIR Bundle */
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-mono">Entries: {fhirData.entry?.length || 0} FHIR R4 Resources</span>
                  <button
                    type="button"
                    onClick={handleCopyJson}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs transition-colors cursor-pointer"
                  >
                    {copied ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                    {copied ? 'Copied' : 'Copy JSON'}
                  </button>
                </div>
                <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-xs font-mono overflow-x-auto max-h-[500px]">
                  {JSON.stringify(fhirData, null, 2)}
                </pre>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
