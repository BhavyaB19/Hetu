import createClient from "openapi-fetch";

import type { components, paths } from "./api/schema";

type Schemas = components["schemas"];
export type CaseSummary = Schemas["CaseSummary"];
export type CaseView = Schemas["CaseView"];
export type Evidence = Schemas["Evidence"];
export type GapView = Schemas["GapView"];
export type JudgmentView = Schemas["JudgmentView"];
export type MediaView = Schemas["MediaView"];
export type PublicView = Schemas["PublicView"];
export type TimelineEventView = Schemas["TimelineEventView"];
export type SourceView = Schemas["SourceView"];
export type JobView = Schemas["JobView"];
export type PollView = Schemas["PollView"];
export type PollResultsView = Schemas["PollResultsView"];
export type VoteRequest = Schemas["VoteRequest"];
export type ReasonTally = Schemas["ReasonTally"];
export type CommentView = Schemas["CommentView"];
export type CommentRequest = Schemas["CommentRequest"];
export type CommentVoteView = Schemas["CommentVoteView"];
export type ReportRequest = Schemas["ReportRequest"];
export type ReportView = Schemas["ReportView"];
export type ListingView = Schemas["ListingView"];
export type DocketView = Schemas["DocketView"];
export type DocketDayView = Schemas["DocketDayView"];
export type DocketHighlightsView = Schemas["DocketHighlightsView"];
export type TrackedMatterView = Schemas["TrackedMatterView"];

/** The API is only called from the server, so this is never exposed to the browser. */
// 127.0.0.1 rather than localhost: Node may resolve localhost to IPv6, where uvicorn isn't listening.
export const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

/** Typed client generated from the FastAPI OpenAPI schema (`npm run gen:api`). */
export const api = createClient<paths>({ baseUrl: API_URL, cache: "no-store" });
