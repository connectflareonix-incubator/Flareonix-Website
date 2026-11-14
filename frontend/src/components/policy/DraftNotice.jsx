import React from 'react';
import { FileWarning } from 'lucide-react';

export const DraftNotice = () => (
  <div className="flex gap-3 p-4 mb-8 rounded-xl border border-[#FFB300]/40 bg-[#FFB300]/10" role="note" data-testid="policy-draft-notice">
    <FileWarning className="h-5 w-5 text-[#FFB300] shrink-0 mt-0.5" />
    <p className="text-sm text-white/80">
      <strong className="text-[#FFB300]">Draft, under legal review.</strong> This policy is a working draft and may change before it is finalised.
    </p>
  </div>
);

export default DraftNotice;
