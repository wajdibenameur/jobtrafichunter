import {
  ChangeDetectionStrategy,
  Component,
  Input,
  OnChanges,
  SimpleChanges,
  inject,
} from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { I18n, TranslationKey } from '../core/i18n';
import { SearchCriteria, defaultCriteria, visaStatusKey } from '../core/search-api';
import { JobSource } from '../core/source-api';

export const DOMAINS = [
  'Software Development',
  'DevOps & Cloud',
  'Data Engineering & Analytics',
  'AI',
  'Business & IT Consulting',
];
export const TITLES = [
  'Java',
  'Spring Boot',
  'Angular',
  'Full Stack',
  'Backend',
  'Frontend',
  'Python',
  'Software Engineer',
  'Junior DevOps',
  'DevOps',
  'Cloud',
  'AWS',
  'Azure',
  'CI/CD',
  'Platform Engineer',
  'SRE',
  'Docker',
  'Kubernetes',
  'Junior Data Engineer',
  'Data Engineer',
  'ETL',
  'Analytics Engineer',
  'Data Analyst',
  'BI/Power BI',
  'SQL',
  'Big Data',
  'Data Warehouse',
  'PySpark',
  'Databricks',
  'Junior AI',
  'Machine Learning',
  'Generative AI',
  'LLM',
  'RAG',
  'Python AI',
  'Junior Business Analyst',
  'IT Business Analyst',
  'Functional/Technical Consultant',
  'Application Support',
];
const COUNTRIES = [
  'Tunisia',
  'France',
  'Germany',
  'Portugal',
  'Belgium',
  'Netherlands',
  'Luxembourg',
  'Ireland',
  'Finland',
  'Sweden',
  'Poland',
  'Canada',
  'United Kingdom',
  'UAE',
  'Saudi Arabia',
  'Qatar',
];
@Component({
  selector: 'jh-criteria-editor',
  imports: [ReactiveFormsModule],
  templateUrl: './criteria-editor.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CriteriaEditor implements OnChanges {
  protected readonly visaKey = visaStatusKey;
  protected levelKey(level: string): TranslationKey {
    return (
      (
        {
          Internship: 'levelInternship',
          Graduate: 'levelGraduate',
          'Entry Level': 'levelEntry',
          Junior: 'levelJunior',
          Associate: 'levelAssociate',
          'Mid-Level': 'levelMid',
          Senior: 'levelSenior',
        } as Record<string, TranslationKey>
      )[level] ?? 'unknownValue'
    );
  }
  protected domainKey(domain: string): TranslationKey {
    return (
      (
        {
          'Software Development': 'domainSoftware',
          'DevOps & Cloud': 'domainDevops',
          'Data Engineering & Analytics': 'domainData',
          AI: 'domainAi',
          'Business & IT Consulting': 'domainBusiness',
        } as Record<string, TranslationKey>
      )[domain] ?? 'unknownValue'
    );
  }
  protected countryLabel(country: string): string {
    const code = (
      {
        Tunisia: 'TN',
        France: 'FR',
        Germany: 'DE',
        Portugal: 'PT',
        Belgium: 'BE',
        Netherlands: 'NL',
        Luxembourg: 'LU',
        Ireland: 'IE',
        Finland: 'FI',
        Sweden: 'SE',
        Poland: 'PL',
        Canada: 'CA',
        'United Kingdom': 'GB',
        UAE: 'AE',
        'Saudi Arabia': 'SA',
        Qatar: 'QA',
      } as Record<string, string>
    )[country];
    return code
      ? (new Intl.DisplayNames([this.i18n.locale()], { type: 'region' }).of(code) ?? country)
      : country;
  }
  @Input() criteria: SearchCriteria = defaultCriteria();
  @Input() sources: JobSource[] = [];
  @Input() busy = false;
  protected readonly i18n = inject(I18n);
  protected readonly domains = DOMAINS;
  protected readonly titles = TITLES;
  protected readonly levels = [
    'Internship',
    'Graduate',
    'Entry Level',
    'Junior',
    'Associate',
    'Mid-Level',
    'Senior',
  ];
  protected readonly visas = ['CONFIRMED', 'POSSIBLE', 'RELOCATION', 'NOT_SPECIFIED', 'NONE'];
  protected readonly form = new FormGroup({
    source_ids: new FormControl<string[]>([], { nonNullable: true }),
    domains: new FormControl<string[]>([], { nonNullable: true }),
    titles: new FormControl<string[]>([], { nonNullable: true }),
    countries: new FormControl<string[]>([], { nonNullable: true }),
    work_modes: new FormControl<SearchCriteria['work_modes']>([], { nonNullable: true }),
    experience_levels: new FormControl<string[]>([], { nonNullable: true }),
    visa_statuses: new FormControl<string[]>([], { nonNullable: true }),
    include: new FormControl('', { nonNullable: true, validators: Validators.maxLength(10000) }),
    exclude: new FormControl('', { nonNullable: true, validators: Validators.maxLength(10000) }),
    cities: new FormControl('', { nonNullable: true, validators: Validators.maxLength(10000) }),
    customDomains: new FormControl('', {
      nonNullable: true,
      validators: Validators.maxLength(10000),
    }),
    customTitles: new FormControl('', {
      nonNullable: true,
      validators: Validators.maxLength(10000),
    }),
    max_years: new FormControl(3, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(0), Validators.max(60)],
    }),
    publication_days: new FormControl<SearchCriteria['publication_days']>(0, { nonNullable: true }),
    novelty: new FormControl<SearchCriteria['novelty']>('all', { nonNullable: true }),
    unknown_policy: new FormControl<SearchCriteria['unknown_policy']>('include', {
      nonNullable: true,
    }),
  });
  protected countryOptions(): string[] {
    return [...new Set([...COUNTRIES, ...this.criteria.countries])];
  }
  ngOnChanges(changes: SimpleChanges): void {
    if (!changes['criteria']) return;
    const c = this.criteria;
    this.form.reset(
      {
        ...c,
        domains: c.domains.filter((d) => DOMAINS.includes(d)),
        titles: c.titles.filter((t) => TITLES.includes(t)),
        include: c.include_keywords.join(', '),
        exclude: c.exclude_keywords.join(', '),
        cities: c.cities.join(', '),
        customDomains: c.domains.filter((d) => !DOMAINS.includes(d)).join(', '),
        customTitles: c.titles.filter((t) => !TITLES.includes(t)).join(', '),
      },
      { emitEvent: false },
    );
  }
  protected toggleSource(id: string): void {
    const ids = this.form.controls.source_ids.value;
    this.form.controls.source_ids.setValue(
      ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id],
    );
  }
  getValue(): SearchCriteria | null {
    this.form.markAllAsTouched();
    if (this.form.invalid || !Number.isInteger(this.form.controls.max_years.value)) return null;
    const value = this.form.getRawValue();
    const split = (text: string): string[] => [
      ...new Set(
        text
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      ),
    ];
    const result: SearchCriteria = {
      ...this.criteria,
      source_ids: value.source_ids,
      domains: [...new Set([...value.domains, ...split(value.customDomains)])],
      titles: [...new Set([...value.titles, ...split(value.customTitles)])],
      countries: value.countries,
      cities: split(value.cities),
      work_modes: value.work_modes,
      experience_levels: value.experience_levels,
      visa_statuses: value.visa_statuses,
      include_keywords: split(value.include),
      exclude_keywords: split(value.exclude),
      max_years: value.max_years,
      publication_days: value.publication_days,
      novelty: value.novelty,
      unknown_policy: value.unknown_policy,
    };
    const lists = [
      result.domains,
      result.titles,
      result.countries,
      result.cities,
      result.experience_levels,
      result.include_keywords,
      result.exclude_keywords,
    ];
    return lists.some(
      (items) =>
        items.length > 100 || items.some((item) => item.length > 100 || item.includes('\0')),
    )
      ? null
      : result;
  }
}
