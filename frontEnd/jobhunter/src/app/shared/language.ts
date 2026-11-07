import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { I18n } from '../core/i18n';
@Component({
  selector: 'jh-language',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="language-switch" role="group" [attr.aria-label]="i18n.t('language')">
    <button
      type="button"
      lang="fr"
      (click)="i18n.setLocale('fr')"
      [attr.aria-pressed]="i18n.locale() === 'fr'"
    >
      FR</button
    ><button
      type="button"
      lang="en"
      (click)="i18n.setLocale('en')"
      [attr.aria-pressed]="i18n.locale() === 'en'"
    >
      EN
    </button>
  </div>`,
})
export class Language {
  protected readonly i18n = inject(I18n);
}
