import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { Api, Owner } from '../../core/api';
import { I18n } from '../../core/i18n';
import { Icon } from '../../shared/icon';
@Component({
  selector: 'jh-account',
  imports: [Icon],
  templateUrl: './account.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Account {
  protected readonly i18n = inject(I18n);
  private readonly api = inject(Api);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly owner = signal<Owner | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal(false);
  constructor() {
    this.load();
  }
  protected load(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set(false);
    this.api
      .account()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (owner) => this.owner.set(owner),
        error: (error: unknown) => {
          this.error.set(true);
          if (error instanceof HttpErrorResponse && error.status === 401) {
            void this.router.navigate(['/auth/signin'], { queryParams: { reason: 'expired' } });
          }
        },
      });
  }
}
