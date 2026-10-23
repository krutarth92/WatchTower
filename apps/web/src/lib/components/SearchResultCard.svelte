<script lang="ts">
	import type { SearchResultRead } from '#lib/api/contracts.ts';
	import StatusChip from './StatusChip.svelte';
	import UtcDate from './UtcDate.svelte';

	let { result, fromSearch }: { result: SearchResultRead; fromSearch: string } = $props();

	const actorId = $derived(result.entity_type === 'actor' ? result.id : result.actor_id);
	const actorHref = $derived(
		actorId ? `/actors/${actorId}?fromSearch=${encodeURIComponent(fromSearch)}` : null
	);
	const entityLabel = $derived(result.entity_type.replace('_', ' ').toUpperCase());
	const matchLabel = $derived(result.match_kind === 'exact' ? 'EXACT MATCH' : 'FULL TEXT');
</script>

<article>
	<div class="result-index" aria-hidden="true"></div>
	<header>
		<div class="labels">
			<span class="entity">{entityLabel}</span>
			<span class="match">{matchLabel}</span>
			{#if result.intelligence_type}
				<StatusChip
					label={result.intelligence_type.toUpperCase()}
					tone={result.intelligence_type}
				/>
			{/if}
		</div>
		{#if actorHref}
			<h2><a href={actorHref}>{result.title}</a></h2>
		{:else}
			<h2>{result.title}</h2>
		{/if}
	</header>

	{#if result.summary}<p class="summary">{result.summary}</p>{/if}

	<dl>
		{#if result.external_id}
			<div>
				<dt>EXTERNAL ID</dt>
				<dd><code>{result.external_id}</code></dd>
			</div>
		{/if}
		{#if result.source_id}
			<div>
				<dt>SOURCE REF</dt>
				<dd><code>{result.source_id}</code></dd>
			</div>
		{/if}
		{#if result.observed_at}
			<div>
				<dt>OBSERVED</dt>
				<dd><UtcDate value={result.observed_at} /></dd>
			</div>
		{/if}
		{#if result.origin}
			<div>
				<dt>ORIGIN</dt>
				<dd>{result.origin}</dd>
			</div>
		{/if}
	</dl>

	<footer>
		<span>RELEVANCE {result.score.toFixed(3)}</span>
		{#if actorHref}
			<a href={actorHref}>Open actor context <span aria-hidden="true">→</span></a>
		{:else}
			<span class="self-contained">No public detail route</span>
		{/if}
	</footer>
</article>

<style>
	article {
		position: relative;
		display: grid;
		gap: var(--space-4);
		padding: var(--space-5) var(--space-5) var(--space-5) var(--space-6);
		border-top: var(--border-width) solid var(--color-border);
		background: transparent;
		transition: background var(--motion-fast) var(--easing-standard);
	}

	article:hover {
		background: var(--color-primary-faint);
	}

	.result-index {
		position: absolute;
		top: var(--space-5);
		bottom: var(--space-5);
		left: 0;
		width: 0.1875rem;
		background: var(--gradient-brand);
	}

	header {
		display: grid;
		gap: var(--space-3);
	}

	.labels {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-2);
	}

	.entity,
	.match,
	footer,
	dt {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	.entity {
		color: var(--color-primary);
		font-weight: 700;
	}

	.match {
		color: var(--color-ink-subtle);
	}

	h2 {
		margin: 0;
		font-size: clamp(1.2rem, 3vw, 1.65rem);
		line-height: 1.25;
	}

	h2 a {
		text-decoration-color: var(--color-border-strong);
		text-underline-offset: var(--space-1);
	}

	h2 a:hover {
		color: var(--color-primary);
		text-decoration-color: currentColor;
	}

	.summary {
		margin: 0;
		color: var(--color-ink-muted);
	}

	dl {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3) var(--space-6);
		margin: 0;
		padding: var(--space-3) 0;
		border-top: var(--border-width) solid var(--color-border);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	dl div {
		min-width: min(100%, 9rem);
	}

	dt {
		color: var(--color-ink-subtle);
	}

	dd {
		margin: var(--space-1) 0 0;
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
	}

	code {
		font-family: var(--font-mono);
		overflow-wrap: anywhere;
	}

	footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		color: var(--color-ink-subtle);
	}

	footer a {
		color: var(--color-primary);
		font-weight: 700;
		text-decoration: none;
	}

	.self-contained {
		text-align: right;
	}

	@media (max-width: 34rem) {
		article {
			padding: var(--space-4);
		}

		footer {
			align-items: flex-start;
			flex-direction: column;
		}

		.self-contained {
			text-align: left;
		}
	}
</style>
