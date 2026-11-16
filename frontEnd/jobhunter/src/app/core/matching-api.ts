import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Execution } from './search-api';

export interface MatchingRun {
  id: string;
  candidate_id: string;
  candidate_revision: number;
  policy_version: number;
  policy_id: string;
  status: string;
  cursor: number;
  total: number;
  cache_hits: number;
}
export interface MatchingCapabilities {
  ready: boolean;
  reason: string;
  candidate_id?: string;
  candidate_revision?: number;
}
export interface ScoringPolicy {
  weights: Record<string, number>;
  mandatory_cap: number;
}
export interface PolicyVersion {
  id: string;
  version: number;
  policy: ScoringPolicy;
}
export interface MatchPreview {
  score: number;
  uncapped_score: number;
  coverage: number;
  provisional: true;
  confidence: 'LOW';
  calibration_status: 'UNVALIDATED';
  scoring_version: string;
  components: {
    name: string;
    weight: number;
    points: number;
    state: string;
    matched: string[];
    unattested: string[];
  }[];
  cap_reasons: string[];
  warnings: string[];
  analysis: { evidence: { field: string; value: string; quote: string; origin: string }[] };
}
export interface MatchItem {
  group_id: string;
  preview: MatchPreview;
}
@Injectable({ providedIn: 'root' })
export class MatchingApi {
  private readonly http = inject(HttpClient);
  capabilities(): Observable<MatchingCapabilities> {
    return this.http.get<MatchingCapabilities>('/api/matching/capabilities');
  }
  policies(): Observable<PolicyVersion[]> {
    return this.http.get<PolicyVersion[]>('/api/matching/policies');
  }
  savePolicy(body: ScoringPolicy): Observable<PolicyVersion> {
    return this.http.post<PolicyVersion>('/api/matching/policies', body);
  }
  start(
    profile_id: string,
    candidate_id: string,
    policy_id: string,
    source_execution_id?: string,
  ): Observable<Execution> {
    return this.http.post<Execution>('/api/search/executions', {
      profile_id,
      matching_preview: true,
      expected_candidate_id: candidate_id,
      ...(policy_id ? { policy_id } : {}),
      ...(source_execution_id ? { scope: 'MATCHING_ONLY', source_execution_id } : {}),
    });
  }
  page(execution: string, groups: string[]): Observable<{ run: MatchingRun; items: MatchItem[] }> {
    return this.http.get<{ run: MatchingRun; items: MatchItem[] }>(
      `/api/matching/executions/${execution}`,
      {
        params: { group_id: groups, limit: 20 },
      },
    );
  }
}
