<script lang="ts">
	import {
		AccentHeading,
		ConfidenceMeter,
		EvidenceDisclosure,
		GridSurface,
		MetadataStrip,
		Panel,
		SafeLocator,
		SourceMetadata,
		StatePanel,
		StatusChip,
		UtcDate
	} from '#lib/components/index.ts';
	import type { EvidenceRead, SourceRead } from '#lib/api/contracts.ts';

	const source: SourceRead = {
		id: '10000000-0000-4000-8000-000000000001',
		name: 'Published source',
		kind: 'fixture',
		base_url: 'https://example.test'
	};
	const evidence: EvidenceRead = {
		id: '20000000-0000-4000-8000-000000000001',
		citation: 'Representative evidence citation',
		excerpt: '<img src=x onerror="alert(\'untrusted strings remain text\')">',
		locator: 'https://example.test/reports/representative',
		captured_at: '2026-01-02T03:04:05Z',
		confidence: 86,
		origin: 'imported',
		raw_evidence_id: null,
		source
	};
	let retries = $state(0);
</script>

<svelte:head>
	<title>Component gallery | WATCHTOWER</title>
	<meta name="description" content="WATCHTOWER shared component and state gallery." />
</svelte:head>

<GridSurface>
	<div class="gallery">
		<AccentHeading
			eyebrow="TASK 31 / SHARED SYSTEM"
			title="Intelligence interface primitives"
			description="A review surface for reusable hierarchy, provenance, state and evidence components."
		/>

		<MetadataStrip
			items={[
				{ label: 'VIEWPORTS', value: '320 · 768 · 1440' },
				{ label: 'BOUNDARY', value: 'Public reads only' },
				{ label: 'MOTION', value: 'Reduced-motion aware' }
			]}
		/>

		<div class="gallery-grid">
			<Panel eyebrow="SEMANTIC LABELS" title="Intelligence and operational state">
				<div class="chips">
					<StatusChip label="OBSERVED" tone="observed" />
					<StatusChip label="ASSESSED" tone="assessed" />
					<StatusChip label="CRITICAL" tone="critical" />
					<StatusChip label="READY" tone="ready" />
				</div>
				<p class="guidance">Labels and marker shapes preserve meaning without relying on color.</p>
			</Panel>

			<Panel eyebrow="PROVENANCE" title="Source and confidence">
				<div class="stack">
					<SourceMetadata {source} nativeId="fixture--source--01" />
					<ConfidenceMeter value={86} />
					<div class="date-row"><span>CAPTURED</span><UtcDate value="2026-01-02T03:04:05Z" /></div>
				</div>
			</Panel>
		</div>

		<Panel eyebrow="EVIDENCE" title="Disclosure and safe locator">
			<div class="stack">
				<EvidenceDisclosure {evidence} />
				<div class="locator-row">
					<span>REJECTED SCHEME</span>
					<SafeLocator value="javascript:alert('unsafe')" />
				</div>
			</div>
		</Panel>

		<section aria-labelledby="states-title">
			<div class="section-heading">
				<p>SHARED STATES</p>
				<h2 id="states-title">Loading, empty and recoverable failure</h2>
			</div>
			<div class="state-grid">
				<StatePanel
					state="loading"
					title="Loading intelligence"
					message="Published records are being requested."
				/>
				<StatePanel
					state="empty"
					title="No published intelligence"
					message="No records matched the current scope."
				/>
				<StatePanel
					state="error"
					title="Panel unavailable"
					message={`Retry preserves successful panels. Attempts: ${retries}`}
					requestId="fixture-request-id"
					onRetry={() => (retries += 1)}
				/>
			</div>
		</section>
	</div>
</GridSurface>

<style>
	.gallery {
		display: grid;
		gap: var(--space-7);
		max-width: var(--content-width);
		min-height: calc(100vh - var(--header-height));
		margin: 0 auto;
		padding: clamp(3rem, 7vw, 6rem) var(--space-5);
	}

	.gallery-grid,
	.state-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--space-5);
	}

	.state-grid {
		grid-template-columns: repeat(3, minmax(0, 1fr));
	}

	.chips,
	.locator-row,
	.date-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-3);
	}

	.stack {
		display: grid;
		gap: var(--space-4);
	}

	.guidance {
		margin: var(--space-4) 0 0;
		color: var(--color-ink-muted);
	}

	.date-row,
	.locator-row {
		justify-content: space-between;
	}

	.date-row > span,
	.locator-row > span,
	.section-heading p {
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	.section-heading p,
	.section-heading h2 {
		margin: 0;
	}

	.section-heading h2 {
		margin-top: var(--space-2);
	}

	@media (max-width: 62rem) {
		.state-grid {
			grid-template-columns: 1fr;
		}
	}

	@media (max-width: 48rem) {
		.gallery-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
