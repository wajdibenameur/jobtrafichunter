# LinkedIn via Apify — vérification de Phase A

Date : 2026-11-08. **UNVERIFIED, désactivé ; aucun lancement autorisé.**
Lecture de documentation publique uniquement : aucun token, compte, Actor,
dataset ou run utilisateur interrogé. Aucun outil Apify n’est exposé dans cette
session ; aucune conclusion n’est tirée sur la configuration MCP de la machine.

## Autorisation de la source

- [Conditions LinkedIn, §8.2](https://www.linkedin.com/legal/user-agreement) :
  restrictions sur le scraping et les accès automatisés non autorisés.
- [robots.txt LinkedIn](https://www.linkedin.com/robots.txt) : accès automatisé
  soumis à autorisation expresse ; les exceptions de certains robots ne sont pas
  une permission accordée à ce projet ou à un Actor quelconque.
- [Conditions Actors Apify](https://docs.apify.com/legal/actor-terms-and-conditions),
  notamment §2 et §9 : obligations de l’utilisateur et absence de garantie de
  conformité des Community Actors. Le catalogue Apify ne vaut pas permission LinkedIn.
- [Conditions générales Apify](https://docs.apify.com/legal/general-terms-and-conditions)
  consultées ; les conditions propres du créateur restent à examiner.

Conclusion technique pour JobHunter : aucun Actor identifié, aucun accès autorisé
ou accord spécifique démontré, aucune revue fournisseur complète. Ne pas renseigner
`PERMITTED`, `robots_allowed=true` ou `access_confirmed=true` sur cette seule base.
Les règles AGENTS/SPEC interdisant le scraping restent applicables. Un test réel
exige une méthode expressément autorisée ; l’accord de dépense seul ne suffit pas.

## Documentation API examinée

| Fonction | Source officielle | Point retenu |
| --- | --- | --- |
| Authentification | [API](https://docs.apify.com/api/v2) | Token conservé backend, en-tête Bearer proposé |
| Vérification du compte | [users/me](https://docs.apify.com/api/v2/users-me-get) | GET sans Actor ; réponse privée à réduire à un DTO, jamais à relayer brute |
| Lancement asynchrone | [Run Actor](https://docs.apify.com/api/v2/actors-runs-post) | Retour d’un run et defaultDatasetId ; paramètres timeout/build/limites |
| Statut et coût | [Get Actor run](https://docs.apify.com/api/v2/actor-run-get) | usageTotalUsd peut être absent ; conserver null et date d’observation |
| Résultats paginés | [Dataset items](https://docs.apify.com/api/v2/dataset-items-get) | offset/limit et compteurs de pagination |
| Annulation distante | [Abort](https://docs.apify.com/api/v2/actor-run-abort-post) | Une demande d’arrêt n’est pas un remboursement ou une preuve d’arrêt instantané |

La référence REST décrit `maxTotalChargeUsd` comme plafond par run pour les modèles
tarifaires et `maxItems` comme limite facturable pay-per-result, sans garantir le
nombre de résultats retournés. La [référence du client JS](https://docs.apify.com/api/client/js/reference/next/interface/ActorCallOptions)
décrit encore le plafond monétaire comme pay-per-event. Vérifier le modèle réel et
le support de l’Actor choisi ; ni plafond global du compte, ni coût total garanti.
Appliquer aussi une limite locale d’import de 10 par défaut, indépendante du prix.

La référence de lancement consultée ne documente pas de clé d’idempotence de
création de run. **Ne pas en inventer une.** En cas de réponse perdue après un POST,
le run peut exister sans identifiant enregistré : bloquer le redémarrage automatique
et demander réconciliation. Aucune promesse d’exactly-once côté fournisseur.

## Informations manquantes avant activation

Actor exact, build/version, conditions du créateur, méthode et preuve d’autorisation,
schémas d’entrée/sortie et fixture anonymisée, tarif/modalités des limites, droits
du token et permissions Actor. Aucun tarif, crédit disponible ou coût réel vérifié.
Revue à renouveler au changement d’Actor/build/conditions et selon l’échéance de
90 jours prévue par le projet. Aucun contournement, cookie ou session LinkedIn.
