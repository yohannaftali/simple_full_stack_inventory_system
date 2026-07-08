# GitHub Issues API — Field Reference

Base URL pattern: `https://api.github.com/repos/{owner}/{repo}/issues`

## Authentication

```
Header: Authorization: Bearer <your_token>
Header: Accept: application/vnd.github+json
Header: X-GitHub-Api-Version: 2022-11-28
```

## Create Issue — POST /repos/{owner}/{repo}/issues

| Field | Type | Notes |
|---|---|---|
| `title` | string | **Required** |
| `body` | string | Markdown supported |
| `labels` | array[string] | e.g. `["bug", "backend"]` |
| `assignees` | array[string] | GitHub usernames |
| `milestone` | int | Milestone number |

## Update Issue — PATCH /repos/{owner}/{repo}/issues/{issue_number}

Same fields as create. Use `state: "closed"` to close.

## Search Issues — GET /repos/{owner}/{repo}/issues

| Param | Notes |
|---|---|
| `state` | `open`, `closed`, `all` |
| `labels` | Comma-separated label names |
| `assignee` | GitHub username |
| `sort` | `created`, `updated`, `comments` |
| `direction` | `asc`, `desc` |

Note: GitHub's issues endpoint does not support full-text `search` param.
Use the Search API instead for keyword search:
```
GET https://api.github.com/search/issues?q={keywords}+repo:{owner}/{repo}+is:open
```

## Response shape (issue object)

```json
{
  "number": 1,
  "title": "...",
  "body": "...",
  "state": "open",
  "labels": [{ "name": "bug" }],
  "html_url": "https://github.com/org/repo/issues/1",
  "assignees": [{ "login": "...", "id": 1 }],
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Token Scopes Required

| Operation | Required scope |
|---|---|
| Read issues (public repo) | None (but rate-limited) |
| Read issues (private repo) | `repo` |
| Create/update issues | `repo` |

## Common Errors

| Code | Meaning |
|---|---|
| 401 | Invalid or missing token |
| 403 | Token lacks `repo` scope or rate limit hit |
| 404 | Repo not found or no access |
| 410 | Issues disabled on this repo |
| 422 | Validation failed |