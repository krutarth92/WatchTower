<script lang="ts">
	import type { PageProps } from './$types';
	import StatePanel from '#lib/components/StatePanel.svelte';
	import UtcDate from '#lib/components/UtcDate.svelte';

	let { data }: PageProps = $props();
	const actors = $derived(data.discovery?.recent ?? []);
</script>

<svelte:head>
	<title>Actor evolution | WATCHTOWER</title>
	<meta
		name="description"
		content="Open published actor histories and follow behavior changes over time."
	/>
</svelte:head>

<section class="evolution-page">
	<header>
		<p>BEHAVIOR OVER TIME / PUBLISHED EVENTS</p>
		<h1>Actor evolution</h1>
		<span>Start with a recently observed actor, then follow its ordered timeline and evidence.</span
		>
	</header>

	<div class="boundary-note">
		<strong>Why there is no aggregate chart</strong>
		<p>
			Actor timelines are cursor-paginated. WATCHTOWER does not present one page as a complete
			historical series.
		</p>
	</div>

	{#if data.error}
		<StatePanel
			state="error"
			title="Evolution index unavailable"
			message={data.error.message}
			requestId={data.error.requestId ?? undefined}
		/>
	{:else if actors.length}
		<ol>
			{#each actors as actor, index (actor.id)}
				<li>
					<span class="index">{String(index + 1).padStart(2, '0')}</span>
					<div>
						<a href={`/actors/${actor.id}?fromSearch=%2Fevolution`}>{actor.canonical_name}</a>
						<p>
							{actor.description ?? 'Published actor profile with an evidence-backed timeline.'}
						</p>
						<small>
							{actor.published_observation_count} events
							{#if actor.latest_observed_at}
								· latest <UtcDate value={actor.latest_observed_at} />{/if}
						</small>
					</div>
					<span class="action">Open timeline →</span>
				</li>
			{/each}
		</ol>
	{:else}
		<StatePanel
			state="empty"
			title="No actor histories are published"
			message="This page will populate when published actor observations are available."
		/>
	{/if}
</section>

<style>
	.evolution-page {
		max-width: 70rem;
		margin: 0 auto;
		padding: var(--space-8) var(--space-5);
	}

	.evolution-page > header {
		max-width: 50rem;
		padding-bottom: var(--space-6);
	}

	header p,
	.index,
	small {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	header p {
		margin: 0;
		color: var(--color-primary);
		font-weight: 700;
	}

	h1 {
		margin: var(--space-2) 0;
		font-size: var(--font-size-xl);
	}

	header span,
	li p,
	small,
	.boundary-note p {
		color: var(--color-ink-muted);
	}

	.boundary-note {
		display: grid;
		grid-template-columns: minmax(12rem, 0.5fr) minmax(0, 1.5fr);
		gap: var(--space-5);
		padding: var(--space-4) 0;
		border-block: var(--border-width) solid var(--color-border);
	}

	.boundary-note p {
		margin: 0;
	}

	ol {
		margin: var(--space-6) 0 0;
		padding: 0;
		list-style: none;
	}

	li {
		display: grid;
		grid-template-columns: 2.5rem minmax(0, 1fr) auto;
		gap: var(--space-4);
		align-items: center;
		padding: var(--space-5) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.index {
		color: var(--color-secondary);
	}

	li a {
		color: var(--color-ink);
		font-size: var(--font-size-lg);
		font-weight: 750;
		text-decoration: none;
	}

	li a:hover,
	.action {
		color: var(--color-primary);
	}

	li p {
		margin: var(--space-1) 0;
	}

	.action {
		font-size: var(--font-size-sm);
		font-weight: 700;
	}

	@media (max-width: 40rem) {
		.boundary-note,
		li {
			grid-template-columns: 1fr;
		}

		.index {
			display: none;
		}
	}
</style>
