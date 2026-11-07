import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription, finalize, forkJoin } from 'rxjs';
import { I18n, TranslationKey } from '../../core/i18n';
import {
  Execution,
  SearchApi,
  SearchProfile,
  activeExecution,
  executionStatusKey,
} from '../../core/search-api';
@Component({
  selector: 'jh-search',
  imports: [DatePipe, ReactiveFormsModule, RouterLink],
  templateUrl: './search.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Search {
  protected readonly i18n = inject(I18n);
  private readonly api = inject(SearchApi);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly profiles = signal<SearchProfile[]>([]);
  protected readonly history = signal<Execution[]>([]);
  protected readonly current = signal<Execution | null>(null);
  protected readonly loading = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal<TranslationKey | null>(null);
  protected readonly reconnecting = signal(false);
  protected readonly selection = new FormControl('', { nonNullable: true });
  protected readonly isActive = activeExecution;
  protected readonly statusKey = executionStatusKey;
  private events: EventSource | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private fallback: Subscription | null = null;
  private loadRequest: Subscription | null = null;
  private observedId: string | null = null;
  constructor() {
    this.load();
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const id = params.get('execution');
      if (id) {
        this.observe(id);
      } else {
        this.stop();
        this.current.set(null);
      }
    });
    this.destroyRef.onDestroy(() => {
      this.stop();
      this.loadRequest?.unsubscribe();
    });
  }
  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({ profiles: this.api.profiles(), history: this.api.history() })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: ({ profiles, history }) => {
          this.profiles.set(profiles);
          this.history.set(history);
          if (!this.selection.value) this.selection.setValue(profiles[0]?.id ?? '');
        },
        error: () => this.error.set('searchLoadError'),
      });
  }
  protected chosen(): SearchProfile | undefined {
    return this.profiles().find((profile) => profile.id === this.selection.value);
  }
  private stop(): void {
    this.events?.close();
    this.events = null;
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    this.fallback?.unsubscribe();
    this.fallback = null;
    this.observedId = null;
  }
  private receive(execution: Execution): void {
    this.current.set(execution);
    this.history.update((rows) =>
      [execution, ...rows.filter((row) => row.id !== execution.id)]
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
        .slice(0, 50),
    );
    if (!activeExecution(execution)) this.stop();
  }
  private observe(id: string): void {
    this.stop();
    this.loadRequest?.unsubscribe();
    this.observedId = id;
    this.error.set(null);
    this.loadRequest = this.api
      .execution(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (execution) => {
          this.receive(execution);
          if (!activeExecution(execution)) return;
          this.events = new EventSource(`/api/search/executions/${encodeURIComponent(id)}/events`);
          this.events.onopen = () => this.reconnecting.set(false);
          this.events.addEventListener('progress', (event: MessageEvent<string>) => {
            if (this.observedId !== id) return;
            try {
              this.receive(JSON.parse(event.data) as Execution);
            } catch {
              this.reconnecting.set(true);
            }
          });
          this.events.onerror = () => this.reconnecting.set(true);
          this.timer = setInterval(() => {
            if (this.reconnecting() && !this.fallback) {
              this.fallback = this.api
                .execution(id)
                .pipe(
                  takeUntilDestroyed(this.destroyRef),
                  finalize(() => (this.fallback = null)),
                )
                .subscribe({
                  next: (view) => this.receive(view),
                  error: () => this.error.set('searchError'),
                });
            }
          }, 2000);
        },
        error: () => this.error.set('searchError'),
      });
  }
  protected start(): void {
    if (!this.selection.value || this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    this.api
      .start(this.selection.value)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (execution) => {
          this.current.set(execution);
          void this.router.navigate(['/search'], { queryParams: { execution: execution.id } });
        },
        error: (error: unknown) => {
          const code = error instanceof HttpErrorResponse ? error.error?.error?.code : '';
          this.error.set(
            (
              {
                SEARCH_ALREADY_ACTIVE: 'activeSearchError',
                SOURCES_REQUIRED: 'sourceRequiredError',
                FEATURE_UNAVAILABLE: 'featureUnavailableError',
              } as Record<string, TranslationKey>
            )[code] ?? 'searchError',
          );
          this.loadHistory();
        },
      });
  }
  private loadHistory(): void {
    this.api
      .history()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (rows) => this.history.set(rows), error: () => {} });
  }
  protected cancel(): void {
    const execution = this.current();
    if (!execution || this.busy()) return;
    this.busy.set(true);
    this.api
      .cancel(execution.id)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (view) => this.receive(view),
        error: () => this.error.set('searchError'),
      });
  }
}
