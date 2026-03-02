type HeaderProps = {
  needsReviewOnly: boolean;
  setNeedsReviewOnly: (value: boolean) => void;
  apiBase: string;
};

const Header = ({
  needsReviewOnly,
  setNeedsReviewOnly,
  apiBase,
}: HeaderProps) => {
  return (
    <header className="mb-6 flex items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold">AI Ticket Triage</h1>
      </div>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            checked={needsReviewOnly}
            onChange={(e) => setNeedsReviewOnly(e.target.checked)}
          />
          Needs review only
        </label>

        <a
          className="inline-flex items-center rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 shadow-sm transition-colors hover:border-indigo-300 hover:bg-indigo-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-1"
          href={`${apiBase}/docs`}
          target="_blank"
          rel="noreferrer"
        >
          API Docs
        </a>
      </div>
    </header>
  );
};

export default Header;
