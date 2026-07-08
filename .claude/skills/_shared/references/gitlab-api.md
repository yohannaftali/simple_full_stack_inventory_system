# GitLab Issues API — Field Reference

Base URL pattern: `https://{gitlab-host}/api/v4/projects/{id}/issues`

This project uses a **self-hosted GitLab** — derive `{gitlab-host}` from the
`origin` remote URL (`.git/config`), not `gitlab.com`.

Project ID can be either:
- The numeric ID (e.g., `12345`)
- The URL-encoded path (e.g., `org%2Frepo`)

## Authentication

```
Header: PRIVATE-TOKEN: <your_token>
```

## Create Issue — POST /projects/{id}/issues

| Field | Type | Notes |
|---|---|---|
| `title` | string | **Required** |
| `description` | string | Markdown supported |
| `labels` | string | Comma-separated, e.g. `"bug,backend"` |
| `assignee_ids` | array[int] | GitLab user IDs |
| `milestone_id` | int | Optional |
| `due_date` | string | Format: `YYYY-MM-DD` |
| `weight` | int | GitLab EE only |

## Update Issue — PUT /projects/{id}/issues/{issue_iid}

Same fields as create. Use `state_event: "close"` to close an issue.

## Search Issues — GET /projects/{id}/issues

| Param | Notes |
|---|---|
| `state` | `opened`, `closed`, `all` |
| `search` | Searches title and description |
| `labels` | Filter by label |
| `assignee_id` | Filter by assignee |
| `order_by` | `created_at`, `updated_at` |
| `sort` | `asc`, `desc` |

## Response shape (issue object)

```json
{
  "id": 1,
  "iid": 1,
  "title": "...",
  "description": "...",
  "state": "opened",
  "labels": ["bug"],
  "web_url": "https://{gitlab-host}/org/repo/-/issues/1",
  "assignees": [{ "username": "...", "name": "..." }],
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Common Errors

| Code | Meaning |
|---|---|
| 401 | Invalid or missing token |
| 403 | Token lacks `api` scope or user lacks project access |
| 404 | Project not found or no access |
| 422 | Validation failed (e.g., duplicate title, invalid field) |