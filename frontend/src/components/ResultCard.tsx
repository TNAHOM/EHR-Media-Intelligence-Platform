import { FileText, Activity, Sparkles, ChevronRight, User, Calendar, LucideIcon, CheckCircle2 } from 'lucide-react';
import { SearchResultItem } from '../services/api';

interface ResultCardProps {
  item: SearchResultItem;
  onSelectPatient: () => void;
}

interface ScoreBadge {
  bg: string;
  label: string;
}

interface ResourceTag {
  icon: LucideIcon;
  label: string;
  style: string;
}

export default function ResultCard({ item, onSelectPatient }: ResultCardProps) {
  // Score Badge styling (only for semantic search matches)
  const isSearchMatch = Boolean(item.isSearchMatch && typeof item.relevance_score === 'number');
  const scorePercent = isSearchMatch ? Math.round((item.relevance_score || 0) * 100) : null;

  const getScoreBadge = (score: number): ScoreBadge => {
    if (score >= 0.30) {
      return { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'High Match' };
    }
    if (score >= 0.15) {
      return { bg: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Moderate' };
    }
    return { bg: 'bg-slate-100 text-slate-600 border-slate-200', label: 'Low Relevance' };
  };

  const badge = isSearchMatch && typeof item.relevance_score === 'number'
    ? getScoreBadge(item.relevance_score)
    : null;

  // Resource Type Tag styling
  const getResourceTag = (type: string, category?: string): ResourceTag => {
    if (type === 'DocumentReference') {
      return {
        icon: FileText,
        label: category === 'discharge_summary' ? 'Discharge Summary' : 'Clinical Note',
        style: 'bg-sky-50 text-sky-700 border-sky-200',
      };
    }
    if (type === 'DiagnosticReport') {
      return {
        icon: Activity,
        label: category === 'imaging' ? 'Imaging / Radiology' : 'Lab Diagnostic',
        style: 'bg-teal-50 text-teal-700 border-teal-200',
      };
    }
    return {
      icon: Sparkles,
      label: 'AI Clinical Summary',
      style: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    };
  };

  const resourceInfo = getResourceTag(item.resource_type, item.record_type);
  const IconComponent = resourceInfo.icon;

  return (
    <div
      onClick={onSelectPatient}
      className="group bg-white rounded-xl border border-slate-200 p-5 hover:border-slate-300 hover:shadow-md transition-all cursor-pointer space-y-3"
    >
      {/* Card Header: Metadata Badges & Relevance / Status */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${resourceInfo.style}`}>
            <IconComponent className="h-3.5 w-3.5" />
            {resourceInfo.label}
          </span>
          <span className="text-xs text-slate-400">•</span>
          <span className="inline-flex items-center gap-1 text-xs text-slate-500 font-mono">
            <User className="h-3 w-3" /> {item.patient_mrn}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {badge && scorePercent !== null ? (
            <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${badge.bg}`}>
              {scorePercent}% {badge.label}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium text-slate-500 bg-slate-50 border border-slate-200">
              <CheckCircle2 className="h-3 w-3 text-emerald-600" /> Standard Record
            </span>
          )}
        </div>
      </div>

      {/* Patient Name & Date */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors text-base">
          {item.patient_name}
        </h3>
        <span className="inline-flex items-center gap-1 text-xs text-slate-400">
          <Calendar className="h-3 w-3" /> {item.record_date}
        </span>
      </div>

      {/* Snippet */}
      <p className="text-xs text-slate-600 leading-relaxed line-clamp-3 bg-slate-50 p-3 rounded-lg border border-slate-100 font-mono">
        {item.snippet}
      </p>

      {/* Action Footer */}
      <div className="pt-1 flex items-center justify-between text-xs text-slate-500">
        <span className="text-[11px] text-slate-400">Click to view complete FHIR chart & AI synthesis</span>
        <span className="inline-flex items-center gap-1 font-medium text-slate-700 group-hover:text-indigo-600 transition-colors">
          Open Record <ChevronRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
        </span>
      </div>
    </div>
  );
}

