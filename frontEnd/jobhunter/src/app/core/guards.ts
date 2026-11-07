import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { Session } from './session';

export function safeReturnUrl(value: string | null): string {
  return value && /^\/(dashboard|account)(?:[?#].*)?$/.test(value) ? value : '/dashboard';
}
export const ownerGuard: CanActivateFn = (_route, state) => {
  const session = inject(Session);
  const router = inject(Router);
  if (session.owner()) return true;
  return session.check().pipe(
    map((owner) =>
      owner
        ? true
        : router.createUrlTree(['/auth/signin'], {
            queryParams: { returnUrl: safeReturnUrl(state.url) },
          }),
    ),
  );
};
export const guestGuard: CanActivateFn = () => {
  const session = inject(Session);
  const router = inject(Router);
  if (session.owner()) return router.createUrlTree(['/dashboard']);
  if (session.state() !== 'unknown') return true;
  return session
    .check()
    .pipe(map((owner) => (owner ? router.createUrlTree(['/dashboard']) : true)));
};
