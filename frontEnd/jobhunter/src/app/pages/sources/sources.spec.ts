import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Sources } from './sources';
import { I18n } from '../../core/i18n';
import { JobSource } from '../../core/source-api';

const source: JobSource = {
  id: '10000000-0000-4000-8000-000000000003',
  slug: 'keejob',
  name: 'Keejob',
  homepage: 'https://www.keejob.com',
  region: 'TN',
  integration_type: 'LINK_ONLY',
  legal_status: 'LINK_ONLY',
  enabled: false,
  automation_eligible: false,
  manual_import_supported: true,
  custom: false,
  settings: { keywords: '', location: '' },
  health_status: 'DISABLED',
  last_successful_sync: null,
  jobs_collected: null,
  reason: 'MANUAL_WORKFLOW',
};
describe('Sources workflows', () => {
  let fixture: ComponentFixture<Sources>;
  let http: HttpTestingController;
  let element: HTMLElement;
  beforeEach(async () => {
    localStorage.removeItem('jobhunter.locale');
    TestBed.configureTestingModule({
      imports: [Sources],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    fixture = TestBed.createComponent(Sources);
    http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/sources').flush([source]);
    http.expectOne((r) => r.url === '/api/jobs').flush({ items: [], total: 0 });
    await fixture.whenStable();
    element = fixture.nativeElement as HTMLElement;
  });
  afterEach(() => http.verify());
  function fill(selector: string, value: string): void {
    const input = element.querySelector<HTMLInputElement>(selector)!;
    input.value = value;
    input.dispatchEvent(new Event('input'));
  }
  it('waits for persistence before selecting a site and keeps automation unavailable', async () => {
    const checkbox = element.querySelector<HTMLInputElement>('[type=checkbox]')!;
    checkbox.click();
    const request = http.expectOne(`/api/sources/${source.id}`);
    expect(request.request.body).toEqual({ enabled: true });
    request.flush({ ...source, enabled: true, health_status: 'MANUAL_ONLY' });
    await fixture.whenStable();
    expect(checkbox.checked).toBeTrue();
    expect(element.textContent).toContain('aucune collecte automatique');
    expect(element.querySelector('.source-state')!.textContent).toContain('manuel');
  });
  it('reviews URL-only data locally and saves only after explicit confirmation', async () => {
    fill('[formControlName=original_url]', 'https://example.test/job');
    await fixture.whenStable();
    element.querySelector<HTMLButtonElement>('.import-card button[type=submit]')!.click();
    await fixture.whenStable();
    http.expectNone('/api/jobs/import');
    expect(element.querySelector('.preview-card')!.textContent).toContain('Non renseigné');
    element.querySelector<HTMLButtonElement>('.preview-card .btn-primary')!.click();
    const request = http.expectOne('/api/jobs/import');
    expect(request.request.body).toEqual({
      source_id: source.id,
      jobs: [{ original_url: 'https://example.test/job' }],
      confirm: true,
    });
    request.flush({ created_count: 1, existing_count: 0 });
    http.expectOne((r) => r.url === '/api/jobs').flush({ items: [], total: 1 });
    await fixture.whenStable();
    expect(element.querySelector('[role=status]')!.textContent).toContain('Import terminé');
  });
  it('invalidates a preview when edited and translates the complete workflow', async () => {
    fill('[formControlName=original_url]', 'https://example.test/job');
    await fixture.whenStable();
    element.querySelector<HTMLButtonElement>('.import-card button[type=submit]')!.click();
    await fixture.whenStable();
    expect(element.querySelector('.preview-card')).not.toBeNull();
    fill('[formControlName=title]', 'Changed');
    await fixture.whenStable();
    expect(element.querySelector('.preview-card')).toBeNull();
    TestBed.inject(I18n).setLocale('en');
    await fixture.whenStable();
    expect(element.textContent).toContain('Tunisian sites');
    expect(element.textContent).toContain('Review before import');
  });
  it('shows a save failure without claiming the toggle was saved', async () => {
    element.querySelector<HTMLInputElement>('[type=checkbox]')!.click();
    http
      .expectOne(`/api/sources/${source.id}`)
      .flush({}, { status: 503, statusText: 'Unavailable' });
    await fixture.whenStable();
    expect(element.querySelector('[role=alert]')!.textContent).toContain('Impossible');
    expect(element.querySelector('.source-state')!.textContent).toContain('Non sélectionnée');
    expect(element.querySelector<HTMLInputElement>('[type=checkbox]')!.checked).toBeFalse();
  });
});
