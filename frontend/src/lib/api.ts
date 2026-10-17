import {
  AnalysisResponse,
  ChangesResponse,
  DataMode,
  EventCategory,
  EventDetailResponse,
  EventListResponse,
  HealthResponse,
  ProcessingResponse,
  SourcesResponse,
  TimelineResponse,
} from "./types";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...options?.headers,
    },
    // Don't cache in dev to always get fresh data
    cache: "no-store",
  });

  if (!res.ok) {
    let errorData: unknown;
    try {
      errorData = await res.json();
    } catch {
      errorData = await res.text();
    }
    const message =
      typeof errorData === "object" && errorData !== null && "message" in errorData
        ? String((errorData as { message: unknown }).message)
        : `Request to ${endpoint} failed with status ${res.status}`;
    throw new ApiError(message, res.status, errorData);
  }

  return res.json() as Promise<T>;
}

export interface ListEventsParams {
  category?: EventCategory;
  location?: string;
  location_province?: string;
  location_city?: string;
  data_mode?: DataMode;
  q?: string;
  limit?: number;
  offset?: number;
  since?: string;
}

export const api = {
  /**
   * List canonical events ordered by importance_score DESC.
   */
  async listEvents(params?: ListEventsParams): Promise<EventListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set("category", params.category);
    if (params?.location) searchParams.set("location", params.location);
    if (params?.location_province)
      searchParams.set("location_province", params.location_province);
    if (params?.location_city)
      searchParams.set("location_city", params.location_city);
    if (params?.data_mode) searchParams.set("data_mode", params.data_mode);
    if (params?.q) searchParams.set("q", params.q);
    if (params?.limit !== undefined)
      searchParams.set("limit", String(params.limit));
    if (params?.offset !== undefined)
      searchParams.set("offset", String(params.offset));
    if (params?.since) searchParams.set("since", params.since);

    const query = searchParams.toString();
    const endpoint = query ? `/events?${query}` : "/events";
    return fetchJson<EventListResponse>(endpoint);
  },

  /**
   * Get single event detail with grounded 5-Ws, actions, confidence.
   */
  async getEvent(id: string): Promise<EventDetailResponse> {
    return fetchJson<EventDetailResponse>(`/events/${encodeURIComponent(id)}`);
  },

  /**
   * Get chronological timeline entries for an event.
   */
  async getEventTimeline(
    id: string,
    snapshotId?: string
  ): Promise<TimelineResponse> {
    const query = snapshotId ? `?snapshot_id=${encodeURIComponent(snapshotId)}` : "";
    return fetchJson<TimelineResponse>(
      `/events/${encodeURIComponent(id)}/timeline${query}`
    );
  },

  /**
   * Get news sources and media family grouping for an event.
   */
  async getEventSources(id: string): Promise<SourcesResponse> {
    return fetchJson<SourcesResponse>(
      `/events/${encodeURIComponent(id)}/sources`
    );
  },

  /**
   * Get what changed (deltas) between snapshots for an event.
   */
  async getEventChanges(
    id: string,
    fromSnapshotId?: string,
    toSnapshotId?: string
  ): Promise<ChangesResponse> {
    const searchParams = new URLSearchParams();
    if (fromSnapshotId) searchParams.set("from_snapshot_id", fromSnapshotId);
    if (toSnapshotId) searchParams.set("to_snapshot_id", toSnapshotId);
    const query = searchParams.toString();
    const endpoint = query
      ? `/events/${encodeURIComponent(id)}/changes?${query}`
      : `/events/${encodeURIComponent(id)}/changes`;
    return fetchJson<ChangesResponse>(endpoint);
  },

  /**
   * Get analysis including conflicts and confidence breakdown.
   */
  async getEventAnalysis(id: string): Promise<AnalysisResponse> {
    return fetchJson<AnalysisResponse>(
      `/events/${encodeURIComponent(id)}/analysis`
    );
  },

  /**
   * Get processing funnel audit data (Screen 3: Processing & Evidence).
   */
  async getEventProcessing(id: string): Promise<ProcessingResponse> {
    return fetchJson<ProcessingResponse>(
      `/events/${encodeURIComponent(id)}/processing`
    );
  },

  /**
   * Get backend system health.
   */
  async getHealth(): Promise<HealthResponse> {
    return fetchJson<HealthResponse>("/health");
  },
};
