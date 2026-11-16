import { ChangeDetectionStrategy, Component, inject, input } from '@angular/core';
import { I18n, TranslationKey } from '../core/i18n';
import { MatchPreview } from '../core/matching-api';
import { matchingWeights } from './matching-controls';

@Component({
  selector: 'jh-match-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h3>{{ i18n.t('matchingPreview') }} : {{ preview().score }}/100</h3>
    <p class="warning-note">{{ i18n.t('matchingNotice') }}</p>
    <p>{{ i18n.t('matchingSnapshot') }}</p>
    <p>{{ i18n.t('matchingCoverage') }} : {{ preview().coverage }}%</p>
    @for (part of preview().components; track part.name) {
      <p>
        <strong>{{ i18n.t(label(part.name)) }}</strong> : {{ part.points }}/{{ part.weight }}
        @if (part.state === 'UNKNOWN') {
          <span> — {{ i18n.t('matchingUnknown') }}</span>
        }
      </p>
      @if (part.matched.length) {
        <p>{{ i18n.t('matchingMatched') }} : {{ part.matched.join(', ') }}</p>
      }
      @if (part.unattested.length) {
        <p>{{ i18n.t('matchingMissing') }} : {{ part.unattested.join(', ') }}</p>
      }
    }
    @if (preview().cap_reasons.length) {
      <h4>{{ i18n.t('matchingLimits') }}</h4>
      <p>{{ i18n.t('matchingGap') }}</p>
    }
    <h4>{{ i18n.t('matchingEvidence') }}</h4>
    <ul>
      @for (proof of preview().analysis.evidence; track $index) {
        <li>{{ proof.value }} : {{ proof.quote || proof.value }}</li>
      }
    </ul>
  `,
})
export class MatchDetail {
  readonly preview = input.required<MatchPreview>();
  protected readonly i18n = inject(I18n);
  protected label(name: string): TranslationKey {
    return matchingWeights.find(([key]) => key === name)?.[1] ?? 'matchingUnknown';
  }
}
