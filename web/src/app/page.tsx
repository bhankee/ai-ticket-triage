"use client";

import React, { useEffect, useMemo, useState } from "react";
import Header from "./components/Header";
import TicketsSummary from "./components/TicketsSummary";
import type { Stats } from "./components/TicketsSummary";

type Ticket = {
  ticket_id: number;
  created_at: string;
  source: string;
  customer: string;
  priority: string;

  category?: string | null;
  severity?: string | null;
  summary?: string | null;
  confidence?: number | null;
  needs_human_review?: number | null; // 0/1
  suggested_next_steps?: string[] | string | null;
  redacted_text?: string | null;
};

function fmtPct(x?: number | null) {
  if (x === null || x === undefined) return "—";
  return `${Math.round(x * 100)}%`;
}

function normalizeSteps(t: Ticket): string[] {
  const v = t.suggested_next_steps;

  // Already an array
  if (Array.isArray(v)) return v.map(String);

  // JSON string
  if (typeof v === "string" && v.trim().length > 0) {
    try {
      const parsed = JSON.parse(v);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  }

  return [];
}

export default function HomePage() {
  const [items, setItems] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [needsReviewOnly, setNeedsReviewOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const url = new URL("/tickets", apiBase);
        if (needsReviewOnly) url.searchParams.set("needs_review", "1");

        const res = await fetch(url.toString(), { cache: "no-store" });
        if (!res.ok) throw new Error(`API error ${res.status}`);
        const data = await res.json();

        const newItems = (data.items ?? []) as Ticket[];
        setItems(newItems);

        // @ts-ignore
        window.__tickets = newItems;
        console.log("tickets count", newItems.length);
      } catch (e: any) {
        setError(e?.message ?? "Failed to load");
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [apiBase, needsReviewOnly]);

  const sorted = useMemo(() => items, [items]);

  const stats = useMemo<Stats>(() => {
    const categoryCounts = new Map<string, number>();

    for (const ticket of items) {
      const category = ticket.category?.trim() || "Uncategorized";
      categoryCounts.set(category, (categoryCounts.get(category) ?? 0) + 1);
    }

    const categories = Array.from(categoryCounts.entries())
      .map(([category, n]) => ({ category, n }))
      .sort((a, b) => b.n - a.n);

    return {
      total: items.length,
      needs_review: items.filter((ticket) => ticket.needs_human_review === 1)
        .length,
      categories,
    };
  }, [items]);

  return (
    <main className="min-h-screen p-6">
      <div className="mx-auto max-w-6xl">
        <Header
          needsReviewOnly={needsReviewOnly}
          setNeedsReviewOnly={setNeedsReviewOnly}
          apiBase={apiBase}
        />
        <TicketsSummary stats={stats} />

        {loading && <div className="text-sm text-gray-500">Loading…</div>}
        {error && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="overflow-x-auto rounded border">
            <table className="w-full border-collapse text-sm">
              <thead className="bg-gray-100 text-left">
                <tr className="border-b border-gray-200">
                  <th className="p-3 text-xs font-semibold uppercase tracking-wide text-gray-700">
                    Ticket
                  </th>
                  <th className="p-3 text-xs font-semibold uppercase tracking-wide text-gray-700">
                    Deterministic
                  </th>
                  <th className="p-3 text-xs font-semibold uppercase tracking-wide text-gray-700">
                    LLM Assist
                  </th>
                  <th className="p-3 text-xs font-semibold uppercase tracking-wide text-gray-700">
                    Actions
                  </th>
                </tr>
              </thead>

              <tbody>
                {sorted.map((ticket) => {
                  const isExpanded = !!expanded[ticket.ticket_id];
                  const steps = normalizeSteps(ticket);

                  // LLM exists if any of the unified fields exist
                  const hasLLM =
                    !!ticket.summary ||
                    !!ticket.category ||
                    !!ticket.severity ||
                    steps.length > 0 ||
                    (ticket.confidence !== null &&
                      ticket.confidence !== undefined);

                  return (
                    <React.Fragment key={ticket.ticket_id}>
                      <tr className="border-t align-top">
                        <td className="p-3">
                          <div className="font-medium">#{ticket.ticket_id}</div>
                          <div className="text-gray-600">{ticket.customer}</div>
                          <div className="text-gray-500">
                            {ticket.source} • {ticket.priority} •{" "}
                            {ticket.created_at}
                          </div>
                        </td>

                        <td className="p-3">
                          <div className="mb-2">
                            <span className="inline-flex items-center rounded-full border border-gray-300 bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-800">
                              {ticket.category ?? "—"}
                            </span>{" "}
                            {ticket.needs_human_review ? (
                              <span className="inline-flex items-center rounded-full border border-red-300 bg-red-100 px-2.5 py-1 text-xs font-medium text-red-900">
                                Needs review
                              </span>
                            ) : (
                              <span className="ml-2 inline-flex items-center rounded-full border border-emerald-300 bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-900">
                                OK
                              </span>
                            )}
                          </div>
                          <div className="text-gray-500">
                            {ticket.summary ?? "—"}
                          </div>
                        </td>

                        <td className="p-3">
                          {!hasLLM ? (
                            <div className="text-gray-400">
                              No LLM suggestion yet
                            </div>
                          ) : (
                            <>
                              <div className="mb-2 flex flex-wrap items-center gap-2">
                                {ticket.severity && (
                                  <span className="inline-flex items-center rounded-full border border-blue-300 bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-900">
                                    {ticket.severity}
                                  </span>
                                )}
                                {ticket.category && (
                                  <span className="inline-flex items-center rounded-full border border-purple-300 bg-purple-100 px-2.5 py-1 text-xs font-medium text-purple-900">
                                    {ticket.category}
                                  </span>
                                )}
                                {ticket.confidence !== null && (
                                  <span className="inline-flex items-center rounded-full border border-gray-300 bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-800">
                                    conf {fmtPct(ticket.confidence)}
                                  </span>
                                )}
                              </div>

                              <div className="text-gray-500">
                                {ticket.summary ?? "N/A"}
                              </div>
                            </>
                          )}
                        </td>

                        <td className="p-3">
                          <button
                            className="inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition-colors hover:border-slate-400 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-1"
                            onClick={() =>
                              setExpanded((prev) => ({
                                ...prev,
                                [ticket.ticket_id]: !prev[ticket.ticket_id],
                              }))
                            }
                          >
                            {isExpanded ? "Hide" : "Details"}
                          </button>
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr className="border-t bg-slate-50/70">
                          <td className="p-3" colSpan={4}>
                            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                              <div className="grid gap-4 md:grid-cols-2">
                                <div>
                                  <div className="mb-1 text-xs font-semibold text-slate-600">
                                    Redacted Text
                                  </div>
                                  <div className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-white/90 p-3 text-sm text-slate-800 shadow-sm">
                                    {ticket.redacted_text ?? "N/A"}
                                  </div>
                                </div>

                                <div>
                                  <div className="mb-1 text-xs font-semibold text-slate-600">
                                    LLM Suggested Next Steps
                                  </div>
                                  <div className="rounded-lg border border-slate-200 bg-white/90 p-3 shadow-sm">
                                    {steps.length === 0 ? (
                                      <div className="text-sm text-gray-400">
                                        —
                                      </div>
                                    ) : (
                                      <ol className="list-decimal pl-5 text-sm text-gray-800">
                                        {steps.map((step, idx) => (
                                          <li
                                            key={`${ticket.ticket_id}-${idx}`}
                                            className="mb-1"
                                          >
                                            {step}
                                          </li>
                                        ))}
                                      </ol>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
