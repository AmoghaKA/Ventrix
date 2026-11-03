# Shared Data Retrieval Policy

## Website crawling and robots.txt

Ventrix sends the `VentrixResearchBot/0.1` user agent and checks the origin's
`/robots.txt` before retrieving the site or its discovered pages. Rules are
evaluated with Python's `RobotFileParser`. Pages disallowed for this user agent
are not requested.

Ventrix treats a `404 Not Found` robots response as no published policy. Any
other non-success response, network or DNS error, unsafe redirect, oversized
robots file, or parser error blocks crawling for that origin for that
retrieval run. This is deliberately stricter than the broad robots protocol
fallbacks: access restrictions and unavailable policy files never grant
permission to crawl. Robots retrieval uses the same redirect checks, public IP
validation, DNS-pinned sockets, timeouts, and response-size limit as page
retrieval.

The retriever does not authenticate, solve CAPTCHAs, bypass paywalls, or evade
other access controls. Discovered page links stay on the startup website's
scheme, hostname, and port. A public redirect to another origin may be followed
only after that target independently passes URL and DNS checks. The configured
retrieval cache applies to robots responses as it does to page responses.
`Crawl-delay` and `Request-rate` directives supported by Python's parser are
observed between page requests.

## PDF extraction

PDFs are recognized by their `application/pdf` media type or PDF file header.
Text is extracted with `pypdf`; documents are limited to 2 MB, 100 pages, and
200,000 extracted characters by default. Page references are retained in
evidence metadata. Ventrix does not perform OCR, guess document passwords, or
treat encrypted, malformed, empty, oversized, or textless files as evidence.

An extraction failure is stored in `document_extraction_failures`, separate
from the evidence table. It records the source URL, stage, category, safe
description, and document name when available. A source that fails extraction
does not create an evidence record.
