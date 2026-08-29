import { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import SearchAndFilters from './components/SearchAndFilters';
import ResultCard from './components/ResultCard';
import PatientDrawer from './components/PatientDrawer';
import UploadModal from './components/UploadModal';
import Pagination from './components/Pagination';
import EmptyState from './components/EmptyState';
import {
  fetchCleanRecords,
  mapCleanRecordToSearchResultItem,
  PaginationMeta,
  searchRecords,
  SearchResultItem,
} from './services/api';
import { Clock, Database, ArrowLeft, RefreshCw } from 'lucide-react';


export default function App() {
  // Search & Filter State
  const [query, setQuery] = useState<string>('');
  const [resourceType, setResourceType] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [patientMrn, setPatientMrn] = useState<string>('');

  // Mode & Data State
  const [isSearchMode, setIsSearchMode] = useState<boolean>(false);
  const [activeSearchQuery, setActiveSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [executionTime, setExecutionTime] = useState<number | null>(null);

  // Paginated Records (Browse Mode)
  const [cleanRecords, setCleanRecords] = useState<SearchResultItem[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Status & Modals
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPatient, setSelectedPatient] = useState<SearchResultItem | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [refreshKey, setRefreshKey] = useState<number>(0);

  // Initial load and filter change for browse mode
  useEffect(() => {
    if (isSearchMode) return;

    let isSubscribed = true;
    setIsLoading(true);

    fetchCleanRecords({
      page,
      pageSize,
      mrn: patientMrn.trim() || undefined,
      resourceType: resourceType || undefined,
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
    })
      .then((res) => {
        if (!isSubscribed) return;
        if (res.data) {
          const mapped = res.data.map(mapCleanRecordToSearchResultItem);
          setCleanRecords(mapped);
          setPagination(res.pagination);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!isSubscribed) return;
        const msg = err instanceof Error ? err.message : 'Failed to load records';
        setError(msg);
      })
      .finally(() => {
        if (isSubscribed) {
          setIsLoading(false);
        }
      });

    return () => {
      isSubscribed = false;
    };
  }, [page, pageSize, resourceType, dateFrom, dateTo, patientMrn, isSearchMode, refreshKey]);

  // Search mode effect: executes search reactively when activeSearchQuery or filters change
  useEffect(() => {
    if (!isSearchMode || !activeSearchQuery.trim()) return;

    let isSubscribed = true;
    setIsLoading(true);

    searchRecords({
      query: activeSearchQuery.trim(),
      resourceType: resourceType || undefined,
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
      patientMrn: patientMrn.trim() || undefined,
      limit: 10,
    })
      .then((res) => {
        if (!isSubscribed) return;
        if (res.data) {
          setSearchResults(res.data.results || []);
          setExecutionTime(res.data.execution_time_ms);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!isSubscribed) return;
        const msg = err instanceof Error ? err.message : 'Failed to execute search';
        setError(msg);
      })
      .finally(() => {
        if (isSubscribed) {
          setIsLoading(false);
        }
      });

    return () => {
      isSubscribed = false;
    };
  }, [isSearchMode, activeSearchQuery, resourceType, dateFrom, dateTo, patientMrn, refreshKey]);

  // Filter change handlers
  const handleResourceTypeChange = (type: string) => {
    setResourceType(type);
    setPage(1);
  };
  const handleDateFromChange = (date: string) => {
    setDateFrom(date);
    setPage(1);
  };
  const handleDateToChange = (date: string) => {
    setDateTo(date);
    setPage(1);
  };
  const handlePatientMrnChange = (mrn: string) => {
    setPatientMrn(mrn);
    setPage(1);
  };

  // Perform semantic search
  const handleSearch = (overrideQuery?: string) => {
    const q = overrideQuery !== undefined ? overrideQuery : query;
    if (!q.trim()) {
      handleClearSearch();
      return;
    }

    setError(null);
    setIsSearchMode(true);
    setActiveSearchQuery(q.trim());
  };

  // Return from search mode to all records
  const handleClearSearch = () => {
    setIsSearchMode(false);
    setActiveSearchQuery('');
    setSearchResults([]);
    setExecutionTime(null);
    setQuery('');
  };

  const handleQuickSearch = (sampleQuery: string) => {
    setQuery(sampleQuery);
    handleSearch(sampleQuery);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setPage(1);
  };

  const displayedRecords = isSearchMode ? searchResults : cleanRecords;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50/50">
      <Navbar onOpenUpload={() => setIsUploadOpen(true)} />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
        {/* Search & Filter Controls */}
        <SearchAndFilters
          query={query}
          setQuery={setQuery}
          resourceType={resourceType}
          setResourceType={handleResourceTypeChange}
          dateFrom={dateFrom}
          setDateFrom={handleDateFromChange}
          dateTo={dateTo}
          setDateTo={handleDateToChange}
          patientMrn={patientMrn}
          setPatientMrn={handlePatientMrnChange}
          onSearch={() => handleSearch()}
          onClearSearch={handleClearSearch}
          onQuickSearch={handleQuickSearch}
          isLoading={isLoading}
        />

        {/* Error Alert */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs flex items-center justify-between">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => {
                setIsLoading(true);
                setRefreshKey((k) => k + 1);
              }}
              className="inline-flex items-center gap-1 font-medium underline text-red-800 cursor-pointer"
            >
              <RefreshCw className="h-3 w-3" /> Retry
            </button>
          </div>
        )}

        {/* Mode Status & Metadata Header */}
        {!isLoading && !error && (
          <div className="flex items-center justify-between text-xs text-slate-500 px-1 flex-wrap gap-2">
            {isSearchMode ? (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium cursor-pointer transition-colors bg-indigo-50 hover:bg-indigo-100 px-2 py-1 rounded-md border border-indigo-200 text-xs"
                >
                  <ArrowLeft className="h-3 w-3" /> View All Records
                </button>
                <span>
                  Found <strong className="text-slate-800">{searchResults.length}</strong> semantic matches for "
                  <strong className="text-slate-900">{activeSearchQuery}</strong>"
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 font-semibold text-slate-800">
                  <Database className="h-3.5 w-3.5 text-slate-500" /> All Clinical Records
                </span>
                {pagination && (
                  <span className="text-slate-400">
                    ({pagination.total_records} total in database)
                  </span>
                )}
              </div>
            )}

            {isSearchMode && executionTime !== null && (
              <span className="inline-flex items-center gap-1 font-mono text-[11px] bg-white px-2 py-0.5 rounded border border-slate-200 shadow-2xs">
                <Clock className="h-3 w-3 text-slate-400" /> {executionTime}ms
              </span>
            )}
          </div>
        )}

        {/* Records List / Skeletons / Empty States */}
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((n) => (
              <div
                key={n}
                className="bg-white rounded-xl border border-slate-200 p-5 animate-pulse space-y-3 shadow-2xs"
              >
                <div className="flex items-center justify-between">
                  <div className="h-4 bg-slate-200 rounded w-1/4" />
                  <div className="h-4 bg-slate-100 rounded w-16" />
                </div>
                <div className="h-5 bg-slate-200 rounded w-1/2" />
                <div className="h-12 bg-slate-100 rounded w-full" />
              </div>
            ))}
          </div>
        ) : displayedRecords.length === 0 ? (
          isSearchMode ? (
            <EmptyState
              type="search_empty"
              searchQuery={activeSearchQuery}
              onClearSearch={handleClearSearch}
              onQuickSearch={handleQuickSearch}
            />
          ) : (
            <EmptyState
              type="browse_empty"
              onOpenUpload={() => setIsUploadOpen(true)}
            />
          )
        ) : (
          <div className="space-y-4">
            <div className="space-y-3">
              {displayedRecords.map((item) => (
                <ResultCard
                  key={item.record_id}
                  item={item}
                  onSelectPatient={() => setSelectedPatient(item)}
                />
              ))}
            </div>

            {/* Pagination for Browse Mode */}
            {!isSearchMode && pagination && pagination.total_pages > 1 && (
              <Pagination
                pagination={pagination}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
                isLoading={isLoading}
              />
            )}
          </div>
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
          setIsLoading(true);
          setPage(1);
          setRefreshKey((k) => k + 1);
        }}
      />
    </div>
  );
}
