"use client";

import { useEffect, useState } from "react";
import type { EventItem } from "@/lib/queries";
import { shortTime } from "@/lib/format";

const SEVERITY: Record<EventItem["severity"], { dot: string; text: string }> = {
  info: { dot: "#22d3ee", text: "text-slate-300" },
  warn: { dot: "#eab308", text: "text-amber-200" },
  crit: { dot: "#f43f5e", text: "text-rose-200" },
};

export default function LiveEventTicker({ events }: { events: EventItem[] }) {
  const [cursor, setCursor] = useState(0);

  useEffect(() => {
    if (events.length === 0) return;
    const id = setInterval(() => setCursor((c) => (c + 1) % events.length), 2600);
    return () => clearInterval(id);
  }, [events.length]);

  if (events.length === 0) {
    return <p className="text-[11px] text-slate-500">No events in the last window.</p>;
  }

  const ordered = [...events.slice(cursor), ...events.slice(0, cursor)];
  const head = events[cursor % events.length];
  const tone = SEVERITY[head.severity];

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/60 px-2.5 py-2">
        <span className="relative flex h-2 w-2">
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-70"
            style={{ background: tone.dot }}
          />
          <span
            className="relative inline-flex h-2 w-2 rounded-full"
            style={{ background: tone.dot }}
          />
        </span>
        <span className="mono text-[9.5px] uppercase tracking-widest text-slate-400">live</span>
        <span className={`mono truncate text-[10.5px] ${tone.text}`}>{head.kind}</span>
        <span className="mono ml-auto shrink-0 text-[9.5px] text-slate-500">
          {shortTime(head.ts)}
        </span>
      </div>

      <ul className="flex-1 space-y-2 overflow-hidden">
        {ordered.slice(0, 6).map((event) => {
          const s = SEVERITY[event.severity];
          return (
            <li key={event.id} className="flex items-start gap-2">
              <span
                className="mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full"
                style={{ background: s.dot }}
              />
              <div className="min-w-0">
                <p className="truncate text-[11px] text-slate-300">{event.message}</p>
                <p className="mono text-[9px] uppercase tracking-wider text-slate-600">
                  {event.kind} {"\u00B7"} {shortTime(event.ts)}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
