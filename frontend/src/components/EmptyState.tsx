import { Search, Sparkles, Database, ArrowLeft, Upload, AlertCircle, RefreshCw } from 'lucide-react';
import { sampleQueries } from '../common/shared';

export interface EmptyStateProps {
  type?: 'search_empty' | 'browse_empty' | 'error' | 'initial';
  searchQuery?: string;
  errorMessage?: string;
  onClearSearch?: () => void;
  onOpenUpload?: () => void;
  onQuickSearch?: (query: string) => void;
  onRetry?: () => void;
}

export default function EmptyState({
  type = 'initial',
  searchQuery = '',
  errorMessage,
  onClearSearch,
  onOpenUpload,
  onQuickSearch,
  onRetry,
}: EmptyStateProps) {
  if (type === 'error') {
    return (
      <div className="text-center py-12 px-4 bg-white rounded-xl border border-red-200 p-6 space-y-4 shadow-sm">
        <div className="h-12 w-12 rounded-full bg-red-50 flex items-center justify-center mx-auto text-red-600">
          <AlertCircle className="h-6 w-6" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-800 text-sm sm:text-base">
            Failed to load clinical records
          </h3>
          <p className="text-xs text-red-600 max-w-md mx-auto mt-1">
            {errorMessage || 'A network error occurred while communicating with the backend.'}
          </p>
        </div>
        {onRetry && (
          <div>
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-medium transition-colors cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Retry Request
            </button>
          </div>
        )}
      </div>
    );
  }

  if (type === 'search_empty') {
    return (
      <div className="text-center py-12 px-4 bg-white rounded-xl border border-slate-200 p-6 space-y-4 shadow-sm">
        <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
          <Search className="h-6 w-6" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-800 text-sm sm:text-base">
            No clinical records matched your search query
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
            {searchQuery
              ? `No semantic matches found for "${searchQuery}". Try broadening your terms or adjusting filters.`
              : 'Try broadening your search query or removing the date/type filters.'}
          </p>
        </div>

        <div className="flex items-center justify-center gap-3 pt-1 flex-wrap">
          {onClearSearch && (
            <button
              type="button"
              onClick={onClearSearch}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-medium transition-colors cursor-pointer"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back to All Records
            </button>
          )}
        </div>

        {onQuickSearch && (
          <div className="pt-4 border-t border-slate-100 max-w-lg mx-auto">
            <span className="text-xs font-medium text-slate-500 inline-flex items-center gap-1 mb-2.5">
              <Sparkles className="h-3 w-3 text-indigo-500" /> Try these clinical queries instead:
            </span>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {sampleQueries.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onQuickSearch(sample)}
                  className="text-xs px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-slate-900 rounded-lg border border-slate-200 transition-colors cursor-pointer"
                >
                  {sample}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (type === 'browse_empty') {
    return (
      <div className="text-center py-12 px-4 bg-white rounded-xl border border-slate-200 p-6 space-y-4 shadow-sm">
        <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
          <Database className="h-6 w-6" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-800 text-sm sm:text-base">
            No clinical records found
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
            No records match your active filters, or the database is currently empty.
          </p>
        </div>
        {onOpenUpload && (
          <div>
            <button
              type="button"
              onClick={onOpenUpload}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-medium transition-colors cursor-pointer"
            >
              <Upload className="h-3.5 w-3.5" /> Upload EHR Dataset
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="text-center py-12 px-4 bg-white rounded-xl border border-slate-200 border-dashed space-y-4">
      <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
        <Search className="h-6 w-6" />
      </div>
      <div>
        <h3 className="font-semibold text-slate-800 text-sm sm:text-base">No clinical search performed yet</h3>
        <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
          Type a natural language query above to search unstructured notes, lab panels, and imaging findings.
        </p>
      </div>

      {onQuickSearch && (
        <div className="pt-2">
          <span className="text-xs font-medium text-slate-500 inline-flex items-center gap-1 mb-2">
            <Sparkles className="h-3 w-3 text-indigo-500" /> Try these clinical queries:
          </span>
          <div className="flex flex-wrap items-center justify-center gap-2 max-w-md mx-auto">
            {sampleQueries.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onQuickSearch(sample)}
                className="text-xs px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-slate-900 rounded-lg border border-slate-200 transition-colors cursor-pointer"
              >
                {sample}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
