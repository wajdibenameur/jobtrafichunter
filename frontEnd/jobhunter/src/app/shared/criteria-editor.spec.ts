import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CriteriaEditor } from './criteria-editor';
import { defaultCriteria } from '../core/search-api';
import { I18n } from '../core/i18n';

describe('Publication window editor', () => {
  let fixture: ComponentFixture<CriteriaEditor>;
  let element: HTMLElement;
  beforeEach(async () => {
    localStorage.removeItem('jobhunter.locale');
    TestBed.configureTestingModule({ imports: [CriteriaEditor] });
    fixture = TestBed.createComponent(CriteriaEditor);
    await fixture.whenStable();
    element = fixture.nativeElement;
  });
  function radio(value: string): HTMLInputElement {
    return element.querySelector<HTMLInputElement>(`input[type=radio][value="${value}"]`)!;
  }
  it('defaults new profiles to strict 24 hours', () => {
    expect(radio('1440').checked).toBeTrue();
    expect(fixture.componentInstance.getValue()?.publication_minutes).toBe(1440);
    expect(fixture.componentInstance.getValue()?.publication_days).toBe(0);
  });
  it('keeps a single active radio and saves minute windows', async () => {
    radio('120').click();
    await fixture.whenStable();
    expect(element.querySelectorAll('input[type=radio]:checked').length).toBe(1);
    expect(radio('1440').checked).toBeFalse();
    expect(fixture.componentInstance.getValue()?.publication_minutes).toBe(120);
    expect(fixture.componentInstance.dirty).toBeTrue();
  });
  it('retains saved historical 24-hour semantics instead of silently converting them', async () => {
    const criteria = { ...defaultCriteria(), publication_days: 1 as const };
    delete criteria.publication_minutes;
    fixture.componentRef.setInput('criteria', criteria);
    await fixture.whenStable();
    expect(radio('legacy').checked).toBeTrue();
    expect(fixture.componentInstance.getValue()?.publication_days).toBe(1);
    expect(fixture.componentInstance.getValue()?.publication_minutes).toBeNull();
  });
  it('preserves week and month windows in the historical day field', async () => {
    for (const days of [7, 30] as const) {
      radio(`${days}d`).click();
      await fixture.whenStable();
      const value = fixture.componentInstance.getValue();
      expect(value?.publication_days).toBe(days);
      expect(value?.publication_minutes).toBeNull();
      expect(value?.unknown_policy).toBe('include');
    }
  });
  it('translates the controls and explains unknown publication dates', async () => {
    TestBed.inject(I18n).setLocale('en');
    await fixture.whenStable();
    expect(element.textContent).toContain('Less than 2 h');
    expect(element.textContent).toContain('exclude unknown and future publication dates');
  });
});
