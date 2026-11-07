import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { Session } from './session';

export const sessionInterceptor: HttpInterceptorFn = (request, next) => {
  if (!request.url.startsWith('/api/')) return next(request);
  const session = inject(Session);
  const credentialed = request.clone({ withCredentials: true });
  const authMutation = /^\/api\/auth\/(login|refresh|logout)$/.test(request.url);
  return next(credentialed).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse) || error.status !== 401 || authMutation)
        return throwError(() => error);
      return session.refresh().pipe(
        switchMap(() => next(credentialed)),
        catchError((retryError: unknown) => {
          if (retryError instanceof HttpErrorResponse && retryError.status === 401) session.clear();
          return throwError(() => retryError);
        }),
      );
    }),
  );
};
