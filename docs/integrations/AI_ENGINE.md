# AI image engine contract

The desktop ERP does not run AI models. It communicates with the configured
`AI_ENGINE_URL` over HTTP and sends `Authorization: Bearer <key>` only when
`AI_ENGINE_API_KEY` is configured.

## Endpoints

- `POST /v1/jobs`: multipart form with a JSON `metadata` part and source `file`.
- `GET /v1/jobs/{job_id}`: returns job status, progress from 0–100, and a message.
- `DELETE /v1/jobs/{job_id}`: requests cancellation.
- `GET /v1/jobs/{job_id}/result`: returns the processed raster image.

The metadata object contains `tool` and `parameters`. Job responses contain
`job_id`, `status`, `progress`, and optional `message`. Supported statuses are
`queued`, `running`, `completed`, `failed`, and `cancelled`.

Network operations run in background workers. Transient unavailable responses
are retried, while failed jobs can be retried explicitly. Successful result
images are imported into managed artwork storage as new versions.

