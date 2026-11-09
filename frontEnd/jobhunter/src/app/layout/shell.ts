import { DOCUMENT } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  Injector,
  afterNextRender,
  effect,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { finalize } from 'rxjs';
import { I18n, TranslationKey } from '../core/i18n';
import { Session } from '../core/session';
import { Icon, IconName } from '../shared/icon';
import { Language } from '../shared/language';

@Component({
  selector: 'jh-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon, Language],
  templateUrl: './shell.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '(document:keydown.escape)': 'closeMenu()', '(window:resize)': 'onResize()' },
})
export class Shell {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(Session);
  private readonly router = inject(Router);
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);
  private readonly injector = inject(Injector);
  protected readonly mobileOpen = signal(false);
  protected readonly loggingOut = signal(false);
  private readonly signedOut = signal(false);
  protected readonly logoutError = signal(false);
  protected readonly mobile = signal(
    this.document.defaultView?.matchMedia('(max-width: 991px)').matches ?? false,
  );
  private readonly navigation = viewChild<ElementRef<HTMLElement>>('navigation');
  private readonly menuButton = viewChild<ElementRef<HTMLButtonElement>>('menuButton');
  protected readonly futureNav: { key: TranslationKey; icon: IconName }[] = [
    { key: 'applications', icon: 'check' },
    { key: 'history', icon: 'clock' },
  ];
  constructor() {
    effect(() => {
      this.document.body.style.overflow = this.mobileOpen() ? 'hidden' : '';
      if (this.session.state() === 'anonymous' && !this.loggingOut() && !this.signedOut()) {
        void this.router.navigate(['/auth/signin'], { queryParams: { reason: 'expired' } });
      }
    });
    this.destroyRef.onDestroy(() => {
      this.document.body.style.overflow = '';
    });
  }
  protected openMenu(): void {
    this.mobileOpen.set(true);
    afterNextRender(
      () => this.navigation()?.nativeElement.querySelector<HTMLElement>('a, button')?.focus(),
      { injector: this.injector },
    );
  }
  protected closeMenu(restoreFocus = true): void {
    if (!this.mobileOpen()) return;
    this.mobileOpen.set(false);
    if (restoreFocus)
      afterNextRender(() => this.menuButton()?.nativeElement.focus(), { injector: this.injector });
  }
  protected onResize(): void {
    this.mobile.set(this.document.defaultView?.matchMedia('(max-width: 991px)').matches ?? false);
    if (!this.mobile()) this.mobileOpen.set(false);
  }
  protected trapFocus(event: KeyboardEvent): void {
    if (event.key !== 'Tab' || !this.mobileOpen()) return;
    const elements = this.navigation()?.nativeElement.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled])',
    );
    if (!elements?.length) return;
    const first = elements[0];
    const last = elements[elements.length - 1];
    if (event.shiftKey && this.document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && this.document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }
  protected logout(): void {
    if (this.loggingOut()) return;
    this.loggingOut.set(true);
    this.logoutError.set(false);
    this.session
      .logout()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loggingOut.set(false)),
      )
      .subscribe({
        next: () => {
          this.signedOut.set(true);
          void this.router.navigate(['/auth/signin']);
        },
        error: () => this.logoutError.set(true),
      });
  }
}
