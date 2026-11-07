import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { I18n, TranslationKey } from '../../core/i18n';
import { Icon, IconName } from '../../shared/icon';
import { SearchApi, Execution, executionStatusKey } from '../../core/search-api';
@Component({
  selector: 'jh-dashboard',
  imports: [RouterLink, Icon, DatePipe],
  templateUrl: './dashboard.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Dashboard {
  private readonly api = inject(SearchApi);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly data = signal<{
    imported_count: number;
    last_execution: Execution | null;
  } | null>(null);
  protected readonly error = signal(false);
  protected readonly statusKey = executionStatusKey;
  constructor() {
    this.load();
  }
  protected load(): void {
    this.error.set(false);
    this.api
      .dashboard()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (data) => this.data.set(data), error: () => this.error.set(true) });
  }
  protected readonly i18n = inject(I18n);
  protected readonly steps: {
    title: TranslationKey;
    body: TranslationKey;
    icon: IconName;
    ready: boolean;
  }[] = [
    { title: 'stepAccount', body: 'stepAccountBody', icon: 'user', ready: true },
    { title: 'stepCv', body: 'stepCvBody', icon: 'file', ready: false },
    { title: 'stepSearch', body: 'stepSearchBody', icon: 'search', ready: true },
    { title: 'stepMatches', body: 'stepMatchesBody', icon: 'briefcase', ready: false },
  ];
}
