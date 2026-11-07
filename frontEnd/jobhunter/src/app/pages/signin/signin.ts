import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize } from 'rxjs';
import { safeReturnUrl } from '../../core/guards';
import { I18n, TranslationKey } from '../../core/i18n';
import { Session } from '../../core/session';
import { Icon } from '../../shared/icon';
import { Language } from '../../shared/language';

@Component({
  selector: 'jh-signin',
  imports: [ReactiveFormsModule, Icon, Language],
  templateUrl: './signin.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SignIn {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(Session);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);
  protected readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email, Validators.maxLength(254)]],
    password: ['', [Validators.required, Validators.maxLength(128)]],
  });
  protected readonly busy = signal(false);
  protected readonly showPassword = signal(false);
  protected readonly illustration = signal(true);
  protected readonly error = signal<TranslationKey | null>(null);
  protected readonly expired = this.route.snapshot.queryParamMap.get('reason') === 'expired';
  private readonly untilDestroyed = takeUntilDestroyed();

  protected submit(): void {
    if (this.busy()) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    this.busy.set(true);
    this.error.set(null);
    this.session
      .login(this.form.getRawValue())
      .pipe(
        this.untilDestroyed,
        finalize(() => {
          this.busy.set(false);
          this.form.controls.password.reset();
        }),
      )
      .subscribe({
        next: () =>
          void this.router.navigateByUrl(
            safeReturnUrl(this.route.snapshot.queryParamMap.get('returnUrl')),
          ),
        error: (error: unknown) => {
          this.error.set(
            error instanceof HttpErrorResponse
              ? error.status === 401
                ? 'invalidCredentials'
                : error.status === 429
                  ? 'locked'
                  : error.status === 0 || error.status >= 500
                    ? 'unavailable'
                    : 'unexpectedError'
              : 'unexpectedError',
          );
        },
      });
  }
}
