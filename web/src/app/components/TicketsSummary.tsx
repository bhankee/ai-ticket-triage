import type { Stats } from "../page";

type TicketsSummaryProps = {
  stats: Stats;
};

const TicketsSummary = ({ stats }: TicketsSummaryProps) => {
  return (
    <>
      <div className="mt-6 grid gap-4 grid-cols-1 md:grid-cols-3">
        <div className="rounded-2xl shadow p-4">
          <div className="text-sm text-gray-500">Total tickets</div>
          <div className="text-2xl font-semibold">{stats.total}</div>
        </div>
        <div className="rounded-2xl shadow p-4">
          <div className="text-sm text-gray-500">Needs human review</div>
          <div className="text-2xl font-semibold">{stats.needs_review}</div>
        </div>
        <div className="rounded-2xl shadow p-4">
          <div className="text-sm text-gray-500">Top categories</div>
          <div className="mt-2 space-y-1">
            {stats.categories.slice(0, 4).map((c, ind) => (
              <div
                key={`${c.category}-${ind}`}
                className="flex justify-between text-sm"
              >
                <span>{c.category}</span>
                <span className="font-medium">{c.n}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
};

export default TicketsSummary;
