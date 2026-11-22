<script lang="ts">
	import type { SearchResultRead } from '#lib/api/contracts.ts';
	import HighlightedText from './HighlightedText.svelte';
	import StatusChip from './StatusChip.svelte';
	import UtcDate from './UtcDate.svelte';

	let {
		result,
		fromSearch,
		query
	}: { result: SearchResultRead; fromSearch: string; query: string } = $props();

	const relatedActorHref = (actorId: string) =>
		`/actors/${actorId}?fromSearch=${encodeURIComponent(fromSearch)}`;
	const actorId = $derived(result.entity_type === 'actor' ? result.id : result.actor_id);
	const actorHref = $derived(
		actorId ? `/actors/${actorId}?fromSearch=${encodeURIComponent(fromSearch)}` : null
	);
	const relatedActorContextHref = $derived(
		result.related_actors[0] ? relatedActorHref(result.related_actors[0].id) : null
	);
	const entityLabel = $derived(
		result.entity_type.replace('_', ' ').replace(/^./, (value) => value.toUpperCase())
	);
	const matchLabel = $derived(result.match_kind === 'exact' ? 'Exact match' : 'Related match');
</script>

<article>
	<header>
		<div class="labels">
			<span
				class="entity"
				class:threat-entity={result.entity_type === 'indicator' ||
					result.entity_type === 'vulnerability'}>{entityLabel}</span
			>
			<span class="match">{matchLabel}</span>
			{#if result.intelligence_type}
				<StatusChip
					label={result.intelligence_type.toUpperCase()}
					tone={result.intelligence_type}
				/>
			{/if}
		</div>
		{#if actorHref}
			<h2><a href={actorHref}><HighlightedText text={result.title} {query} /></a></h2>
		{:else}
			<h2><HighlightedText text={result.title} {query} /></h2>
		{/if}
	</header>

	{#if result.summary}
		<p class="summary"><HighlightedText text={result.summary} {query} /></p>
	{/if}

	<dl>
		{#if result.external_id}
			<div>
				<dt>External ID</dt>
				<dd><code><HighlightedText text={result.external_id} {query} /></code></dd>
			</div>
		{/if}
		{#if result.indicator_type}
			<div>
				<dt>Indicator type</dt>
				<dd>{result.indicator_type}</dd>
			</div>
		{/if}
		{#if result.indicator_value}
			<div>
				<dt>Indicator value</dt>
				<dd><code><HighlightedText text={result.indicator_value} {query} /></code></dd>
			</div>
		{/if}
		{#if result.severity}
			<div>
				<dt>Severity</dt>
				<dd class:critical-severity={result.severity.toLowerCase() === 'critical'}>
					{result.severity}{result.cvss_score !== null ? ` / CVSS ${result.cvss_score}` : ''}
				</dd>
			</div>
		{/if}
		{#if result.source_id}
			<div>
				<dt>Source reference</dt>
				<dd><code>{result.source_id}</code></dd>
			</div>
		{/if}
		{#if result.observed_at}
			<div>
				<dt>Observed</dt>
				<dd><UtcDate value={result.observed_at} /></dd>
			</div>
		{/if}
		{#if result.origin}
			<div>
				<dt>Origin</dt>
				<dd>{result.origin}</dd>
			</div>
		{/if}
	</dl>

	{#if result.related_actors.length}
		<section class="related" aria-label="Related threat actors">
			<h3>Related threat actors</h3>
			{#each result.related_actors as actor (actor.id)}
				<div class="actor-context">
					<a href={relatedActorHref(actor.id)}
						><HighlightedText text={actor.canonical_name} {query} /></a
					>
					{#if actor.description}
						<p><HighlightedText text={actor.description} {query} /></p>
					{/if}
					{#if actor.latest_observed_at}
						<small>Latest published observation <UtcDate value={actor.latest_observed_at} /></small>
					{/if}
				</div>
			{/each}
			{#if result.related_actors_truncated}<small>Additional actor links are available.</small>{/if}
		</section>
	{/if}

	<footer>
		{#if actorHref}
			<a href={actorHref}>View actor profile</a>
		{:else if relatedActorContextHref}
			<a href={relatedActorContextHref}>View related actor</a>
		{:else}
			<span class="self-contained">Search result summary</span>
		{/if}
	</footer>
</article>

<style>
	article {
		display: grid;
		gap: var(--space-4);
		padding: var(--space-6) var(--space-5);
		border-bottom: var(--border-width) solid var(--color-border);
		background: transparent;
		transition: background var(--motion-fast) var(--easing-standard);
	}

	article:hover {
		background: var(--color-threat-faint);
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
	dt {
		font-size: var(--font-size-sm);
	}

	.entity {
		color: var(--color-primary);
		font-weight: 700;
	}

	.entity.threat-entity,
	.critical-severity {
		color: var(--color-threat);
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

	.related {
		display: grid;
		gap: var(--space-3);
		padding-left: var(--space-4);
		border-left: 0.1875rem solid var(--color-secondary);
	}
	.related h3,
	.related small {
		font-size: var(--font-size-sm);
	}
	.related h3 {
		margin: 0;
		color: var(--color-secondary);
	}
	.actor-context {
		display: grid;
		gap: var(--space-1);
	}
	.actor-context a {
		width: fit-content;
		color: var(--color-ink);
		font-family: var(--font-display);
		font-size: var(--font-size-lg);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-heading);
		text-underline-offset: var(--space-1);
	}
	.actor-context p {
		margin: 0;
		color: var(--color-ink-muted);
	}
	.related small {
		color: var(--color-ink-subtle);
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
		justify-content: flex-end;
		gap: var(--space-3);
		color: var(--color-ink-subtle);
	}

	footer a {
		color: var(--color-primary);
		font-weight: 700;
		text-underline-offset: var(--space-2);
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
