# Phase 4 Publishing

## Supported platforms

The backend currently has publisher clients for:

- X (`https://api.x.com/2/tweets`)
- LinkedIn (`https://api.linkedin.com/rest/posts`)

Text publishing is implemented. Image upload is validated but intentionally not sent because the current X and LinkedIn clients do not implement platform media-upload APIs. Audio is not treated as a publishable attachment.

## Environment variables

OAuth application configuration is loaded from `.env`:

- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_REDIRECT_URI`
- `LINKEDIN_CLIENT_ID`
- `LINKEDIN_CLIENT_SECRET`
- `LINKEDIN_REDIRECT_URI`
- `LINKEDIN_API_VERSION` (optional; defaults to `20240201`)

Client secrets and access tokens remain server-side and are never returned by the API.

## Authorization

Use `GET /api/publishing/{platform}/connect` to obtain an authorization URL. The backend stores a short-lived OAuth state in SQLite. The provider redirects to `GET /api/publishing/{platform}/callback`, which validates the state, exchanges the authorization code, fetches the account identity, and stores the access/refresh tokens in `social_accounts`.

The current application has no encryption-at-rest or user-authentication layer. Tokens are stored in the existing local SQLite design and must be protected as server-side secrets. OAuth scopes and platform API permissions must be approved/configured in the provider developer applications.

## Publishing

Publishing is explicit and separate from the LangGraph generation workflow:

```text
POST /api/content/{content_id}/publish
```

The request accepts `platform` (`X` or `LinkedIn`) and optional `media_ids`. Only `approved` or `completed` content with non-empty canonical `final_content` can be published. The exact `generated_content.content` value is sent to the platform publisher.

Successful and failed attempts are stored in `content_publications`. A second successful publish to the same platform/account is rejected unless `republish: true` is supplied. Failed attempts remain in history and can be retried with:

```text
POST /api/publications/{publication_id}/retry
```

Useful status endpoints:

- `GET /api/publishing/accounts`
- `GET /api/content/{content_id}/publications`
- `GET /api/publications/{publication_id}`
- `DELETE /api/publishing/{platform}/disconnect`

Deleting content with publication history is blocked. Deleting a local record does not and cannot unpublish a post already created on X or LinkedIn.

## Publication statuses

Publication attempts use:

- `pending`
- `publishing`
- `published`
- `failed`
- `cancelled` (reserved for future explicit cancellation)

A publication failure does not change the content's final text or content lifecycle status.
