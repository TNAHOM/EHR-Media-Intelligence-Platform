import { Search, Sparkles } from 'lucide-react';

interface EmptyStateProps {
  onQuickSearch: (sampleQuery: string) => void;
}

export default function EmptyState({ onQuickSearch }: EmptyStateProps) {
  const sampleQueries: string[] = [
    "chest pain and elevated troponin",
    "diabetic peripheral neuropathy",
    "moderate cardiomegaly on chest xray",
    "migraine with visual aura",
  ];

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
    </div>
  );
}
