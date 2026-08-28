import { useState } from 'react';
import Navbar from './components/Navbar';
import SearchAndFilters from './components/SearchAndFilters';
import ResultCard from './components/ResultCard';
import PatientDrawer from './components/PatientDrawer';
import UploadModal from './components/UploadModal';
import EmptyState from './components/EmptyState';
import { searchRecords, SearchResultItem } from './services/api';
import { Clock } from 'lucide-react';

export default function App() {
  const [query, setQuery] = useState<string>('');
  const [resourceType, setResourceType] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [patientMrn, setPatientMrn] = useState<string>('');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Drawer & Upload state
  const [selectedPatient, setSelectedPatient] = useState<SearchResultItem | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);

  const handleSearch = async (overrideQuery?: string) => {
    const q = overrideQuery || query;
    if (!q.trim()) return;

    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const res = await searchRecords({
        query: q,
        resourceType: resourceType || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        patientMrn: patientMrn || undefined,
        limit: 10,
      });

      if (res.data) {
        setResults(res.data.results || []);
        setExecutionTime(res.data.execution_time_ms);
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to execute search';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickSearch = (sampleQuery: string) => {
    setQuery(sampleQuery);
    handleSearch(sampleQuery);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50/50">
      <Navbar onOpenUpload={() => setIsUploadOpen(true)} />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
        {/* Search & Filter Controls */}
        <SearchAndFilters
          query={query}
          setQuery={setQuery}
          resourceType={resourceType}
          setResourceType={setResourceType}
          dateFrom={dateFrom}
          setDateFrom={setDateFrom}
          dateTo={dateTo}
          setDateTo={setDateTo}
          patientMrn={patientMrn}
          setPatientMrn={setPatientMrn}
          onSearch={() => handleSearch()}
          isLoading={isLoading}
        />

        {/* Error Alert */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs">
            {error}
          </div>
        )}

        {/* Results Metadata Header */}
        {hasSearched && !isLoading && !error && (
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>
              Showing <strong className="text-slate-800">{results.length}</strong> matching records
            </span>
            {executionTime !== null && (
              <span className="inline-flex items-center gap-1 font-mono text-[11px] bg-white px-2 py-0.5 rounded border border-slate-200">
                <Clock className="h-3 w-3 text-slate-400" /> {executionTime}ms
              </span>
            )}
          </div>
        )}

        {/* Results List / Empty States */}
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((n) => (
              <div key={n} className="bg-white rounded-xl border border-slate-200 p-5 animate-pulse space-y-3">
                <div className="h-4 bg-slate-200 rounded w-1/4" />
                <div className="h-5 bg-slate-200 rounded w-1/2" />
                <div className="h-12 bg-slate-100 rounded w-full" />
              </div>
            ))}
          </div>
        ) : hasSearched && results.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl border border-slate-200 p-6 space-y-2">
            <h3 className="font-semibold text-slate-800 text-sm">No clinical records matched your filters</h3>
            <p className="text-xs text-slate-400">Try broadening your search query or removing the date/type filters.</p>
          </div>
        ) : results.length > 0 ? (
          <div className="space-y-3.5">
            {results.map((item) => (
              <ResultCard
                key={item.record_id}
                item={item}
                onSelectPatient={() => setSelectedPatient(item)}
              />
            ))}
          </div>
        ) : (
          <EmptyState onQuickSearch={handleQuickSearch} />
        )}
      </main>

      {/* Patient Detail Drawer */}
      <PatientDrawer
        isOpen={Boolean(selectedPatient)}
        onClose={() => setSelectedPatient(null)}
        selectedRecord={selectedPatient}
      />

      {/* Upload Ingestion Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={() => {
          if (query) handleSearch();
        }}
      />
    </div>
  );
}
