import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { SearchProfiles } from './search-profiles';
import { defaultCriteria } from '../../core/search-api';
import { I18n } from '../../core/i18n';
describe('Saved search profiles', () => {
  let fixture: ComponentFixture<SearchProfiles>;
  let http: HttpTestingController;
  let element: HTMLElement;
  beforeEach(async () => {
    localStorage.removeItem('jobhunter.locale');
    TestBed.configureTestingModule({
      imports: [SearchProfiles],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    fixture = TestBed.createComponent(SearchProfiles);
    http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/search/profiles').flush([]);
    http.expectOne('/api/sources').flush([{ id: 'source-id', name: 'Keejob' }]);
    await fixture.whenStable();
    element = fixture.nativeElement as HTMLElement;
  });
  afterEach(() => http.verify());
  it('does not save an invalid profile', async () => {
    element.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    await fixture.whenStable();
    http.expectNone('/api/search/profiles');
    expect(element.querySelector('[role=alert]')?.textContent).toContain('Vérifiez');
  });
  it('persists criteria and waits for the server before showing success', async () => {
    const name = element.querySelector<HTMLInputElement>('[formControlName=name]')!;
    name.value = 'Local test';
    name.dispatchEvent(new Event('input'));
    const checkbox = element.querySelector<HTMLInputElement>('[type=checkbox]')!;
    checkbox.click();
    element.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    const request = http.expectOne('/api/search/profiles');
    expect(request.request.method).toBe('POST');
    expect(request.request.body.criteria.source_ids).toEqual(['source-id']);
    expect(element.querySelector('.success-note')).toBeNull();
    request.flush({
      id: 'profile-id',
      name: 'Local test',
      description: '',
      criteria: { ...defaultCriteria(), source_ids: ['source-id'] },
      created_at: '2026-11-07T12:00:00Z',
      updated_at: '2026-11-07T12:00:00Z',
    });
    await fixture.whenStable();
    expect(element.querySelector('.success-note')?.textContent).toContain('Profil enregistré');
  });
  it('translates the editor and states the local scope', async () => {
    TestBed.inject(I18n).setLocale('en');
    await fixture.whenStable();
    expect(element.textContent).toContain('External sites are not queried');
    expect(element.textContent).toContain('Profile name');
    expect(element.textContent).toContain('Missing information');
  });
});
