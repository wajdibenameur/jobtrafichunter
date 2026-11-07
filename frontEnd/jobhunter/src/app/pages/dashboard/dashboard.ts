import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { I18n, TranslationKey } from '../../core/i18n';
import { Icon, IconName } from '../../shared/icon';
@Component({
  selector: 'jh-dashboard',
  imports: [RouterLink, Icon],
  templateUrl: './dashboard.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Dashboard {
  protected readonly i18n = inject(I18n);
  protected readonly steps: {
    title: TranslationKey;
    body: TranslationKey;
    icon: IconName;
    ready: boolean;
  }[] = [
    { title: 'stepAccount', body: 'stepAccountBody', icon: 'user', ready: true },
    { title: 'stepCv', body: 'stepCvBody', icon: 'file', ready: false },
    { title: 'stepSearch', body: 'stepSearchBody', icon: 'search', ready: false },
    { title: 'stepMatches', body: 'stepMatchesBody', icon: 'briefcase', ready: false },
  ];
}
