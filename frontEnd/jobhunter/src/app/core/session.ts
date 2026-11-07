import { HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { catchError, finalize, map, Observable, of, shareReplay, tap, throwError } from 'rxjs';
import { Api, Login, Owner } from './api';

export type SessionState = 'unknown' | 'loading' | 'authenticated' | 'anonymous' | 'unavailable';

@Injectable({ providedIn: 'root' })
export class Session {
  private readonly api = inject(Api);
  private readonly currentOwner = signal<Owner | null>(null);
  private readonly currentState = signal<SessionState>('unknown');
  readonly owner = this.currentOwner.asReadonly();
  readonly state = this.currentState.asReadonly();
  private checkFlight?: Observable<Owner | null>;
  private refreshFlight?: Observable<Owner>;
  private generation = 0;

  check(): Observable<Owner | null> {
    if (this.checkFlight) return this.checkFlight;
    const generation = this.generation;
    this.currentState.set('loading');
    this.checkFlight = this.api.me().pipe(
      tap((owner) => this.accept(owner, generation)),
      catchError((error: unknown) => {
        if (this.generation === generation) this.reject(error);
        return of(null);
      }),
      finalize(() => {
        this.checkFlight = undefined;
      }),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    return this.checkFlight;
  }
  login(credentials: Login): Observable<Owner> {
    const generation = ++this.generation;
    return this.api.login(credentials).pipe(
      map((status) => status.owner),
      tap((owner) => this.accept(owner, generation)),
    );
  }
  refresh(): Observable<Owner> {
    if (this.refreshFlight) return this.refreshFlight;
    const generation = this.generation;
    this.refreshFlight = this.api.refresh().pipe(
      map((status) => status.owner),
      tap((owner) => this.accept(owner, generation)),
      catchError((error: unknown) => {
        if (generation === this.generation) this.reject(error);
        return throwError(() => error);
      }),
      finalize(() => {
        this.refreshFlight = undefined;
      }),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    return this.refreshFlight;
  }
  logout(): Observable<void> {
    ++this.generation;
    return this.api.logout().pipe(tap(() => this.clear()));
  }
  clear(): void {
    ++this.generation;
    this.currentOwner.set(null);
    this.currentState.set('anonymous');
  }
  private accept(owner: Owner, generation: number): void {
    if (generation !== this.generation) return;
    this.currentOwner.set(owner);
    this.currentState.set('authenticated');
  }
  private reject(error: unknown): void {
    this.currentOwner.set(null);
    this.currentState.set(
      error instanceof HttpErrorResponse && error.status === 401 ? 'anonymous' : 'unavailable',
    );
  }
}
