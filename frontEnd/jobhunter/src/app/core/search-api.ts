import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ManualJob } from './source-api';
import { TranslationKey } from './i18n';

export interface SearchCriteria {
  source_ids: string[];
  domains: string[];
  titles: string[];
  include_keywords: string[];
  exclude_keywords: string[];
  countries: string[];
  cities: string[];
  work_modes: ('remote' | 'hybrid' | 'onsite')[];
  experience_levels: string[];
  max_years: number;
  visa_statuses: string[];
  publication_days: 0 | 1 | 3 | 7 | 30;
  novelty: 'all' | 'today' | '24h' | '3d' | '7d' | '30d';
  unknown_policy: 'include' | 'exclude';
  mode: 'MANUAL' | 'CV' | 'HYBRID';
  linked_cv_id: string | null;
  min_score: number;
  notifications_enabled: boolean;
}
export function defaultCriteria(): SearchCriteria {
  return {
    source_ids: [],
    domains: [],
    titles: [],
    include_keywords: [],
    exclude_keywords: [],
    countries: [],
    cities: [],
    work_modes: [],
    experience_levels: ['Graduate', 'Entry Level', 'Junior'],
    max_years: 3,
    visa_statuses: [],
    publication_days: 0,
    novelty: 'all',
    unknown_policy: 'include',
    mode: 'MANUAL',
    linked_cv_id: null,
    min_score: 0,
    notifications_enabled: false,
  };
}
export interface SearchProfile {
  id: string;
  name: string;
  description: string;
  criteria: SearchCriteria;
  created_at: string;
  updated_at: string;
}
export interface ProfileInput {
  name: string;
  description: string;
  criteria: SearchCriteria;
}
export interface Execution {
  id: string;
  profile_id: string;
  profile_name: string;
  scope: 'IMPORTED_OFFERS';
  status: string;
  criteria: SearchCriteria;
  cancel_requested: boolean;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  counts: Record<string, number>;
  reason: string | null;
  stage: string;
  cursor: number;
  attempt: number;
  heartbeat_at: string | null;
  sources: { source_id: string; source_name: string; status: string; reason: string }[];
}
export interface Fact extends ManualJob {
  id: string;
  source_id: string;
  source_name: string;
  canonical_url: string;
  first_seen_at: string;
  last_seen_at: string;
  status: string;
}
export interface SearchResult {
  listing: Fact;
  unknown_fields: string[];
  group: {
    id: string;
    first_seen_at: string;
    members: Fact[];
    candidate_ids: string[];
    repost_of_id: string | null;
    novelty_verified: boolean;
    provenance: {
      listing_id: string;
      source_id: string;
      source_name: string;
      original_url: string;
      application_url: string;
    }[];
  };
}
export function activeExecution(execution: Execution): boolean {
  return ['PENDING', 'RUNNING'].includes(execution.status);
}
export function executionStatusKey(status: string): TranslationKey {
  return (
    (
      {
        PENDING: 'searchPending',
        RUNNING: 'searchRunning',
        SUCCEEDED: 'searchSucceeded',
        PARTIAL: 'searchPartial',
        FAILED: 'searchFailed',
        CANCELLED: 'searchCancelled',
        TIMED_OUT: 'searchTimedOut',
      } as Record<string, TranslationKey>
    )[status] ?? 'unknownValue'
  );
}
export function visaStatusKey(status: string): TranslationKey {
  return (
    (
      {
        CONFIRMED: 'visaConfirmed',
        POSSIBLE: 'visaPossible',
        RELOCATION: 'visaRelocation',
        NONE: 'visaNone',
      } as Record<string, TranslationKey>
    )[status] ?? 'unknownValue'
  );
}
@Injectable({ providedIn: 'root' })
export class SearchApi {
  private readonly http = inject(HttpClient);
  profiles(): Observable<SearchProfile[]> {
    return this.http.get<SearchProfile[]>('/api/search/profiles');
  }
  create(body: ProfileInput): Observable<SearchProfile> {
    return this.http.post<SearchProfile>('/api/search/profiles', body);
  }
  update(id: string, body: ProfileInput): Observable<SearchProfile> {
    return this.http.put<SearchProfile>(`/api/search/profiles/${id}`, body);
  }
  remove(id: string): Observable<void> {
    return this.http.delete<void>(`/api/search/profiles/${id}`);
  }
  duplicate(profile: SearchProfile, name: string): Observable<SearchProfile> {
    return this.http.post<SearchProfile>(`/api/search/profiles/${profile.id}/duplicate`, { name });
  }
  examples(): Observable<SearchProfile[]> {
    return this.http.post<SearchProfile[]>('/api/search/profiles/examples', {});
  }
  start(profile_id: string): Observable<Execution> {
    return this.http.post<Execution>('/api/search/executions', { profile_id });
  }
  history(): Observable<Execution[]> {
    return this.http.get<Execution[]>('/api/search/executions');
  }
  execution(id: string): Observable<Execution> {
    return this.http.get<Execution>(`/api/search/executions/${id}`);
  }
  cancel(id: string): Observable<Execution> {
    return this.http.post<Execution>(`/api/search/executions/${id}/cancel`, {});
  }
  results(
    id: string,
    offset = 0,
    sort = 'discovery',
    q = '',
  ): Observable<{ items: SearchResult[]; total: number }> {
    return this.http.get<{ items: SearchResult[]; total: number }>(
      `/api/search/executions/${id}/results`,
      { params: { offset, limit: 20, sort, q } },
    );
  }
  dashboard(): Observable<{ imported_count: number; last_execution: Execution | null }> {
    return this.http.get<{ imported_count: number; last_execution: Execution | null }>(
      '/api/search/dashboard',
    );
  }
}
