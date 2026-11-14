import React, { useMemo } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export const PolicyBody = ({ markdown }) => {
  const html = useMemo(() => DOMPurify.sanitize(marked.parse(markdown || '')), [markdown]);
  return <div className="policy-prose" dangerouslySetInnerHTML={{ __html: html }} data-testid="policy-body" />;
};

export default PolicyBody;
