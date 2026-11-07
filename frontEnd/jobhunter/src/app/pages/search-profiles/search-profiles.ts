import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable, finalize, forkJoin } from 'rxjs';
import { I18n, TranslationKey } from '../../core/i18n';
import { SearchApi, SearchProfile, defaultCriteria } from '../../core/search-api';
import { JobSource, SourceApi } from '../../core/source-api';
import { CriteriaEditor } from '../../shared/criteria-editor';
@Component({
  selector: 'jh-search-profiles',
  imports: [ReactiveFormsModule, CriteriaEditor, RouterLink],
  templateUrl: './search-profiles.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchProfiles {
  protected readonly i18n = inject(I18n);
  private readonly api = inject(SearchApi);
  private readonly sourceApi = inject(SourceApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly editor = viewChild(CriteriaEditor);
  protected readonly rows = signal<SearchProfile[]>([]);
  protected readonly sources = signal<JobSource[]>([]);
  protected readonly editing = signal<string | null>(null);
  protected readonly criteria = signal(defaultCriteria());
  protected readonly busy = signal(false);
  protected readonly loading = signal(false);
  protected readonly error = signal<TranslationKey | null>(null);
  protected readonly saved = signal(false);
  protected readonly form = new FormGroup({
    name: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.pattern(/\S/), Validators.maxLength(100)],
    }),
    description: new FormControl('', { nonNullable: true, validators: Validators.maxLength(500) }),
  });
  constructor() {
    this.load();
  }
  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({ profiles: this.api.profiles(), sources: this.sourceApi.sources() })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: ({ profiles, sources }) => {
          this.rows.set(profiles);
          this.sources.set(sources);
        },
        error: () => this.error.set('searchLoadError'),
      });
  }
  protected fresh(): void {
    this.editing.set(null);
    this.criteria.set(defaultCriteria());
    this.form.reset();
    this.saved.set(false);
    this.error.set(null);
  }
  protected edit(profile: SearchProfile): void {
    this.editing.set(profile.id);
    this.criteria.set(profile.criteria);
    this.form.reset({ name: profile.name, description: profile.description });
    this.saved.set(false);
    this.error.set(null);
  }
  private run<T>(request: Observable<T>, next: (value: T) => void): void {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    this.saved.set(false);
    request
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({ next, error: () => this.error.set('profileError') });
  }
  protected save(): void {
    this.form.markAllAsTouched();
    const criteria = this.editor()?.getValue();
    if (this.form.invalid || !criteria) {
      this.error.set('requiredFieldsError');
      return;
    }
    const id = this.editing();
    const body = { ...this.form.getRawValue(), criteria };
    this.run(id ? this.api.update(id, body) : this.api.create(body), (profile) => {
      this.rows.update((rows) =>
        id ? rows.map((row) => (row.id === id ? profile : row)) : [...rows, profile],
      );
      this.edit(profile);
      this.saved.set(true);
    });
  }
  protected duplicate(profile: SearchProfile): void {
    this.run(
      this.api.duplicate(profile, profile.name.slice(0, 85) + this.i18n.t('copySuffix')),
      (copy) => {
        this.rows.update((rows) => [...rows, copy]);
        this.edit(copy);
      },
    );
  }
  protected remove(profile: SearchProfile): void {
    this.run(this.api.remove(profile.id), () => {
      this.rows.update((rows) => rows.filter((row) => row.id !== profile.id));
      if (this.editing() === profile.id) this.fresh();
    });
  }
  protected examples(): void {
    this.run(this.api.examples(), (profiles) => this.rows.set(profiles));
  }
}
