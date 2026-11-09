import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface SourceSettings {
  keywords: string;
  location: string;
}
export interface JobSource {
  id: string;
  slug: string;
  name: string;
  homepage: string;
  region: string;
  integration_type: string;
  legal_status: string;
  enabled: boolean;
  automation_eligible: boolean;
  manual_import_supported: boolean;
  custom: boolean;
  settings: SourceSettings;
  health_status: 'MANUAL_ONLY' | 'UNVERIFIED' | 'DISABLED';
  last_successful_sync: string | null;
  jobs_collected: number | null;
  reason: string;
}
export interface ManualJob {
  original_url: string;
  title?: string | null;
  company?: string | null;
  country?: string | null;
  city?: string | null;
  description?: string | null;
  application_url?: string | null;
  source_job_id?: string | null;
  work_mode?: string | null;
  domain?: string | null;
  experience_level?: string | null;
  min_years?: number | null;
  max_years?: number | null;
  mandatory_skills?: string[];
  optional_skills?: string[];
  visa_status?: string;
  visa_evidence?: string | null;
  published_at?: string | null;
}
export interface PreviewRow {
  row_number: number;
  job: ManualJob | null;
  errors: string[];
}
export interface CsvPreview {
  rows: PreviewRow[];
  valid_count: number;
  invalid_count: number;
}
export interface Listing extends ManualJob {
  id: string;
  source_name: string;
  first_seen_at: string;
  published_at: string | null;
  missing_fields: string[];
}
export interface ListingsPage {
  items: Listing[];
  total: number;
}
export interface ImportResult {
  created_count: number;
  existing_count: number;
}

export interface CollectionAvailability {
  source_id: string;
  name: string;
  eligible: boolean;
  reason: string;
  limits: { max_results: number; max_pages: number; duration_seconds: number };
}

@Injectable({ providedIn: 'root' })
export class SourceApi {
  private readonly http = inject(HttpClient);
  collection(id: string): Observable<CollectionAvailability> {
    return this.http.get<CollectionAvailability>(`/api/sources/${id}/collection`);
  }
  testCollection(id: string): Observable<CollectionAvailability> {
    return this.http.post<CollectionAvailability>(`/api/sources/${id}/collection/test`, {});
  }
  sources(): Observable<JobSource[]> {
    return this.http.get<JobSource[]>('/api/sources');
  }
  patch(id: string, body: { enabled?: boolean; settings?: SourceSettings }): Observable<JobSource> {
    return this.http.patch<JobSource>(`/api/sources/${id}`, body);
  }
  create(body: { name: string; homepage: string; region: string }): Observable<JobSource> {
    return this.http.post<JobSource>('/api/sources', body);
  }
  delete(id: string): Observable<void> {
    return this.http.delete<void>(`/api/sources/${id}`);
  }
  link(id: string, body: SourceSettings): Observable<{ url: string; criteria_applied: boolean }> {
    return this.http.post<{ url: string; criteria_applied: boolean }>(
      `/api/sources/${id}/search-link`,
      body,
    );
  }
  preview(source_id: string, csv_text: string): Observable<CsvPreview> {
    return this.http.post<CsvPreview>('/api/jobs/import/preview', { source_id, csv_text });
  }
  import(source_id: string, jobs: ManualJob[]): Observable<ImportResult> {
    return this.http.post<ImportResult>('/api/jobs/import', { source_id, jobs, confirm: true });
  }
  jobs(offset = 0): Observable<ListingsPage> {
    return this.http.get<ListingsPage>('/api/jobs', { params: { limit: 20, offset } });
  }
}
