export type Stats = {
  total: number;
  needs_review: number;
  categories: { category: string; n: number }[];
};

type TicketsSummaryProps = {
  stats: Stats;
};

const TicketsSummary = ({ stats }: TicketsSummaryProps) => {
  const { total, needs_review, categories } = stats;

  return (
    <>
      <div className="mt-6 grid gap-4 grid-cols-1 md:grid-cols-3">
        <div className="rounded-2xl shadow p-4">
          <div className="text-sm text-gray-500">Total tickets</div>
          <div className="text-2xl font-semibold">{total}</div>
        </div>
        <div className="rounded-2xl shadow p-4">
          <div className="text-sm text-gray-500">Needs human review</div>
          <div className="text-2xl font-semibold">{needs_review}</div>
        </div>
        <div className="rounded-2xl shadow p-4">
          <div className="text-sm text-gray-500">Top categories</div>
          <div className="mt-2 space-y-1">
            {categories.slice(0, 4).map((cat, ind) => (
              <div
                key={`${cat.category}-${ind}`}
                className="flex justify-between text-sm"
              >
                <span>{cat.category}</span>
                <span className="font-medium">{cat.n}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
};

export default TicketsSummary;
