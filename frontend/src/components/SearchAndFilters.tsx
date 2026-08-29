import React from 'react';
import { Search, Filter, Calendar, X, Loader2, Sparkles } from 'lucide-react';

interface SearchAndFiltersProps {
  query: string;
  setQuery: (query: string) => void;
  resourceType: string;
  setResourceType: (type: string) => void;
  dateFrom: string;
  setDateFrom: (date: string) => void;
  dateTo: string;
  setDateTo: (date: string) => void;
  patientMrn: string;
  setPatientMrn: (mrn: string) => void;
  onSearch: () => void;
  onClearSearch?: () => void;
  onQuickSearch?: (sampleQuery: string) => void;
  isLoading: boolean;
}

export default function SearchAndFilters({
  query,
  setQuery,
  resourceType,
  setResourceType,
  dateFrom,
  setDateFrom,
  dateTo,
  setDateTo,
  patientMrn,
  setPatientMrn,
  onSearch,
  onClearSearch,
  onQuickSearch,
  isLoading,
}: SearchAndFiltersProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      onSearch();
    }
  };

  const sampleQueries = [
    'chest pain and elevated troponin',
    'diabetic peripheral neuropathy',
    'moderate cardiomegaly on chest xray',
    'migraine with visual aura',
  ];

  const hasActiveFilters = Boolean(resourceType || dateFrom || dateTo || patientMrn);

  const handleResetFilters = () => {
    setResourceType('');
    setDateFrom('');
    setDateTo('');
    setPatientMrn('');
  };

  const handleClearQuery = () => {
    setQuery('');
    if (onClearSearch) {
      onClearSearch();
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-sm space-y-3.5">
      {/* Primary Search Bar */}
      <div className="flex flex-col sm:flex-row gap-2.5">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search patient notes, labs, imaging findings (e.g., 'elevated troponin', 'diabetic neuropathy')..."
            className="w-full pl-10 pr-10 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:bg-white transition-all"
          />
          {query && (
            <button
              type="button"
              onClick={handleClearQuery}
              title="Clear search"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={onSearch}
          disabled={isLoading || !query.trim()}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed min-w-[110px] cursor-pointer"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Searching</span>
            </>
          ) : (
            <>
              <span>Search</span>
            </>
          )}
        </button>
      </div>

      {/* Quick Clinical Prompts */}
      <div className="flex items-center gap-2 flex-wrap text-xs text-slate-500 pt-0.5">
        <span className="inline-flex items-center gap-1 font-medium text-slate-400 text-[11px]">
          <Sparkles className="h-3 w-3 text-indigo-500" /> Try:
        </span>
        {sampleQueries.map((sample, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onQuickSearch?.(sample)}
            className="px-2.5 py-1 rounded-md bg-slate-100/80 hover:bg-slate-200/80 text-slate-600 hover:text-slate-900 transition-colors text-[11px] cursor-pointer"
          >
            {sample}
          </button>
        ))}
      </div>

      {/* Filter Controls Row */}
      <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center gap-2.5 sm:gap-3 text-xs text-slate-600">
        <div className="flex items-center gap-1.5 font-medium text-slate-500">
          <Filter className="h-3.5 w-3.5" />
          <span>Filters:</span>
        </div>

        {/* Resource Type Dropdown */}
        <select
          value={resourceType}
          onChange={(e) => setResourceType(e.target.value)}
          className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400 cursor-pointer"
        >
          <option value="">All Resource Types</option>
          <option value="DocumentReference">Clinical Notes & Discharge</option>
          <option value="DiagnosticReport">Labs & Imaging (Reports)</option>
          <option value="ClinicalSummary">AI Clinical Summaries</option>
        </select>

        {/* Date From */}
        <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1">
          <Calendar className="h-3.5 w-3.5 text-slate-400" />
          <span className="text-slate-400 text-[11px]">From:</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="bg-transparent text-slate-700 focus:outline-none text-xs"
          />
        </div>

        {/* Date To */}
        <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1">
          <Calendar className="h-3.5 w-3.5 text-slate-400" />
          <span className="text-slate-400 text-[11px]">To:</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="bg-transparent text-slate-700 focus:outline-none text-xs"
          />
        </div>

        {/* Patient MRN filter */}
        <input
          type="text"
          value={patientMrn}
          onChange={(e) => setPatientMrn(e.target.value)}
          placeholder="Filter by MRN..."
          className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700 placeholder:text-slate-400 focus:outline-none text-xs w-32"
        />

        {hasActiveFilters && (
          <button
            type="button"
            onClick={handleResetFilters}
            className="text-slate-500 hover:text-slate-800 underline ml-auto text-[11px] cursor-pointer"
          >
            Clear Filters
          </button>
        )}
      </div>
    </div>
  );
}

