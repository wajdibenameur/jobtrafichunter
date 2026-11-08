import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { defaultCriteria, SearchProfile } from '../../core/search-api';
import { I18n } from '../../core/i18n';
import { Scraping } from './scraping';

describe('Scraping preparation', () => {
  let fixture: ComponentFixture<Scraping>;
  let http: HttpTestingController;
  let element: HTMLElement;
  const profile: SearchProfile = {
    id: 'fixture-profile',
    name: 'Synthetic profile',
    description: 'Fixture only',
    criteria: {
      ...defaultCriteria(),
      source_ids: ['source'],
      publication_days: 3,
      publication_minutes: null,
    },
    created_at: '2026-11-08T12:00:00Z',
    updated_at: '2026-11-08T12:00:00Z',
  };
  beforeEach(async () => {
    localStorage.removeItem('jobhunter.locale');
    TestBed.configureTestingModule({
      imports: [Scraping],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    fixture = TestBed.createComponent(Scraping);
    http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/search/profiles').flush([profile]);
    http.expectOne('/api/sources').flush([
      {
        id: 'source',
        name: '<script>inert fixture</script>',
        manual_import_supported: true,
        health_status: 'MANUAL_ONLY',
        automation_eligible: false,
        jobs_collected: null,
        last_successful_sync: null,
      },
    ]);
    http.expectOne('/api/search/executions').flush([]);
    await fixture.whenStable();
    element = fixture.nativeElement;
  });
  afterEach(() => http.verify());
  function button(text: string): HTMLButtonElement {
    return [...element.querySelectorAll<HTMLButtonElement>('button')].find(
      (b) => b.textContent?.trim() === text,
    )!;
  }
  it('shows actual manual capabilities and never launches unavailable collection actions', () => {
    expect(button('Lancer la recherche').disabled).toBeTrue();
    expect(button('Arrêter').disabled).toBeTrue();
    expect(button('Tester la source').disabled).toBeTrue();
    button('Lancer la recherche').click();
    http.expectNone((r) => r.method === 'POST');
    expect(element.textContent).toContain('Non mesuré');
    expect(element.textContent).toContain('Liens et import manuel');
    expect(element.querySelector('script')).toBeNull();
  });
  it('saves strict criteria through the existing profile endpoint and waits for confirmation', async () => {
    element.querySelector<HTMLInputElement>('input[type=radio][value="120"]')!.click();
    button('Enregistrer les critères du profil').click();
    const request = http.expectOne('/api/search/profiles/fixture-profile');
    expect(request.request.method).toBe('PUT');
    expect(request.request.body.criteria.publication_minutes).toBe(120);
    expect(request.request.body.criteria.publication_days).toBe(0);
    expect(request.request.body.name).toBe(profile.name);
    expect(element.querySelector('.success-note')).toBeNull();
    request.flush({ ...profile, criteria: request.request.body.criteria });
    await fixture.whenStable();
    expect(element.querySelector('.success-note')?.textContent).toContain('Profil enregistré');
  });
  it('displays save errors without pretending that the profile was saved', async () => {
    button('Enregistrer les critères du profil').click();
    http
      .expectOne('/api/search/profiles/fixture-profile')
      .flush({}, { status: 500, statusText: 'Fixture error' });
    await fixture.whenStable();
    expect(element.querySelector('[role=alert]')).not.toBeNull();
    expect(element.querySelector('.success-note')).toBeNull();
    expect(button('Enregistrer les critères du profil').disabled).toBeFalse();
  });
  it('uses English and distinguishes local history from collection', async () => {
    TestBed.inject(I18n).setLocale('en');
    await fixture.whenStable();
    expect(element.textContent).toContain('No automatic collection configured');
    expect(element.textContent).toContain('They are not external collection runs');
    expect(button('Start search').disabled).toBeTrue();
  });
});
