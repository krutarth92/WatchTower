<script lang="ts">
	import type { EvidenceRead } from '#lib/api/contracts.ts';
	import ConfidenceMeter from './ConfidenceMeter.svelte';
	import SafeLocator from './SafeLocator.svelte';
	import SourceMetadata from './SourceMetadata.svelte';
	import UtcDate from './UtcDate.svelte';
	let { evidence }: { evidence: EvidenceRead } = $props();
</script>

<details>
	<summary><span aria-hidden="true">+</span> Evidence · {evidence.citation}</summary>
	<div class="evidence-body">
		<SourceMetadata source={evidence.source} />
		{#if evidence.excerpt}<blockquote>{evidence.excerpt}</blockquote>{/if}
		<div class="evidence-meta">
			{#if evidence.captured_at}<UtcDate value={evidence.captured_at} />{/if}
			<SafeLocator value={evidence.locator} />
		</div>
		<ConfidenceMeter value={evidence.confidence} />
	</div>
</details>

<style>
	details {
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-md);
		background: var(--color-surface-raised);
	}

	summary {
		min-height: 2.75rem;
		padding: var(--space-3) var(--space-4);
		cursor: pointer;
		font-weight: 650;
	}

	summary span {
		margin-right: var(--space-2);
		color: var(--color-primary);
		font-family: var(--font-mono);
	}

	.evidence-body {
		display: grid;
		gap: var(--space-4);
		padding: 0 var(--space-4) var(--space-4);
	}

	blockquote {
		margin: 0;
		padding-left: var(--space-4);
		border-left: var(--border-width) solid var(--color-secondary);
		color: var(--color-ink-muted);
	}

	.evidence-meta {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--space-3);
	}
</style>
