import { DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription, finalize } from 'rxjs';
import { I18n, TranslationKey } from '../../core/i18n';
import {
  Execution,
  SearchApi,
  SearchResult,
  executionStatusKey,
  visaStatusKey,
} from '../../core/search-api';
@Component({
  selector: 'jh-results',
  imports: [DatePipe, ReactiveFormsModule, RouterLink],
  templateUrl: './results.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Results {
  protected readonly visaKey = visaStatusKey;
  protected currentExecution(): Execution | undefined {
    return this.executions().find((execution) => execution.id === this.currentId());
  }
  protected readonly i18n = inject(I18n);
  private readonly api = inject(SearchApi);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly dialog = viewChild<ElementRef<HTMLDialogElement>>('details');
  protected readonly executions = signal<Execution[]>([]);
  protected readonly items = signal<SearchResult[]>([]);
  protected readonly total = signal(0);
  protected readonly offset = signal(0);
  protected readonly currentId = signal('');
  protected readonly loading = signal(false);
  protected readonly error = signal(false);
  protected readonly selected = signal<SearchResult | null>(null);
  protected readonly q = new FormControl('', { nonNullable: true });
  protected readonly sort = new FormControl('discovery', { nonNullable: true });
  protected readonly selection = new FormControl('', { nonNullable: true });
  protected readonly statusKey = executionStatusKey;
  private request: Subscription | null = null;
  constructor() {
    this.api
      .history()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (rows) => {
          this.executions.set(rows);
          if (!this.currentId() && rows.length)
            void this.router.navigate(['/results'], {
              queryParams: { execution: rows[0].id },
              replaceUrl: true,
            });
        },
        error: () => this.error.set(true),
      });
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const id = params.get('execution') ?? '';
      this.currentId.set(id);
      this.selection.setValue(id, { emitEvent: false });
      this.items.set([]);
      this.total.set(0);
      if (id) this.load(0);
    });
    this.destroyRef.onDestroy(() => this.request?.unsubscribe());
  }
  protected choose(): void {
    void this.router.navigate(['/results'], { queryParams: { execution: this.selection.value } });
  }
  protected load(offset = 0): void {
    if (!this.currentId()) return;
    this.request?.unsubscribe();
    this.loading.set(true);
    this.error.set(false);
    this.request = this.api
      .results(this.currentId(), offset, this.sort.value, this.q.value)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (page) => {
          this.offset.set(offset);
          this.items.set(page.items);
          this.total.set(page.total);
        },
        error: () => this.error.set(true),
      });
  }
  protected show(item: SearchResult): void {
    this.selected.set(item);
    this.dialog()?.nativeElement.showModal();
  }
  protected close(): void {
    this.dialog()?.nativeElement.close();
    this.selected.set(null);
  }
  protected fieldKey(field: string): TranslationKey {
    return (
      (
        {
          country: 'countriesLabel',
          city: 'citiesLabel',
          work_mode: 'workModes',
          domain: 'domainsLabel',
          experience_level: 'experienceLevels',
          experience_years: 'yearsMaximum',
          title: 'jobTitle',
          include_keywords: 'includeKeywords',
          description_exclusions: 'excludeKeywords',
          published_at: 'publishedAt',
          novelty: 'noveltyWindow',
        } as Record<string, TranslationKey>
      )[field] ?? 'unknownValue'
    );
  }
}
