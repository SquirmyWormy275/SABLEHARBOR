import React from "react";
import { createRoot } from "react-dom/client";
import { SavedViews } from "../src/SavedViews";
import { VisitCheckpoint } from "../src/VisitCheckpoint";
import { InvestigationContexts } from "../src/InvestigationContexts";
import { InvestigationHandoffs } from "../src/InvestigationHandoffs";
import { BackgroundWork } from "../src/BackgroundWork";
import type { Engagement } from "../src/api";
const empty = { controls: [], people: [], tasks: [], requests: [], artifacts: [], meetings: [], notes: [], populations: [], selections: [], calendar: [], findings: [], workpapers: [], reviews: [], surveys: [], events: [] };
const state = { ...empty, id: "NEUTRAL-E", title: "Neutral temporary fixture", revision: 1, discipline: "engineering", mode: "CLEAN", phase: "WORK", simulated_at: "2026-01-01T00:00:00Z", scope: { programs: ["SOC2"], boundaries: ["neutral"], period_start: "2026-01-01", period_end: "2026-12-31", report_type: "neutral" }, permissions: ["learn"], capabilities: {}, company_source_binding: { branch: "neutral-a" }, evidence_acquisition: { mode: "neutral" } } as Engagement;
const root = createRoot(document.getElementById("root")!);
let engagement = state, viewerId = "NEUTRAL-U";
const noop = () => {};
function render() { root.render(<>
  <SavedViews engagement={engagement} viewerId={viewerId} enabled={true} getNavigation={() => ({ section: "controls", query: "", framework: "", scroll_top: 0 })} onRestore={noop} />
  <VisitCheckpoint engagement={engagement} viewerId={viewerId} onPreview={noop} />
  <InvestigationContexts engagement={engagement} viewerId={viewerId} onPreview={noop} />
  <InvestigationHandoffs engagement={engagement} viewerId={viewerId} enabled={true} onPreview={noop} />
  <details className="background-work-panel"><summary>Background work fixture</summary><BackgroundWork engagement={engagement} viewerId={viewerId} onInspect={noop} onCompleted={noop} /></details>
</>); }
(window as any).changeFixture = (patch: Partial<Engagement>, viewer?: string) => { engagement = { ...engagement, ...patch }; if (viewer) viewerId = viewer; render(); };
(window as any).getFixture = () => engagement;
render();
