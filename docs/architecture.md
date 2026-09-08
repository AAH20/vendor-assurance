# Architecture and release boundaries

Current flow: authorized operator prepares a JSON bundle → validate exact source spans → select current document versions → produce deterministic findings → human acknowledges each finding → export an advisory decision and evidence package. The original bundle is retained in the export; therefore exports have the same confidentiality requirements as the inputs.

Each bundle is exactly one tenant, vendor and service. Do not mix products, regions or legal entities in a bundle. Document families group revisions. The highest supplied version is current, including when that version contains no claims: an older version must not silently fill missing current evidence. Validity extends through `valid_until`; overdue actions are open actions with due dates before `as_of`. Conflict comparison is exact text value comparison, not a units-aware or legal interpretation engine. A current evidence claim only establishes that supplied evidence exists, not that it satisfies an obligation.

Source citations contain document ID, version, SHA-256, Python Unicode character offsets and exact quotation. They are not byte offsets or PDF page coordinates. Missing-evidence and overdue-action findings derive from supplied structured records and make no document citation claim. Finding IDs are report-local. Report hashes include the full bundle hash and evaluation date. Decisions are invalidated by any bundle change or date change, requiring review again.

## Next production gates

1. Independent representative evaluation and paid design-partner validation.
2. Authenticated identity, server-derived tenant membership, role policy, purpose-specific grants, revocation and authorization at every record and retrieval boundary. Do not expose the current local API as a web service.
3. Durable transactional storage, encrypted evidence storage, retention/deletion policies, immutable version IDs, append-only externally anchored audit events, backup and recovery tests.
4. Ingestion sandbox, file-size limits, PDF/OCR provenance, malware handling, prompt-injection isolation and adversarial document tests before untrusted uploads.
5. Stable obligation identifiers, scoped entity/product/region/time relationships, reviewer-confirmed extraction, remediation ownership and separately approved outbound integrations.
6. Customer-specific deployment/security review, operational support and measured concurrency/reliability before handling sensitive live records.

## Optional stack decisions

Use relational records for permissions and commitments. Introduce LangGraph only for a bounded workflow that needs durable pauses; interrupts do not provide authentication. GraphRAG must outperform structured queries plus ordinary retrieval on the same held-out questions before adoption. Incorrect graph edges can spread incorrect conclusions, and deletion/revocation must cover nodes, edges, caches and embeddings. Pinecone is an optional managed retrieval service, not an OSS dependency or a compliance guarantee. Self-operated retrieval offers more operational control but transfers patching, backup and capacity work to the operator.

No model loop may alter authorization or make external commitments. Slack MCP would be a reviewed interface to separately authorized public channels; commercial evidence belongs in authorized evidence rooms, not private-channel scraping. Existing due-diligence agents require their own license, data-flow, permissions and accuracy review before integration.
