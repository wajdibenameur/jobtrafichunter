import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Session } from './session';
import { sessionInterceptor } from './session.interceptor';
import { safeReturnUrl } from './guards';

const owner = { id: 'fixture-owner', email: 'owner@example.test' };
describe('Session and credential interceptor', () => {
  let session: Session;
  let http: HttpClient;
  let backend: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([sessionInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    session = TestBed.inject(Session);
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
  });
  afterEach(() => backend.verify());

  function authenticate(): void {
    session.login({ email: owner.email, password: 'fixture-password' }).subscribe();
    const request = backend.expectOne('/api/auth/login');
    expect(request.request.withCredentials).toBeTrue();
    request.flush({ authenticated: true, owner });
  }
  it('shares one refresh across simultaneous 401 responses and retries both requests', () => {
    authenticate();
    const results: string[] = [];
    http.get('/api/account?first').subscribe(() => results.push('first'));
    http.get('/api/account?second').subscribe(() => results.push('second'));
    backend.expectOne('/api/account?first').flush({}, { status: 401, statusText: 'Unauthorized' });
    backend.expectOne('/api/account?second').flush({}, { status: 401, statusText: 'Unauthorized' });
    backend.expectOne('/api/auth/refresh').flush({ authenticated: true, owner });
    backend.expectOne('/api/account?first').flush(owner);
    backend.expectOne('/api/account?second').flush(owner);
    expect(results).toEqual(['first', 'second']);
    expect(session.state()).toBe('authenticated');
  });
  it('does not refresh after a failed password login', () => {
    let failed = false;
    session
      .login({ email: owner.email, password: 'wrong' })
      .subscribe({ error: () => (failed = true) });
    backend.expectOne('/api/auth/login').flush({}, { status: 401, statusText: 'Unauthorized' });
    backend.expectNone('/api/auth/refresh');
    expect(failed).toBeTrue();
  });
  it('clears the session when the refresh cookie has expired', () => {
    authenticate();
    http.get('/api/account').subscribe({ error: () => {} });
    backend.expectOne('/api/account').flush({}, { status: 401, statusText: 'Unauthorized' });
    backend.expectOne('/api/auth/refresh').flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(session.owner()).toBeNull();
    expect(session.state()).toBe('anonymous');
  });
  it('never loops if the retried request is still unauthorized', () => {
    authenticate();
    http.get('/api/account').subscribe({ error: () => {} });
    backend.expectOne('/api/account').flush({}, { status: 401, statusText: 'Unauthorized' });
    backend.expectOne('/api/auth/refresh').flush({ authenticated: true, owner });
    backend.expectOne('/api/account').flush({}, { status: 401, statusText: 'Unauthorized' });
    backend.expectNone('/api/auth/refresh');
    expect(session.owner()).toBeNull();
  });
  it('distinguishes an unavailable backend from a signed-out owner', () => {
    let restored: unknown = 'pending';
    session.check().subscribe((value) => (restored = value));
    backend.expectOne('/api/auth/me').flush({}, { status: 503, statusText: 'Unavailable' });
    expect(restored).toBeNull();
    expect(session.state()).toBe('unavailable');
  });
  it('does not restore a session from a check response arriving after logout', () => {
    session.check().subscribe();
    const stale = backend.expectOne('/api/auth/me');
    session.logout().subscribe();
    backend.expectOne('/api/auth/logout').flush(null);
    stale.flush(owner);
    expect(session.owner()).toBeNull();
    expect(session.state()).toBe('anonymous');
  });
  it('keeps a failed logout visible instead of pretending the session was revoked', () => {
    authenticate();
    session.logout().subscribe({ error: () => {} });
    backend.expectOne('/api/auth/logout').flush({}, { status: 503, statusText: 'Unavailable' });
    expect(session.owner()?.email).toBe(owner.email);
  });
  it('does not add credentials or retry behavior to external URLs', () => {
    http.get('https://example.test/public').subscribe();
    const request = backend.expectOne('https://example.test/public');
    expect(request.request.withCredentials).toBeFalse();
    request.flush({});
  });
});

describe('Safe post-login navigation', () => {
  it('rejects external and unexpected destinations', () => {
    for (const value of [
      'https://example.test',
      '//evil.test',
      '/auth/signin',
      '/account/evil',
      null,
    ]) {
      expect(safeReturnUrl(value)).toBe('/dashboard');
    }
    expect(safeReturnUrl('/account')).toBe('/account');
  });
});
