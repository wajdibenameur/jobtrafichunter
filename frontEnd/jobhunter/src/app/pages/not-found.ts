import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { I18n } from '../core/i18n';
import { Language } from '../shared/language';
@Component({
  selector: 'jh-not-found',
  imports: [RouterLink, Language],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<main class="not-found">
    <jh-language />
    <p class="not-found-code">404</p>
    <h1>{{ i18n.t('notFoundTitle') }}</h1>
    <p>{{ i18n.t('notFoundBody') }}</p>
    <a routerLink="/dashboard" class="btn btn-primary">{{ i18n.t('backDashboard') }}</a>
  </main>`,
})
export class NotFound {
  protected readonly i18n = inject(I18n);
}
