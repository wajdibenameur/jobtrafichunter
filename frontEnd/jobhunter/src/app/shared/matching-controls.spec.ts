import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatchingControls } from './matching-controls';
import { I18n } from '../core/i18n';

describe('Matching preview controls', () => {
  let fixture: ComponentFixture<MatchingControls>;
  let http: HttpTestingController;
  let element: HTMLElement;
  beforeEach(() => {
    localStorage.removeItem('jobhunter.locale');
    TestBed.configureTestingModule({
      imports: [MatchingControls],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    fixture = TestBed.createComponent(MatchingControls);
    fixture.componentRef.setInput('profile', 'profile-id');
    http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/matching/policies').flush([]);
    element = fixture.nativeElement as HTMLElement;
  });
  afterEach(() => http.verify());
  async function ready(enabled = true): Promise<void> {
    http
      .expectOne('/api/matching/capabilities')
      .flush({
        ready: enabled,
        reason: 'PREVIEW_ONLY',
        ...(enabled ? { candidate_id: 'candidate-id', candidate_revision: 2 } : {}),
      });
    await fixture.whenStable();
  }
  function start(): HTMLButtonElement {
    return Array.from(element.querySelectorAll('button')).find((item) =>
      item.textContent?.includes('Rechercher avec'),
    )!;
  }
  it('keeps preview disabled without an active reviewed candidate', async () => {
    await ready(false);
    expect(start().disabled).toBeTrue();
    expect(element.textContent).toContain('Validez et activez');
    http.expectNone('/api/search/executions');
  });
  it('requests explicit preview with expected candidate and waits for server', async () => {
    await ready();
    const emitted = jasmine.createSpy('started');
    fixture.componentInstance.started.subscribe(emitted);
    start().click();
    const request = http.expectOne('/api/search/executions');
    expect(request.request.body).toEqual({
      profile_id: 'profile-id',
      matching_preview: true,
      expected_candidate_id: 'candidate-id',
    });
    expect(emitted).not.toHaveBeenCalled();
    request.flush({ id: 'execution-id' });
    expect(emitted).toHaveBeenCalled();
  });
  it('rejects invalid weights before saving a policy', async () => {
    await ready();
    const mandatory = element.querySelector<HTMLInputElement>('#matching-weight-mandatory')!;
    mandatory.value = '99';
    mandatory.dispatchEvent(new Event('input'));
    element.querySelector('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
    await fixture.whenStable();
    http.expectNone('/api/matching/policies');
    expect(element.querySelector('[role=alert]')?.textContent).toContain('Barème invalide');
  });
  it('requires availability refresh after the active profile changes', async () => {
    await ready();
    start().click();
    http
      .expectOne('/api/search/executions')
      .flush({ error: { code: 'PROFILE_CHANGED' } }, { status: 409, statusText: 'Conflict' });
    await fixture.whenStable();
    expect(start().disabled).toBeTrue();
    expect(element.querySelector('[role=alert]')?.textContent).toContain('Actualisez');
  });
  it('translates the provisional warning into English', async () => {
    await ready();
    TestBed.inject(I18n).setLocale('en');
    await fixture.whenStable();
    expect(element.textContent).toContain('Experimental, uncalibrated');
    expect(element.textContent).toContain('No threshold or alerts');
  });
});
