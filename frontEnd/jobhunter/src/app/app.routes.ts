import { Routes } from '@angular/router';
import { guestGuard, ownerGuard } from './core/guards';

export const routes: Routes = [
  {
    path: 'auth/signin',
    canActivate: [guestGuard],
    loadComponent: () => import('./pages/signin/signin').then((m) => m.SignIn),
  },
  {
    path: '',
    canActivate: [ownerGuard],
    loadComponent: () => import('./layout/shell').then((m) => m.Shell),
    children: [
      {
        path: 'scraping',
        loadComponent: () => import('./pages/scraping/scraping').then((m) => m.Scraping),
      },
      {
        path: 'search',
        loadComponent: () => import('./pages/search/search').then((m) => m.Search),
      },
      {
        path: 'search-profiles',
        loadComponent: () =>
          import('./pages/search-profiles/search-profiles').then((m) => m.SearchProfiles),
      },
      {
        path: 'results',
        loadComponent: () => import('./pages/results/results').then((m) => m.Results),
      },
      {
        path: 'sources',
        loadComponent: () => import('./pages/sources/sources').then((m) => m.Sources),
      },
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () => import('./pages/dashboard/dashboard').then((m) => m.Dashboard),
      },
      {
        path: 'account',
        loadComponent: () => import('./pages/account/account').then((m) => m.Account),
      },
    ],
  },
  { path: '**', loadComponent: () => import('./pages/not-found').then((m) => m.NotFound) },
];
