import { ChangeDetectionStrategy, Component, input } from '@angular/core';
export type IconName =
  | 'grid'
  | 'search'
  | 'file'
  | 'briefcase'
  | 'clock'
  | 'bell'
  | 'globe'
  | 'user'
  | 'logout'
  | 'menu'
  | 'close'
  | 'arrow'
  | 'check'
  | 'shield'
  | 'eye'
  | 'eyeOff'
  | 'layers';
const paths: Record<IconName, string> = {
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  search: 'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M8 13h8 M8 17h5',
  briefcase: 'M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2 M3 7h18v14H3z M3 11l9 5 9-5 M12 13v4',
  clock: 'M12 8v5l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4',
  globe: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M3 12h18 M12 3c-5 5-5 13 0 18 M12 3c5 5 5 13 0 18',
  user: 'M20 21v-2a6 6 0 0 0-6-6h-4a6 6 0 0 0-6 6v2 M16 6a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  logout: 'M9 21H3V3h6 M9 12h12 M17 8l4 4-4 4',
  menu: 'M3 6h18 M3 12h18 M3 18h18',
  close: 'M6 6l12 12 M18 6L6 18',
  arrow: 'M4 12h16 M14 6l6 6-6 6',
  check: 'M5 12l4 4L19 6',
  shield: 'M12 3l9 4v5c0 6-9 10-9 10S3 18 3 12V7z M8 12l3 3 5-6',
  eye: 'M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12 M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  eyeOff: 'M3 3l18 18 M10 5h2c7 0 10 7 10 7a18 18 0 0 1-4 5 M6 6a18 18 0 0 0-4 6s3 7 10 7h2',
  layers: 'M12 3L2 8l10 5 10-5z M2 12l10 5 10-5 M2 16l10 5 10-5',
};
@Component({
  selector: 'jh-icon',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path [attr.d]="paths[name()]" />
  </svg>`,
  styles: `
    :host {
      display: inline-flex;
      width: 20px;
      height: 20px;
      flex-shrink: 0;
    }
    svg {
      width: 100%;
      height: 100%;
    }
  `,
})
export class Icon {
  readonly name = input.required<IconName>();
  protected readonly paths = paths;
}
