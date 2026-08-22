# Rules engine

Supported declarative v1 assertions include `exists`, `equals`, `anyOf`, `allOf`, `not`, `gtePath`, `existsIn`, `notIn`, and a conservative `equalsPath` formula `end - start + 1`.

Rules that lack an executable condition/assertion (for example a registry lookup described only in prose/source metadata) are normalized as `unsupported` and are not executed from `message` or `notes` text.
