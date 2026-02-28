import Header from "./components/Header";
import TicketsSummary from "./components/TicketsSummary";

export type Stats = {
  total: number;
  needs_review: number;
  categories: { category: string; n: number }[];
};

type Ticket = {
  ticket_id: number;
  created_at: string;
  source: string;
  customer: string;
  priority: string;
  category: string;
  needs_human_review: number;
  summary: string;
  redacted_text: string;
};

async function getJSON<T>(path: string): Promise<T> {
  const base = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
  const res = await fetch(`${base}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed: ${res.status} ${path}`);
  return res.json();
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full px-2 py-1 text-xs bg-gray-100">
      {children}
    </span>
  );
}

export default async function Home() {
  const stats = await getJSON<Stats>("/stats");
  const data = await getJSON<{ items: Ticket[] }>("/tickets");
  const items = data.items;

  return (
    <main className="min-h-screen p-6 max-w-6xl mx-auto">
      <Header />
      <TicketsSummary stats={stats} />
      <h2 className="text-xl font-semibold mt-10">Tickets</h2>
      <div className="mt-4 overflow-x-auto rounded-2xl shadow">
        <table className="w-full text-sm">
          <thead className="bg-gray-600">
            <tr>
              <th className="text-left p-3">Ticket</th>
              <th className="text-left p-3">Priority</th>
              <th className="text-left p-3">Category</th>
              <th className="text-left p-3">Review</th>
              <th className="text-left p-3">Customer</th>
              <th className="text-left p-3">Summary</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t, ind) => (
              <tr key={`${t.ticket_id}-${ind}`} className="border-t align-top">
                <td className="p-3 font-medium">#{t.ticket_id}</td>
                <td className="p-3">
                  <Pill>
                    <span className="text-blue-700">{t.priority}</span>
                  </Pill>
                </td>
                <td className="p-3">{t.category}</td>
                <td className="p-3">
                  {t.needs_human_review === 1 ? (
                    <span className="inline-flex items-center rounded-full px-2 py-1 text-xs bg-red-400">
                      Needs review
                    </span>
                  ) : (
                    <span className="inline-flex items-center rounded-full px-2 py-1 text-xs bg-green-500">
                      Auto ok
                    </span>
                  )}
                </td>
                <td className="p-3">{t.customer}</td>
                <td className="p-3 max-w-xl">{t.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
