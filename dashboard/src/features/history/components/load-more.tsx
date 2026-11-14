type LoadMoreProps = {
  readonly hasMore: boolean;
  readonly loading: boolean;
  readonly load: () => void;
};

/** The next page of the history, after the last row shown: the API alone says whether one follows. */
export const LoadMore = ({ hasMore, loading, load }: LoadMoreProps) => {
  if (!hasMore) {
    return null;
  }
  return (
    <button
      type="button"
      onClick={load}
      disabled={loading}
      className="mt-4 rounded border border-slate-300 bg-white px-3 py-1 hover:bg-slate-100 disabled:text-slate-400"
    >
      {loading ? 'Caricamento…' : 'Carica altri'}
    </button>
  );
};
