import { createRoot } from "react-dom/client";
import { InstructorAssessments } from "../src/InstructorAssessments";
import type { InstructorAssessmentsProps } from "../src/InstructorAssessments";
const format=new URL(location.href).searchParams.get("format");
const pin="a".repeat(64), event="c".repeat(64);
const reference={schema:"SH_SELECTED_HISTORY_INTEGRITY_REFERENCE_V1",kind:"ROOT_ACCEPTED_BASE",algorithm:"SH_VERIFIED_EVENT_CHAIN_AND_CANONICAL_STATE_V1",engagement_id:"NEUTRAL-E",revision:1,selected_event_sha256:event,selected_request_sha256:"d".repeat(64),state_storage:format === "V2_RAW" ? "RAW_CANONICAL_JSON" : "CANONICAL_CODEC_GRAPH",selected_state_root_sha256:format === "V2_RAW" ? null : "f".repeat(64),selected_state_sha256:pin,selected_state_bytes:37,accepted_base_sha256:"b".repeat(64),checkpoint_sha256:"b".repeat(64)};
const props={engagement:{id:"NEUTRAL-E",revision:3,permissions:["instruct"],scope:{boundaries:["NEUTRAL"]}},viewerId:"NEUTRAL-INSTRUCTOR",enabled:true,bound:{binding:{manifest_sha256:pin,bound_revision:0},snapshot:{audited_actor_id:"NEUTRAL-AUDITOR"}},history:format === "V1" ? {revision:1,state_sha256:pin,history_sha256:"e".repeat(64),event_sha256:event} : {revision:1,state_sha256:pin,event_sha256:event,history_integrity_format:"SELECTED_HISTORY_INTEGRITY_REFERENCE_V2",history_integrity_reference:reference}} as unknown as InstructorAssessmentsProps;
(window as any).neutralFixture={props,reference,format};
createRoot(document.getElementById("root")!).render(<main><h1>Neutral workroom summary</h1><p>The workroom and summary stay available after opening a private assessment.</p><InstructorAssessments {...props}/></main>);
