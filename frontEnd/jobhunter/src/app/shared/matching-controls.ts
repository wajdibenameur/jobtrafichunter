import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { I18n, TranslationKey } from '../core/i18n';
import { MatchingApi, MatchingCapabilities, PolicyVersion } from '../core/matching-api';
import { Execution, activeExecution } from '../core/search-api';

export const matchingWeights = [
  ['mandatory', 'matchingMandatory', 35],
  ['optional', 'matchingOptional', 10],
  ['experience', 'matchingExperience', 20],
  ['title', 'matchingTitle', 10],
  ['languages', 'matchingLanguages', 10],
  ['location', 'matchingLocation', 5],
  ['education', 'matchingEducation', 5],
  ['visa', 'matchingVisa', 5],
] as const;

@Component({
  selector: 'jh-matching-controls',
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <hr />
    <h2>{{ i18n.t('matchingPreview') }}</h2>
    <p class="warning-note">{{ i18n.t('matchingNotice') }}</p>
    @if (!capabilities()?.ready) {
      <p>{{ i18n.t('matchingUnavailable') }}</p>
    }
    @if (capabilities()?.ready) {
      <p>{{ i18n.t('matchingRevision') }} : {{ capabilities()?.candidate_revision }}</p>
      <label
        >{{ i18n.t('matchingPolicy')
        }}<select [formControl]="policy">
          <option value="">{{ i18n.t('matchingDefault') }}</option>
          @for (item of policies(); track item.id) {
            <option [value]="item.id">{{ i18n.t('matchingPolicy') }} {{ item.version }}</option>
          }
        </select></label
      >
      <details>
        <summary>{{ i18n.t('matchingConfigure') }}</summary>
        <p>{{ i18n.t('matchingPolicyHelp') }}</p>
        <form [formGroup]="weights" (submit)="$event.preventDefault(); savePolicy()">
          <div class="search-form-grid">
            @for (item of fields; track item[0]) {
              <label
                >{{ i18n.t(item[1])
                }}<input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  [id]="'matching-weight-' + item[0]"
                  [formControlName]="item[0]"
              /></label>
            }
          </div>
          <label
            >{{ i18n.t('matchingCap')
            }}<input type="number" min="0" max="60" step="1" [formControl]="cap"
          /></label>
          <button class="btn" type="submit" [disabled]="busy()">
            {{ i18n.t('matchingSavePolicy') }}
          </button>
        </form>
      </details>
    }
    @if (error(); as error) {
      <p role="alert">{{ i18n.t(error) }}</p>
    }
    <div class="search-actions">
      <button class="btn" (click)="refresh()" [disabled]="busy()">
        {{ i18n.t('matchingRefresh') }}
      </button>
      <button
        class="btn"
        (click)="start(false)"
        [disabled]="busy() || !capabilities()?.ready || !profile()"
      >
        {{ i18n.t('matchingStart') }}
      </button>
      @if (canRescore()) {
        <button class="btn" (click)="start(true)" [disabled]="busy() || !capabilities()?.ready">
          {{ i18n.t('matchingRescore') }}
        </button>
      }
    </div>
  `,
})
export class MatchingControls {
  readonly profile = input.required<string>();
  readonly execution = input<Execution | null>(null);
  readonly started = output<Execution>();
  protected readonly i18n = inject(I18n);
  private readonly api = inject(MatchingApi);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly capabilities = signal<MatchingCapabilities | null>(null);
  protected readonly policies = signal<PolicyVersion[]>([]);
  protected readonly busy = signal(false);
  protected readonly error = signal<TranslationKey | null>(null);
  protected readonly fields = matchingWeights;
  protected readonly policy = new FormControl('', { nonNullable: true });
  protected readonly cap = new FormControl(60, { nonNullable: true });
  protected readonly weights = new FormGroup(
    Object.fromEntries(
      matchingWeights.map(([name, , value]) => [
        name,
        new FormControl<number>(value, { nonNullable: true }),
      ]),
    ),
  );
  constructor() {
    this.refresh();
  }
  protected canRescore(): boolean {
    const row = this.execution();
    return !!row && !activeExecution(row) && row.profile_id === this.profile();
  }
  protected refresh(): void {
    this.busy.set(true);
    this.error.set(null);
    forkJoin({ capabilities: this.api.capabilities(), policies: this.api.policies() })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: ({ capabilities, policies }) => {
          this.capabilities.set(capabilities);
          this.policies.set(policies);
        },
        error: () => {
          this.capabilities.set(null);
          this.error.set('matchingError');
        },
      });
  }
  protected savePolicy(): void {
    const weights = this.weights.getRawValue();
    if (
      Object.values(weights).some((v) => !Number.isInteger(v) || v < 0 || v > 100) ||
      Object.values(weights).reduce((a, b) => a + b, 0) !== 100 ||
      !Number.isInteger(this.cap.value) ||
      this.cap.value < 0 ||
      this.cap.value > 60
    ) {
      this.error.set('matchingPolicyError');
      return;
    }
    this.busy.set(true);
    this.error.set(null);
    this.api
      .savePolicy({ weights, mandatory_cap: this.cap.value })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (version) => {
          this.policies.update((items) => [
            version,
            ...items.filter((item) => item.id !== version.id),
          ]);
          this.policy.setValue(version.id);
        },
        error: () => this.error.set('matchingPolicyError'),
      });
  }
  protected start(rescore: boolean): void {
    const candidate = this.capabilities()?.candidate_id;
    if (this.busy() || !candidate || !this.profile() || (rescore && !this.canRescore())) return;
    this.busy.set(true);
    this.error.set(null);
    this.api
      .start(
        this.profile(),
        candidate,
        this.policy.value,
        rescore ? this.execution()?.id : undefined,
      )
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (execution) => this.started.emit(execution),
        error: () => {
          this.capabilities.set(null);
          this.error.set('matchingError');
        },
      });
  }
}
