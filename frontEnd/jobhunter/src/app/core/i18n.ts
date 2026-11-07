import { DOCUMENT } from '@angular/common';
import { inject, Injectable, signal } from '@angular/core';
import { sourcesFr, sourcesEn } from './sources-translations';

const fr = {
  ...sourcesFr,
  app: 'JobHunter AI',
  tagline: 'Votre prochain chapitre commence ici.',
  signIn: 'Se connecter',
  signInTitle: 'Heureux de vous retrouver',
  signInSubtitle: 'Connectez-vous à votre espace de recherche d’emploi.',
  email: 'Adresse e-mail',
  password: 'Mot de passe',
  showPassword: 'Afficher le mot de passe',
  hidePassword: 'Masquer le mot de passe',
  emailRequired: 'Saisissez une adresse e-mail valide.',
  passwordRequired: 'Saisissez votre mot de passe.',
  signingIn: 'Connexion en cours…',
  secureSpace: 'Un espace qui vous appartient',
  privateSpace: 'Votre profil, vos recherches et vos prochaines opportunités, au même endroit.',
  ownerOnly: 'Cet espace est réservé à son propriétaire.',
  noAccount: 'Utilisez le compte créé lors de la configuration de JobHunter.',
  invalidCredentials: 'Adresse e-mail ou mot de passe incorrect.',
  locked: 'Trop de tentatives. Réessayez dans quelques minutes.',
  unavailable: 'Le service est indisponible. Vérifiez la connexion et réessayez.',
  unexpectedError: 'Une erreur est survenue. Veuillez réessayer.',
  expired: 'Votre session a expiré. Reconnectez-vous pour continuer.',
  signingOut: 'Déconnexion…',
  signOut: 'Se déconnecter',
  logoutError: 'La déconnexion a échoué. Réessayez.',
  dashboard: 'Tableau de bord',
  search: 'Recherche',
  results: 'Résultats',
  cvs: 'Mes CV',
  profiles: 'Profils de recherche',
  sources: 'Sources',
  applications: 'Candidatures',
  history: 'Historique',
  notifications: 'Notifications',
  account: 'Mon compte',
  workspace: 'ESPACE PERSONNEL',
  preferences: 'PRÉFÉRENCES',
  soon: 'Bientôt',
  openMenu: 'Ouvrir la navigation',
  closeMenu: 'Fermer la navigation',
  skipContent: 'Aller au contenu',
  language: 'Langue',
  connected: 'Session active',
  welcome: 'Bienvenue dans votre espace',
  dashboardSubtitle: 'Une recherche plus claire, des opportunités qui vous ressemblent.',
  readyTitle: 'Préparez votre prochaine opportunité.',
  readyBody:
    'JobHunter réunira votre profil, vos sources et vos candidatures dans un seul espace. Votre compte est prêt.',
  viewAccount: 'Voir mon compte',
  privateLabel: 'VOTRE ESPACE, VOTRE PARCOURS',
  opportunities: 'Vos opportunités',
  noOpportunities: 'Votre recherche prend bientôt forme',
  noOpportunitiesBody:
    'Les offres découvertes et leurs correspondances apparaîtront ici lorsque la recherche sera disponible.',
  journey: 'Les étapes de votre recherche',
  journeySubtitle: 'Un parcours simple, du profil à la candidature.',
  stepAccount: 'Votre compte',
  stepAccountBody: 'Votre espace personnel est prêt et sécurisé.',
  stepCv: 'Votre profil professionnel',
  stepCvBody: 'Ajoutez un CV, puis vérifiez les informations extraites.',
  stepSearch: 'Vos critères de recherche',
  stepSearchBody: 'Choisissez vos sources et les opportunités qui vous intéressent.',
  stepMatches: 'Vos meilleures correspondances',
  stepMatchesBody: 'Retrouvez des offres classées avec des explications claires.',
  available: 'Disponible',
  personalAccount: 'Votre compte personnel',
  accountSubtitle: 'Les informations de votre session et de votre espace.',
  owner: 'Propriétaire',
  sessionSecurity: 'Une connexion protégée',
  securityBody: 'Votre session utilise des cookies sécurisés. Vous pouvez la fermer à tout moment.',
  singleOwner: 'Un compte unique',
  singleOwnerBody: 'Cet espace est personnel. Aucune inscription publique n’est ouverte.',
  accountLoadError: 'Impossible de charger votre compte.',
  retry: 'Réessayer',
  loading: 'Chargement de votre espace…',
  footer: 'Un nouvel élan pour votre recherche.',
  comingFeature: 'Cette fonctionnalité sera bientôt disponible.',
  notFoundTitle: 'Cette page est introuvable',
  notFoundBody: 'Retrouvez votre espace depuis le tableau de bord.',
  backDashboard: 'Revenir au tableau de bord',
} as const;
export type TranslationKey = keyof typeof fr;
const en: Record<TranslationKey, string> = {
  ...sourcesEn,
  app: 'JobHunter AI',
  tagline: 'Your next chapter starts here.',
  signIn: 'Sign in',
  signInTitle: 'Welcome back',
  signInSubtitle: 'Sign in to your personal job search workspace.',
  email: 'Email address',
  password: 'Password',
  showPassword: 'Show password',
  hidePassword: 'Hide password',
  emailRequired: 'Enter a valid email address.',
  passwordRequired: 'Enter your password.',
  signingIn: 'Signing in…',
  secureSpace: 'A space of your own',
  privateSpace: 'Your profile, your searches and your next opportunities, together.',
  ownerOnly: 'This workspace is reserved for its owner.',
  noAccount: 'Use the account created when JobHunter was set up.',
  invalidCredentials: 'Incorrect email address or password.',
  locked: 'Too many attempts. Try again in a few minutes.',
  unavailable: 'The service is unavailable. Check your connection and try again.',
  unexpectedError: 'Something went wrong. Please try again.',
  expired: 'Your session has expired. Sign in to continue.',
  signingOut: 'Signing out…',
  signOut: 'Sign out',
  logoutError: 'Sign out failed. Please try again.',
  dashboard: 'Dashboard',
  search: 'Search',
  results: 'Results',
  cvs: 'My CVs',
  profiles: 'Search profiles',
  sources: 'Sources',
  applications: 'Applications',
  history: 'History',
  notifications: 'Notifications',
  account: 'My account',
  workspace: 'PERSONAL WORKSPACE',
  preferences: 'PREFERENCES',
  soon: 'Soon',
  openMenu: 'Open navigation',
  closeMenu: 'Close navigation',
  skipContent: 'Skip to content',
  language: 'Language',
  connected: 'Session active',
  welcome: 'Welcome to your workspace',
  dashboardSubtitle: 'A clearer search, opportunities that fit you.',
  readyTitle: 'Get ready for your next opportunity.',
  readyBody:
    'JobHunter will bring your profile, sources and applications together. Your personal account is ready.',
  viewAccount: 'View my account',
  privateLabel: 'YOUR SPACE, YOUR JOURNEY',
  opportunities: 'Your opportunities',
  noOpportunities: 'Your search will take shape here',
  noOpportunitiesBody:
    'Discovered jobs and their match explanations will appear here when search is available.',
  journey: 'Your search journey',
  journeySubtitle: 'A simple path from profile to application.',
  stepAccount: 'Your account',
  stepAccountBody: 'Your personal workspace is ready and protected.',
  stepCv: 'Your professional profile',
  stepCvBody: 'Add a CV, then review the extracted information.',
  stepSearch: 'Your search criteria',
  stepSearchBody: 'Choose your sources and the opportunities you care about.',
  stepMatches: 'Your best matches',
  stepMatchesBody: 'Find ranked jobs with clear explanations.',
  available: 'Available',
  personalAccount: 'Your personal account',
  accountSubtitle: 'Your session and workspace information.',
  owner: 'Owner',
  sessionSecurity: 'A protected connection',
  securityBody: 'Your session uses secure cookies. You can close it at any time.',
  singleOwner: 'One personal account',
  singleOwnerBody: 'This is your personal workspace. Public registration is closed.',
  accountLoadError: 'Your account could not be loaded.',
  retry: 'Try again',
  loading: 'Loading your workspace…',
  footer: 'A fresh start for your job search.',
  comingFeature: 'This feature will be available soon.',
  notFoundTitle: 'This page could not be found',
  notFoundBody: 'Find your workspace from the dashboard.',
  backDashboard: 'Back to dashboard',
};
@Injectable({ providedIn: 'root' })
export class I18n {
  private readonly document = inject(DOCUMENT);
  readonly locale = signal<'fr' | 'en'>('fr');
  constructor() {
    try {
      if (localStorage.getItem('jobhunter.locale') === 'en') this.locale.set('en');
    } catch {
      /* optional UI preference */
    }
    this.document.documentElement.lang = this.locale();
  }
  t(key: TranslationKey): string {
    return (this.locale() === 'fr' ? fr : en)[key];
  }
  setLocale(locale: 'fr' | 'en'): void {
    this.locale.set(locale);
    this.document.documentElement.lang = locale;
    try {
      localStorage.setItem('jobhunter.locale', locale);
    } catch {
      /* no session data stored */
    }
  }
}
