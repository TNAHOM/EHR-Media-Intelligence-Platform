import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { PaginationMeta } from '../services/api';

interface PaginationProps {
  pagination: PaginationMeta;
  onPageChange: (newPage: number) => void;
  onPageSizeChange: (newPageSize: number) => void;
  isLoading?: boolean;
}

export default function Pagination({
  pagination,
  onPageChange,
  onPageSizeChange,
  isLoading = false,
}: PaginationProps) {
  const { total_records, page, page_size, total_pages, has_next, has_previous } = pagination;

  if (total_records === 0) return null;

  const startRecord = (page - 1) * page_size + 1;
  const endRecord = Math.min(page * page_size, total_records);

  // Generate page numbers with ellipses
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 7;

    if (total_pages <= maxVisible) {
      for (let i = 1; i <= total_pages; i++) {
        pages.push(i);
      }
    } else {
      if (page <= 4) {
        for (let i = 1; i <= 5; i++) {
          pages.push(i);
        }
        pages.push('...');
        pages.push(total_pages);
      } else if (page >= total_pages - 3) {
        pages.push(1);
        pages.push('...');
        for (let i = total_pages - 4; i <= total_pages; i++) {
          pages.push(i);
        }
      } else {
        pages.push(1);
        pages.push('...');
        pages.push(page - 1);
        pages.push(page);
        pages.push(page + 1);
        pages.push('...');
        pages.push(total_pages);
      }
    }
    return pages;
  };

  const pageNumbers = getPageNumbers();

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 sm:px-6 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4 select-none">
      {/* Range & Page Size Controls */}
      <div className="flex items-center gap-4 text-xs text-slate-600 w-full sm:w-auto justify-between sm:justify-start">
        <span>
          Showing <strong className="text-slate-900 font-semibold">{startRecord}</strong>–
          <strong className="text-slate-900 font-semibold">{endRecord}</strong> of{' '}
          <strong className="text-slate-900 font-semibold">{total_records}</strong> records
        </span>

        <div className="flex items-center gap-1.5 pl-2 border-l border-slate-200">
          <span className="text-slate-400 text-[11px]">Rows:</span>
          <select
            value={page_size}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            disabled={isLoading}
            className="bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-slate-400 cursor-pointer disabled:opacity-50"
          >
            <option value={5}>5 / page</option>
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>
      </div>

      {/* Navigation Buttons */}
      <div className="flex items-center gap-1">
        {/* First Page */}
        <button
          type="button"
          onClick={() => onPageChange(1)}
          disabled={!has_previous || isLoading}
          title="First Page"
          className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-colors cursor-pointer"
        >
          <ChevronsLeft className="h-4 w-4" />
        </button>

        {/* Previous Page */}
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={!has_previous || isLoading}
          title="Previous Page"
          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-colors cursor-pointer mr-1"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          <span className="hidden xs:inline">Prev</span>
        </button>

        {/* Page Numbers */}
        <div className="flex items-center gap-1">
          {pageNumbers.map((num, idx) => {
            if (num === '...') {
              return (
                <span key={`ellipsis-${idx}`} className="px-2 py-1 text-slate-400 text-xs font-mono">
                  …
                </span>
              );
            }

            const isCurrent = num === page;
            return (
              <button
                key={`page-${num}`}
                type="button"
                onClick={() => onPageChange(Number(num))}
                disabled={isLoading || isCurrent}
                className={`min-w-[32px] h-8 flex items-center justify-center rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                  isCurrent
                    ? 'bg-slate-900 text-white font-semibold shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                } disabled:cursor-default`}
              >
                {num}
              </button>
            );
          })}
        </div>

        {/* Next Page */}
        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={!has_next || isLoading}
          title="Next Page"
          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-colors cursor-pointer ml-1"
        >
          <span className="hidden xs:inline">Next</span>
          <ChevronRight className="h-3.5 w-3.5" />
        </button>

        {/* Last Page */}
        <button
          type="button"
          onClick={() => onPageChange(total_pages)}
          disabled={!has_next || isLoading}
          title="Last Page"
          className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-colors cursor-pointer"
        >
          <ChevronsRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
