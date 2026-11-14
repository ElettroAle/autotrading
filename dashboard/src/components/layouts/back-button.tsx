import { useLocation, useNavigate } from 'react-router';

import { paths } from '@/config/paths';

// The router gives the key «default» only to the page the dashboard was opened on: there is no page of the dashboard
// to go back to, and going back would leave it (ADR 0145).
const FIRST_PAGE_KEY = 'default';

/** Back to the previous page of the dashboard, or to the main page when there is none (ADR 0145). */
export const BackButton = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const goBack = () => {
    if (location.key === FIRST_PAGE_KEY) {
      void navigate(paths.home.getHref());
      return;
    }
    void navigate(-1);
  };
  return (
    <button
      type="button"
      onClick={goBack}
      className="inline-flex min-h-11 min-w-11 items-center justify-center gap-1 rounded border border-slate-300 px-2 text-sm"
    >
      <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path d="M12.7 4.3a1 1 0 0 1 0 1.4L8.4 10l4.3 4.3a1 1 0 0 1-1.4 1.4l-5-5a1 1 0 0 1 0-1.4l5-5a1 1 0 0 1 1.4 0Z" />
      </svg>
      Indietro
    </button>
  );
};
