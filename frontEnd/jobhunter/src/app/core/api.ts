import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface Owner {
  id: string;
  email: string;
}
export interface Login {
  email: string;
  password: string;
}
export interface AuthStatus {
  authenticated: boolean;
  owner: Owner;
}
export interface Health {
  status: 'ok' | 'degraded';
  database: 'ok' | 'unavailable';
}

@Injectable({ providedIn: 'root' })
export class Api {
  private readonly http = inject(HttpClient);
  me(): Observable<Owner> {
    return this.http.get<Owner>('/api/auth/me');
  }
  account(): Observable<Owner> {
    return this.http.get<Owner>('/api/account');
  }
  login(body: Login): Observable<AuthStatus> {
    return this.http.post<AuthStatus>('/api/auth/login', body);
  }
  refresh(): Observable<AuthStatus> {
    return this.http.post<AuthStatus>('/api/auth/refresh', {});
  }
  logout(): Observable<void> {
    return this.http.post<void>('/api/auth/logout', {});
  }
  health(): Observable<Health> {
    return this.http.get<Health>('/health');
  }
}
