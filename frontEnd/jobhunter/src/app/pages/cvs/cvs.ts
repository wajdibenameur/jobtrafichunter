import { DOCUMENT, DatePipe } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  FormControl,
  FormGroup,
  FormRecord,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Observable, finalize, forkJoin } from 'rxjs';
import { Candidate, CandidateFields, CvApi, CvInspection, CvVersion } from '../../core/cv-api';
import { cvEn, cvFr } from '../../core/cv-translations';
import { I18n } from '../../core/i18n';

type Key = keyof typeof cvFr;
const categories = [
  'languages',
  'frameworks',
  'backend',
  'frontend',
  'databases',
  'devops',
  'cloud',
  'ai_ml',
  'data_engineering',
  'business_analysis',
  'other',
];
@Component({
  selector: 'jh-cvs',
  imports: [ReactiveFormsModule, DatePipe],
  templateUrl: './cvs.html',
  styleUrl: './cvs.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Cvs {
  protected readonly i18n = inject(I18n);
  private readonly api = inject(CvApi);
  private readonly destroy = inject(DestroyRef);
  private readonly document = inject(DOCUMENT);
  protected readonly versions = signal<CvVersion[]>([]);
  protected readonly documents = computed(() =>
    this.versions().filter(
      (v, i, all) =>
        v.state === 'READY' && all.findIndex((x) => x.document_id === v.document_id) === i,
    ),
  );
  protected readonly selected = signal<CvVersion | null>(null);
  protected readonly inspection = signal<CvInspection | null>(null);
  protected readonly profiles = signal<Candidate[]>([]);
  protected readonly profile = signal<Candidate | null>(null);
  protected readonly ready = signal(false);
  protected readonly loading = signal(false);
  protected readonly detailsLoading = signal(false);
  private readonly acting = signal(false);
  protected readonly busy = computed(
    () => this.loading() || this.detailsLoading() || this.acting(),
  );
  protected readonly error = signal<Key | null>(null);
  protected readonly uploading = signal(false);
  protected readonly progress = signal(0);
  protected readonly deleting = signal(false);
  protected readonly replacement = new FormControl('', { nonNullable: true });
  protected readonly reviewed = new FormControl(false, { nonNullable: true });
  protected readonly records = ['education', 'experiences', 'languages', 'certifications'] as const;
  protected readonly editor = new FormGroup({
    professional_title: new FormControl('', {
      nonNullable: true,
      validators: Validators.maxLength(200),
    }),
    summary: new FormControl('', { nonNullable: true, validators: Validators.maxLength(3000) }),
    years_experience: new FormControl<number | null>(null, [Validators.min(0), Validators.max(60)]),
    education: new FormControl('', { nonNullable: true }),
    experiences: new FormControl('', { nonNullable: true }),
    languages: new FormControl('', { nonNullable: true }),
    certifications: new FormControl('', { nonNullable: true }),
    locations: new FormControl('', { nonNullable: true }),
    domains: new FormControl('', { nonNullable: true }),
    target_levels: new FormControl('', { nonNullable: true }),
    visa_needed: new FormControl('', { nonNullable: true }),
  });
  protected readonly skillForm = new FormRecord<FormControl<string>>({});
  protected readonly skillCategories = signal<string[]>(categories);
  protected readonly proofs = computed(() =>
    Object.entries(this.profile()?.data.evidence ?? {}).map(([field, values]) => ({
      field,
      values,
    })),
  );
  protected readonly origins = computed(() =>
    Object.entries(this.profile()?.data.origins ?? {}).map(([field, origin]) => ({
      field,
      origin,
    })),
  );
  constructor() {
    this.load();
  }
  protected t(key: Key): string {
    return (this.i18n.locale() === 'fr' ? cvFr : cvEn)[key];
  }
  protected label(field: string): string {
    if (field === 'skills.languages') return this.t('programming');
    const key = field.replace(/^skills\./, '').replace(/^preferences\./, '');
    return key in cvFr ? this.t(key as Key) : key;
  }
  protected dirty(): boolean {
    return this.editor.dirty || this.skillForm.dirty;
  }
  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({ versions: this.api.versions(), capabilities: this.api.capabilities() })
      .pipe(
        takeUntilDestroyed(this.destroy),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: ({ versions, capabilities }) => {
          this.versions.set(versions);
          this.ready.set(capabilities.ready);
          const selected = versions.find((v) => v.id === this.selected()?.id);
          if (selected) this.selected.set(selected);
          else if (versions.some((v) => v.state === 'READY'))
            this.show(versions.find((v) => v.state === 'READY')!);
          else {
            this.selected.set(null);
            this.profile.set(null);
            this.inspection.set(null);
          }
          if (!versions.some((v) => v.document_id === this.replacement.value))
            this.replacement.setValue('');
        },
        error: () => this.error.set('error'),
      });
  }
  protected select(version: CvVersion): void {
    if (this.busy() || (this.dirty() && !this.document.defaultView?.confirm(this.t('discard'))))
      return;
    this.show(version);
  }
  private show(version: CvVersion): void {
    this.editor.reset();
    this.skillForm.markAsPristine();
    this.reviewed.setValue(false);
    this.selected.set(version);
    this.profile.set(null);
    this.inspection.set(null);
    this.profiles.set([]);
    this.deleting.set(false);
    if (version.state !== 'READY') {
      this.detailsLoading.set(false);
      return;
    }
    this.detailsLoading.set(true);
    forkJoin({
      inspection: this.api.inspection(version.id),
      profiles: this.api.profiles(version.id),
    })
      .pipe(
        takeUntilDestroyed(this.destroy),
        finalize(() => this.detailsLoading.set(false)),
      )
      .subscribe({
        next: (value) => {
          if (this.selected()?.id !== version.id) return;
          this.inspection.set(value.inspection.inspection);
          this.profiles.set(value.profiles);
          if (value.profiles[0]) this.hydrate(value.profiles[0]);
        },
        error: () => this.error.set('error'),
      });
  }
  protected chooseProfile(candidate: Candidate): void {
    if (this.dirty() && !this.document.defaultView?.confirm(this.t('discard'))) return;
    this.hydrate(candidate);
  }
  private hydrate(candidate: Candidate): void {
    this.profile.set(candidate);
    this.reviewed.setValue(false);
    const fields = candidate.data.fields,
      preferences = candidate.data.preferences;
    this.editor.setValue({
      professional_title: fields.professional_title ?? '',
      summary: fields.summary ?? '',
      years_experience: fields.years_experience,
      education: fields.education.join('\n'),
      experiences: fields.experiences.join('\n'),
      languages: fields.languages.join('\n'),
      certifications: fields.certifications.join('\n'),
      locations: preferences.locations.join(', '),
      domains: preferences.domains.join(', '),
      target_levels: preferences.target_levels.join(', '),
      visa_needed: preferences.visa_needed === null ? '' : String(preferences.visa_needed),
    });
    for (const name of Object.keys(this.skillForm.controls)) this.skillForm.removeControl(name);
    const keys = [...new Set([...categories, ...Object.keys(fields.skills)])];
    this.skillCategories.set(keys);
    for (const key of keys)
      this.skillForm.addControl(
        key,
        new FormControl((fields.skills[key] ?? []).join(', '), { nonNullable: true }),
      );
    this.editor.markAsPristine();
    this.skillForm.markAsPristine();
  }
  private run<T>(request: Observable<T>, next: (value: T) => void): void {
    if (this.busy()) return;
    this.acting.set(true);
    this.error.set(null);
    request
      .pipe(
        takeUntilDestroyed(this.destroy),
        finalize(() => this.acting.set(false)),
      )
      .subscribe({ next, error: () => this.error.set('error') });
  }
  protected upload(event: Event): void {
    const input = event.target as HTMLInputElement,
      file = input.files?.[0];
    input.value = '';
    if (!file || this.busy()) return;
    if (this.dirty() && !this.document.defaultView?.confirm(this.t('discard'))) return;
    if (!file.size || file.size > 5 * 1024 * 1024 || !/\.(pdf|docx)$/i.test(file.name)) {
      this.error.set('fileError');
      return;
    }
    this.uploading.set(true);
    this.progress.set(0);
    this.acting.set(true);
    this.error.set(null);
    this.api
      .upload(file, this.replacement.value || undefined)
      .pipe(
        takeUntilDestroyed(this.destroy),
        finalize(() => {
          this.uploading.set(false);
          this.acting.set(false);
        }),
      )
      .subscribe({
        next: (event) => {
          if (event.type === HttpEventType.UploadProgress && event.total)
            this.progress.set(Math.round((event.loaded / event.total) * 100));
          if (event.type === HttpEventType.Response && event.body) {
            this.show(event.body);
            this.load();
          }
        },
        error: () => this.error.set('error'),
      });
  }
  protected generate(regenerate = false): void {
    const v = this.selected();
    if (v) this.run(this.api.generate(v.id, regenerate), (p) => this.saved(p));
  }
  private saved(candidate: Candidate): void {
    this.profiles.update((all) =>
      [candidate, ...all.filter((p) => p.id !== candidate.id)].sort(
        (a, b) => b.revision - a.revision,
      ),
    );
    this.hydrate(candidate);
  }
  protected save(): void {
    const profile = this.profile();
    if (!profile || this.editor.invalid) return;
    const value = this.editor.getRawValue();
    const split = (text: string, separator: string) =>
      text
        .split(separator)
        .map((s) => s.trim())
        .filter(Boolean);
    const skills = Object.fromEntries(
      Object.entries(this.skillForm.getRawValue())
        .map(([key, text]) => [key, split(text, ',')])
        .filter(([, values]) => (values as string[]).length),
    );
    const fields: CandidateFields = {
      professional_title: value.professional_title.trim() || null,
      summary: value.summary.trim() || null,
      years_experience: value.years_experience,
      education: split(value.education, '\n'),
      experiences: split(value.experiences, '\n'),
      languages: split(value.languages, '\n'),
      certifications: split(value.certifications, '\n'),
      skills,
    };
    this.run(
      this.api.edit(profile.id, fields, {
        locations: split(value.locations, ','),
        domains: split(value.domains, ','),
        target_levels: split(value.target_levels, ','),
        visa_needed: value.visa_needed === '' ? null : value.visa_needed === 'true',
      }),
      (p) => this.saved(p),
    );
  }
  protected validate(): void {
    const p = this.profile();
    if (p && this.reviewed.value && !this.dirty())
      this.run(this.api.validate(p.id), (value) => this.saved(value));
  }
  protected activate(): void {
    const p = this.profile();
    if (p?.status === 'VALIDATED' && !this.dirty())
      this.run(this.api.activate(p.id), (value) => {
        this.profiles.update((all) => all.map((x) => ({ ...x, active: x.id === value.id })));
        this.saved(value);
        this.load();
      });
  }
  protected remove(): void {
    const v = this.selected();
    if (v && this.deleting())
      this.run(this.api.remove(v.document_id), () => {
        this.selected.set(null);
        this.profile.set(null);
        this.deleting.set(false);
        this.editor.markAsPristine();
        this.skillForm.markAsPristine();
        this.load();
      });
  }
  protected download(exportData = false): void {
    const v = this.selected();
    if (!v) return;
    this.run(exportData ? this.api.export(v.id) : this.api.download(v.id), (blob) => {
      const url = URL.createObjectURL(blob),
        link = this.document.createElement('a');
      link.href = url;
      link.download = exportData ? `cv-export-${v.id}.json` : v.filename;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }
}
