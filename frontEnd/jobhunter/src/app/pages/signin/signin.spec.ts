import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { SignIn } from './signin';
import { I18n } from '../../core/i18n';

describe('Sign-in form', () => {
  beforeEach(() => {
    localStorage.removeItem('jobhunter.locale');
    TestBed.configureTestingModule({
      imports: [SignIn],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
  });
  afterEach(() => TestBed.inject(HttpTestingController).verify());
  it('validates empty fields without sending a login request', async () => {
    const fixture = TestBed.createComponent(SignIn);
    await fixture.whenStable();
    const element = fixture.nativeElement as HTMLElement;
    element.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    await fixture.whenStable();
    expect(element.querySelector('#email-error')?.textContent).toContain('valide');
    expect(element.querySelector('#password-error')).not.toBeNull();
    TestBed.inject(HttpTestingController).expectNone('/api/auth/login');
  });
  it('switches all form labels to English and updates document language', async () => {
    const fixture = TestBed.createComponent(SignIn);
    await fixture.whenStable();
    TestBed.inject(I18n).setLocale('en');
    await fixture.whenStable();
    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('h1')?.textContent).toBe('Welcome back');
    expect(element.querySelector('label[for=email]')?.textContent).toBe('Email address');
    expect(document.documentElement.lang).toBe('en');
  });
  it('shows a lockout response and clears the password', async () => {
    const fixture = TestBed.createComponent(SignIn);
    await fixture.whenStable();
    const element = fixture.nativeElement as HTMLElement;
    for (const [id, value] of [
      ['email', 'owner@example.test'],
      ['password', 'fixture-password'],
    ]) {
      const input = element.querySelector<HTMLInputElement>(`#${id}`)!;
      input.value = value!;
      input.dispatchEvent(new Event('input'));
    }
    element.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    TestBed.inject(HttpTestingController)
      .expectOne('/api/auth/login')
      .flush({}, { status: 429, statusText: 'Locked' });
    await fixture.whenStable();
    expect(element.querySelector('[role=alert]')?.textContent).toContain('Trop de tentatives');
    expect(element.querySelector<HTMLInputElement>('#password')?.value).toBe('');
  });
});
