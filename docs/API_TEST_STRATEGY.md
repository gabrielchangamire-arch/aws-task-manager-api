# API Test Strategy

This is the test strategy I use for the FastAPI task manager API. The main goal is to protect the task CRUD contract, validation behavior, and optional S3 attachment path without requiring real AWS credentials in normal test runs.

## Areas Under Test

- Health check and database connectivity
- Task creation, listing, fetching, updating, and deletion
- Pydantic request validation for required fields, string lengths, and enum values
- Not-found behavior for missing task IDs
- Partial update behavior for `PUT /tasks/{id}`
- Attachment behavior when S3 is disabled
- S3 upload helper behavior with moto-mocked AWS
- Error shape returned by the FastAPI exception handlers

## Validation Cases

- `POST /tasks` requires a non-empty `title`.
- `title` is limited to 200 characters.
- `description` is optional and limited to 5000 characters.
- `status` must be one of `pending`, `in_progress`, or `done`.
- `PUT /tasks/{id}` accepts partial updates but still validates any fields that are present.
- Invalid request bodies should return `422` with a structured `detail` response.

## CRUD Behavior Checks

- Creating a task returns `201` and includes the generated task ID.
- Listing tasks returns the tasks currently in the database.
- Fetching an existing task returns `200`.
- Fetching a missing task returns `404` with `task not found`.
- Updating an existing task returns the updated record.
- Updating only one field should leave the other fields unchanged.
- Deleting an existing task returns `204`.
- Fetching a deleted task returns `404`.

## Negative and Error-Handling Scenarios

- Empty title on create returns `422`.
- Invalid task ID on get/update/delete returns `404`.
- Attachment upload returns `503` when `S3_ENABLED=false`.
- Attachment upload should also be treated as unavailable if S3 is enabled but `S3_BUCKET_NAME` is missing.
- S3 upload failures are wrapped by the storage layer instead of leaking raw boto3 errors.
- Unexpected server exceptions should return the generic `internal server error` shape from `app.main`.

## Existing Automated Coverage

The pytest suite currently covers these areas:

| Test file | What it verifies |
|---|---|
| `tests/test_health.py` | `/health` returns `200` when the app and database session are available. |
| `tests/test_tasks.py` | Create, list, get, partial/full update, delete, not-found responses, empty-title validation, and attachment-disabled behavior. |
| `tests/test_s3_storage.py` | S3 disabled path and a moto-backed upload path that writes an object to a test bucket without using real AWS credentials. |
| `tests/conftest.py` | Test isolation with a throwaway SQLite database and S3 disabled by default. |

The GitHub Actions workflow adds a compile check and runs `pytest -q` on pushes and pull requests to `main`. That catches basic syntax/import regressions and the behavior covered by the current test suite.

## Representative Endpoint Test Cases

| ID | Endpoint | Scenario | Expected Result | Current Coverage |
|---|---|---|---|---|
| API-01 | `POST /tasks` | Create with title, description, and `pending` status. | `201`; response includes ID, timestamps, and submitted fields. | Covered in `test_create_task`. |
| API-02 | `POST /tasks` | Create with empty title. | `422`; task is not created. | Covered in `test_create_rejects_empty_title`. |
| API-03 | `GET /tasks/{id}` | Fetch a task that does not exist. | `404` with `task not found`. | Covered in `test_get_task_not_found`. |
| API-04 | `PUT /tasks/{id}` | Send only `status: done`. | `200`; status changes and other fields remain intact. | Covered in `test_update_task_partial`. |
| API-05 | `PUT /tasks/{id}` | Update a missing task. | `404` with `task not found`. | Covered in `test_update_task_not_found`. |
| API-06 | `DELETE /tasks/{id}` | Delete an existing task, then fetch it. | `204` on delete; later fetch returns `404`. | Covered in `test_delete_task`. |
| API-07 | `DELETE /tasks/{id}` | Delete a missing task. | `404` with `task not found`. | Covered in `test_delete_task_not_found`. |
| API-08 | `POST /tasks/{id}/attachment` | Upload while S3 is disabled. | `503`; message explains attachments are disabled. | Covered in `test_attachment_disabled_returns_503`. |
| API-09 | S3 helper | Upload with moto-backed bucket. | Object is written under the expected key prefix. | Covered in `test_upload_attachment_writes_to_bucket`. |

## Regression Risks

- Changing schema defaults could break existing clients that rely on `pending` as the default status.
- Editing error handlers could change the response shape the React dashboard expects.
- Adding real S3 support to more paths could accidentally require AWS credentials during local tests.
- Switching from SQLite to Postgres in more tests could expose transaction/session assumptions.
- Pagination changes could silently alter `GET /tasks` behavior if tests only check status codes.

## Future QA Improvements

- Add tests for invalid status values and over-limit title/description lengths.
- Add an integration test for S3 enabled but missing `S3_BUCKET_NAME`.
- Add pagination boundary tests for `limit` and `offset`.
- Add contract examples shared with the React dashboard so the UI and API stay aligned.
