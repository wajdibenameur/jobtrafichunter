import { DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable, catchError, finalize, forkJoin, switchMap, tap, throwError } from 'rxjs';
import { I18n, TranslationKey } from '../../core/i18n';
import {
  CsvPreview,
  ImportResult,
  JobSource,
  Listing,
  ManualJob,
  SourceApi,
} from '../../core/source-api';

@Component({
  selector: 'jh-sources',
  imports: [ReactiveFormsModule, DatePipe],
  templateUrl: './sources.html',
  styleUrl: './sources.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Sources {
  protected readonly i18n = inject(I18n);
  private readonly api = inject(SourceApi);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly sources = signal<JobSource[]>([]);
  protected readonly loading = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal<TranslationKey | null>(null);
  protected readonly filter = signal('all');
  protected readonly visible = computed(() =>
    this.sources().filter((s) =>
      this.filter() === 'tn' ? s.region === 'TN' : this.filter() === 'selected' ? s.enabled : true,
    ),
  );
  protected readonly links = signal<Record<string, { url: string; criteria_applied: boolean }>>({});
  protected readonly drafts: Record<string, FormGroup> = {};
  protected readonly custom = new FormGroup({
    name: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.maxLength(100)],
    }),
    homepage: new FormControl('', {
      nonNullable: true,
      validators: [
        Validators.required,
        Validators.pattern(/^https:\/\//),
        Validators.maxLength(4096),
      ],
    }),
    region: new FormControl('TN', { nonNullable: true }),
  });
  protected readonly job = new FormGroup({
    source: new FormControl('', { nonNullable: true, validators: Validators.required }),
    original_url: new FormControl('', {
      nonNullable: true,
      validators: [
        Validators.required,
        Validators.pattern(/^https:\/\//),
        Validators.maxLength(4096),
      ],
    }),
    title: new FormControl('', { nonNullable: true, validators: Validators.maxLength(300) }),
    company: new FormControl('', { nonNullable: true, validators: Validators.maxLength(200) }),
    country: new FormControl('', { nonNullable: true, validators: Validators.maxLength(100) }),
    city: new FormControl('', { nonNullable: true, validators: Validators.maxLength(100) }),
    description: new FormControl('', {
      nonNullable: true,
      validators: Validators.maxLength(50000),
    }),
  });
  protected readonly preview = signal<CsvPreview | null>(null);
  private previewSource = '';
  protected readonly csvReady = signal(false);
  private csvText = '';
  private fileVersion = 0;
  protected readonly result = signal<ImportResult | null>(null);
  protected readonly jobs = signal<Listing[]>([]);
  protected readonly total = signal(0);
  protected readonly offset = signal(0);
  protected readonly jobsError = signal(false);
  protected readonly jobsLoading = signal(false);
  constructor() {
    this.load();
    this.loadJobs();
    this.job.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.preview.set(null);
      this.result.set(null);
    });
  }
  private run<T>(request: Observable<T>, next: (value: T) => void, error: TranslationKey): void {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    request
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({ next, error: () => this.error.set(error) });
  }
  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api
      .sources()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (sources) => {
          this.sources.set(sources);
          for (const source of sources) this.draft(source);
          if (!this.job.controls.source.value && sources.length)
            this.job.controls.source.setValue(sources[0].id);
        },
        error: () => this.error.set('sourceLoadError'),
      });
  }
  protected draft(source: JobSource): FormGroup {
    return (this.drafts[source.id] ??= new FormGroup({
      keywords: new FormControl(source.settings.keywords, [Validators.maxLength(200)]),
      location: new FormControl(source.settings.location, [Validators.maxLength(200)]),
    }));
  }
  private replace(source: JobSource): void {
    this.sources.update((items) => items.map((s) => (s.id === source.id ? source : s)));
  }
  protected toggle(source: JobSource, event: Event): void {
    (event.target as HTMLInputElement).checked = source.enabled;
    this.run(
      this.api.patch(source.id, { enabled: !source.enabled }),
      (s) => this.replace(s),
      'sourceSaveError',
    );
  }
  protected selectAll(enabled: boolean): void {
    const requests = this.sources()
      .filter((s) => s.enabled !== enabled)
      .map((s) => this.api.patch(s.id, { enabled }));
    if (!requests.length) return;
    this.run(
      forkJoin(requests).pipe(
        catchError((error) => {
          this.load();
          return throwError(() => error);
        }),
      ),
      (items) => items.forEach((s) => this.replace(s)),
      'sourceSaveError',
    );
  }
  protected criteriaChanged(id: string): void {
    this.links.update((links) => {
      const copy = { ...links };
      delete copy[id];
      return copy;
    });
  }
  protected save(source: JobSource): void {
    const form = this.draft(source);
    if (form.invalid) {
      form.markAllAsTouched();
      return;
    }
    const settings = {
      keywords: String(form.value.keywords ?? ''),
      location: String(form.value.location ?? ''),
    };
    this.run(
      this.api.patch(source.id, { settings }).pipe(
        tap((saved) => this.replace(saved)),
        switchMap(() => this.api.link(source.id, settings)),
      ),
      (link) => this.links.update((links) => ({ ...links, [source.id]: link })),
      'sourceSaveError',
    );
  }
  protected create(): void {
    if (this.custom.invalid) {
      this.custom.markAllAsTouched();
      return;
    }
    this.run(
      this.api.create(this.custom.getRawValue()),
      (source) => {
        this.sources.update((items) => [...items, source]);
        this.custom.reset({ region: 'TN' });
        this.filter.set('all');
      },
      'sourceSaveError',
    );
  }
  protected remove(source: JobSource): void {
    this.run(
      this.api.delete(source.id),
      () => {
        this.sources.update((items) => items.filter((s) => s.id !== source.id));
        this.preview.set(null);
        if (this.job.controls.source.value === source.id)
          this.job.controls.source.setValue(this.sources()[0]?.id ?? '');
      },
      'sourceSaveError',
    );
  }
  protected review(): void {
    this.result.set(null);
    this.error.set(null);
    if (this.job.invalid) {
      this.job.markAllAsTouched();
      return;
    }
    const { source, ...raw } = this.job.getRawValue();
    const job: ManualJob = { original_url: raw.original_url.trim() };
    for (const key of ['title', 'company', 'country', 'city', 'description'] as const) {
      if (raw[key].trim()) job[key] = raw[key].trim();
    }
    this.previewSource = source;
    this.preview.set({
      rows: [{ row_number: 1, job, errors: [] }],
      valid_count: 1,
      invalid_count: 0,
    });
  }
  protected async fileChanged(event: Event): Promise<void> {
    const version = ++this.fileVersion;
    const file = (event.target as HTMLInputElement).files?.[0];
    this.csvReady.set(false);
    this.csvText = '';
    this.preview.set(null);
    this.result.set(null);
    this.error.set(null);
    if (!file) return;
    if (file.size > 524288) {
      this.error.set('csvInvalid');
      return;
    }
    try {
      const text = await file.text();
      if (version !== this.fileVersion) return;
      this.csvText = text;
      this.csvReady.set(!!text);
    } catch {
      if (version === this.fileVersion) this.error.set('csvInvalid');
    }
  }
  protected reviewCsv(): void {
    const source = this.job.controls.source.value;
    if (!source || !this.csvReady()) return;
    this.preview.set(null);
    this.result.set(null);
    this.run(
      this.api.preview(source, this.csvText),
      (preview) => {
        this.previewSource = source;
        this.preview.set(preview);
      },
      'csvInvalid',
    );
  }
  protected extraFields(job: ManualJob): { label: TranslationKey; value: string }[] {
    const labels: Partial<Record<keyof ManualJob, TranslationKey>> = {
      application_url: 'applicationLink',
      source_job_id: 'sourceJobId',
      work_mode: 'workMode',
      domain: 'jobDomain',
      experience_level: 'experienceLevel',
      min_years: 'minYears',
      max_years: 'maxYears',
      mandatory_skills: 'mandatorySkills',
      optional_skills: 'optionalSkills',
      visa_status: 'visaStatus',
      visa_evidence: 'visaEvidence',
      published_at: 'publishedAt',
    };
    return (Object.keys(labels) as (keyof ManualJob)[]).flatMap((key) => {
      const value = job[key];
      const label = labels[key]!;
      return value == null || value === '' || (Array.isArray(value) && !value.length)
        ? []
        : [{ label, value: Array.isArray(value) ? value.join(', ') : String(value) }];
    });
  }
  protected confirm(): void {
    const preview = this.preview();
    if (!preview || preview.invalid_count || !preview.valid_count) return;
    const jobs = preview.rows.flatMap((row) => (row.job ? [row.job] : []));
    this.run(
      this.api.import(this.previewSource, jobs),
      (result) => {
        this.result.set(result);
        this.preview.set(null);
        this.offset.set(0);
        this.loadJobs();
      },
      'importError',
    );
  }
  protected loadJobs(offset = this.offset()): void {
    this.jobsLoading.set(true);
    this.jobsError.set(false);
    this.api
      .jobs(offset)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.jobsLoading.set(false)),
      )
      .subscribe({
        next: (page) => {
          this.offset.set(offset);
          this.jobs.set(page.items);
          this.total.set(page.total);
        },
        error: () => this.jobsError.set(true),
      });
  }
}
