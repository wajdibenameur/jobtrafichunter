import { DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize, forkJoin, Subscription } from 'rxjs';
import { I18n, TranslationKey } from '../../core/i18n';
import { Execution, SearchApi, SearchProfile, executionStatusKey } from '../../core/search-api';
import { JobSource, SourceApi } from '../../core/source-api';
import { CriteriaEditor } from '../../shared/criteria-editor';

@Component({
  selector: 'jh-scraping',
  imports: [DatePipe, RouterLink, CriteriaEditor, ReactiveFormsModule],
  templateUrl: './scraping.html',
  styleUrl: './scraping.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Scraping {
  protected readonly i18n = inject(I18n);
  private readonly api = inject(SearchApi);
  private readonly sourceApi = inject(SourceApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly editor = viewChild(CriteriaEditor);
  protected readonly profiles = signal<SearchProfile[]>([]);
  protected readonly sources = signal<JobSource[]>([]);
  protected readonly executions = signal<Execution[]>([]);
  protected readonly selectedId = signal('');
  protected readonly selection = new FormControl(
    { value: '', disabled: true },
    { nonNullable: true },
  );
  protected readonly profile = computed(() =>
    this.profiles().find((p) => p.id === this.selectedId()),
  );
  protected readonly history = computed(() =>
    this.executions().filter(
      (e) => e.profile_id === this.selectedId() && e.scope === 'IMPORTED_OFFERS',
    ),
  );
  protected readonly loading = signal(false);
  protected readonly busy = signal(false);
  protected readonly saved = signal(false);
  protected readonly error = signal<TranslationKey | null>(null);
  protected readonly statusKey = executionStatusKey;
  private request: Subscription | null = null;

  constructor() {
    this.load();
  }

  protected load(): void {
    if (this.busy()) return;
    if (this.editor()?.dirty && !window.confirm(this.i18n.t('discardCriteria'))) return;
    this.request?.unsubscribe();
    this.loading.set(true);
    this.selection.disable({ emitEvent: false });
    this.error.set(null);
    this.saved.set(false);
    this.request = forkJoin({
      profiles: this.api.profiles(),
      sources: this.sourceApi.sources(),
      history: this.api.history(),
    })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => {
          this.loading.set(false);
          if (this.profiles().length) this.selection.enable({ emitEvent: false });
        }),
      )
      .subscribe({
        next: ({ profiles, sources, history }) => {
          this.profiles.set(profiles);
          this.sources.set(sources);
          this.executions.set(history);
          const desired = this.selectedId() || this.route.snapshot.queryParamMap.get('profile');
          this.selectedId.set(
            profiles.some((p) => p.id === desired) ? desired! : (profiles[0]?.id ?? ''),
          );
          this.selection.setValue(this.selectedId(), { emitEvent: false });
        },
        error: () => this.error.set('searchLoadError'),
      });
  }

  protected choose(value: string): void {
    if (
      this.busy() ||
      this.loading() ||
      (this.editor()?.dirty && !window.confirm(this.i18n.t('discardCriteria')))
    ) {
      this.selection.setValue(this.selectedId(), { emitEvent: false });
      return;
    }
    this.selectedId.set(value);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { profile: value },
      replaceUrl: true,
    });
    this.saved.set(false);
    this.error.set(null);
  }

  protected save(): void {
    const profile = this.profile();
    if (!profile || this.busy() || this.loading()) return;
    const criteria = this.editor()?.getValue();
    if (!criteria) {
      this.error.set('requiredFieldsError');
      return;
    }
    this.busy.set(true);
    this.selection.disable({ emitEvent: false });
    this.saved.set(false);
    this.error.set(null);
    this.api
      .update(profile.id, { name: profile.name, description: profile.description, criteria })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => {
          this.busy.set(false);
          if (this.profiles().length) this.selection.enable({ emitEvent: false });
        }),
      )
      .subscribe({
        next: (saved) => {
          this.profiles.update((rows) => rows.map((p) => (p.id === saved.id ? saved : p)));
          this.saved.set(true);
        },
        error: () => this.error.set('profileError'),
      });
  }
}
