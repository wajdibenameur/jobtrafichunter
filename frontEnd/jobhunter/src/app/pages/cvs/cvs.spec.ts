import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { Cvs } from './cvs';
import { Candidate, CvVersion } from '../../core/cv-api';
import { I18n } from '../../core/i18n';
const version: CvVersion = {
  id: 'v1',
  document_id: 'd1',
  number: 1,
  filename: 'synthetic.pdf',
  byte_size: 50,
  state: 'READY',
  analysis_status: 'TEXT',
  active: false,
  created_at: '2026-11-08T12:00:00Z',
};
const candidate: Candidate = {
  id: 'p1',
  cv_version_id: 'v1',
  parent_id: null,
  revision: 1,
  status: 'DRAFT',
  active: false,
  created_at: version.created_at,
  validated_at: null,
  data: {
    fields: {
      professional_title: null,
      summary: null,
      years_experience: null,
      education: [],
      experiences: [],
      languages: [],
      certifications: [],
      skills: { languages: ['Python'] },
    },
    preferences: { locations: [], domains: [], target_levels: [], visa_needed: null },
    evidence: { 'skills.languages': [{ page: 1, start: 0, end: 6, quote: 'Python' }] },
    origins: {},
    warnings: [],
  },
  changed_fields: ['skills'],
  unknown_fields: ['professional_title'],
};
describe('Private CV review', () => {
  it('keeps failed publication removable without pretending its original is ready', async () => {
    fixture.destroy();
    fixture = TestBed.createComponent(Cvs);
    http.expectOne('/api/cvs').flush([{ ...version, state: 'FAILED' }]);
    http.expectOne('/api/cvs/capabilities').flush({ ready: true });
    await fixture.whenStable();
    element = fixture.nativeElement as HTMLElement;
    element.querySelector<HTMLButtonElement>('.version-item')!.click();
    await fixture.whenStable();
    expect(element.textContent).toContain('Publication échouée');
    expect(
      element.querySelector<HTMLButtonElement>('[data-testid=cv-generate]')!.disabled,
    ).toBeTrue();
    expect(element.querySelector<HTMLButtonElement>('.actions button')!.disabled).toBeTrue();
    http.expectNone('/api/cvs/versions/v1');
  });
  let fixture: ComponentFixture<Cvs>;
  let http: HttpTestingController;
  let element: HTMLElement;
  beforeEach(async () => {
    localStorage.removeItem('jobhunter.locale');
    TestBed.configureTestingModule({
      imports: [Cvs],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    fixture = TestBed.createComponent(Cvs);
    http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/cvs').flush([version]);
    http.expectOne('/api/cvs/capabilities').flush({ ready: true });
    http.expectOne('/api/cvs/versions/v1').flush({
      version,
      inspection: {
        status: 'TEXT',
        kind: 'PDF',
        pages: [{ number: 1, text: '<script>synthetic</script> Python' }],
      },
    });
    http.expectOne('/api/candidate-profiles/versions/v1').flush([candidate]);
    await fixture.whenStable();
    element = fixture.nativeElement as HTMLElement;
  });
  afterEach(() => http.verify());
  it('requires review before validation, then a separate activation', async () => {
    const validate = element.querySelector<HTMLButtonElement>('[data-testid=cv-validate]')!;
    expect(validate.disabled).toBeTrue();
    element.querySelector<HTMLInputElement>('.review-check input')!.click();
    await fixture.whenStable();
    validate.click();
    const request = http.expectOne('/api/candidate-profiles/p1/validate');
    expect(request.request.body).toEqual({ reviewed: true });
    http.expectNone('/api/candidate-profiles/p1/activate');
    request.flush({ ...candidate, status: 'VALIDATED' });
    await fixture.whenStable();
    expect(
      element.querySelector<HTMLButtonElement>('[data-testid=cv-activate]')!.disabled,
    ).toBeFalse();
    expect(element.textContent).toContain('Matching');
  });
  it('saves edits as a new draft and renders extracted HTML as text', async () => {
    expect(element.querySelector('script')).toBeNull();
    const input = element.querySelector<HTMLInputElement>('[formControlName=professional_title]')!;
    input.value = 'Synthetic developer';
    input.dispatchEvent(new Event('input'));
    await fixture.whenStable();
    expect(
      element.querySelector<HTMLButtonElement>('[data-testid=cv-validate]')!.disabled,
    ).toBeTrue();
    element.querySelector<HTMLButtonElement>('[data-testid=cv-save]')!.click();
    const request = http.expectOne('/api/candidate-profiles/p1/revisions');
    expect(request.request.body.fields.professional_title).toBe('Synthetic developer');
    request.flush({ ...candidate, id: 'p2', parent_id: 'p1', revision: 2 });
    await fixture.whenStable();
    TestBed.inject(I18n).setLocale('en');
    await fixture.whenStable();
    expect(element.textContent).toContain('Candidate profile');
    expect(
      element.querySelector<HTMLButtonElement>('[data-testid=cv-activate]')!.disabled,
    ).toBeTrue();
  });
});
