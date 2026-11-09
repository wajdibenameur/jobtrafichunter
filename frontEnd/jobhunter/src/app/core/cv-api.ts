import { HttpClient, HttpEvent } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface CvVersion {
  id: string;
  document_id: string;
  number: number;
  filename: string;
  byte_size: number;
  state: string;
  analysis_status: string;
  active: boolean;
  created_at: string;
}
export interface CvInspection {
  status: 'TEXT' | 'NEEDS_OCR';
  kind: string;
  pages: { number: number; text: string }[];
}
export interface CandidateFields {
  professional_title: string | null;
  summary: string | null;
  years_experience: number | null;
  education: string[];
  experiences: string[];
  languages: string[];
  certifications: string[];
  skills: Record<string, string[]>;
}
export interface CandidatePreferences {
  locations: string[];
  domains: string[];
  target_levels: string[];
  visa_needed: boolean | null;
}
export interface Candidate {
  id: string;
  cv_version_id: string;
  parent_id: string | null;
  revision: number;
  status: string;
  active: boolean;
  created_at: string;
  validated_at: string | null;
  data: {
    fields: CandidateFields;
    preferences: CandidatePreferences;
    evidence: Record<string, { page: number; start: number; end: number; quote: string }[]>;
    origins: Record<string, string>;
    warnings: string[];
  };
  changed_fields: string[];
  unknown_fields: string[];
}
@Injectable({ providedIn: 'root' })
export class CvApi {
  private readonly http = inject(HttpClient);
  versions(): Observable<CvVersion[]> {
    return this.http.get<CvVersion[]>('/api/cvs');
  }
  capabilities(): Observable<{ ready: boolean }> {
    return this.http.get<{ ready: boolean }>('/api/cvs/capabilities');
  }
  upload(file: File, document?: string): Observable<HttpEvent<CvVersion>> {
    const mime = file.name.toLowerCase().endsWith('.pdf')
      ? 'application/pdf'
      : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    return this.http.post<CvVersion>(
      document ? `/api/cvs/${document}/versions` : '/api/cvs',
      file,
      {
        headers: { 'Content-Type': mime, 'X-CV-Filename': encodeURIComponent(file.name) },
        observe: 'events',
        reportProgress: true,
      },
    );
  }
  inspection(id: string): Observable<{ version: CvVersion; inspection: CvInspection }> {
    return this.http.get<{ version: CvVersion; inspection: CvInspection }>(
      `/api/cvs/versions/${id}`,
    );
  }
  download(id: string): Observable<Blob> {
    return this.http.get(`/api/cvs/versions/${id}/download`, { responseType: 'blob' });
  }
  remove(document: string): Observable<void> {
    return this.http.delete<void>(`/api/cvs/${document}`);
  }
  profiles(version: string): Observable<Candidate[]> {
    return this.http.get<Candidate[]>(`/api/candidate-profiles/versions/${version}`);
  }
  generate(version: string, regenerate = false): Observable<Candidate> {
    return this.http.post<Candidate>(`/api/candidate-profiles/versions/${version}/generate`, {
      regenerate,
    });
  }
  edit(
    id: string,
    fields: CandidateFields,
    preferences: CandidatePreferences,
  ): Observable<Candidate> {
    return this.http.post<Candidate>(`/api/candidate-profiles/${id}/revisions`, {
      fields,
      preferences,
    });
  }
  validate(id: string): Observable<Candidate> {
    return this.http.post<Candidate>(`/api/candidate-profiles/${id}/validate`, { reviewed: true });
  }
  activate(id: string): Observable<Candidate> {
    return this.http.post<Candidate>(`/api/candidate-profiles/${id}/activate`, {});
  }
  export(id: string): Observable<Blob> {
    return this.http.get(`/api/candidate-profiles/versions/${id}/export`, { responseType: 'blob' });
  }
}
