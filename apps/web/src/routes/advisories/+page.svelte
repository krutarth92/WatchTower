<script lang="ts">
	import type { PageProps } from './$types';
	import StatePanel from '#lib/components/StatePanel.svelte';
	import UtcDate from '#lib/components/UtcDate.svelte';

	let { data }: PageProps = $props();
</script>

<svelte:head>
	<title>Living intelligence | WATCHTOWER</title>
	<meta
		name="description"
		content="Read published WATCHTOWER advisories and their revision history."
	/>
</svelte:head>

<section class="intelligence-page">
	<header>
		<p>LIVING INTELLIGENCE / PUBLISHED ADVISORIES</p>
		<h1>Intelligence</h1>
		<span>Reviewed analysis that retains its sources, revisions and timestamped changes.</span>
	</header>

	{#if data.view === 'unavailable'}
		<StatePanel
			state="error"
			title="Intelligence feed unavailable"
			message={data.error?.message ?? 'Published advisories are unavailable.'}
			requestId={data.error?.requestId ?? undefined}
		/>
	{:else if data.view === 'empty'}
		<StatePanel
			state="empty"
			title="No advisories have been published"
			message="Draft work remains outside the public interface."
		/>
	{:else}
		<ol>
			{#each data.response?.data ?? [] as advisory, index (advisory.id)}
				<li>
					<div class="sequence">{String(index + 1).padStart(2, '0')}</div>
					<div class="article">
						<div class="article-meta">
							<span>PUBLISHED <UtcDate value={advisory.published_at} /></span>
							<span>REVISION {advisory.published_revision}</span>
							{#if advisory.latest_update_at}<span
									>UPDATED <UtcDate value={advisory.latest_update_at} /></span
								>{/if}
						</div>
						<a href={`/advisories/${advisory.slug}`}>{advisory.title}</a>
						<p>{advisory.summary}</p>
					</div>
					<span class="open" aria-hidden="true">→</span>
				</li>
			{/each}
		</ol>
	{/if}
</section>

<style>
	.intelligence-page {
		max-width: 72rem;
		margin: 0 auto;
		padding: var(--space-8) var(--space-5);
	}

	.intelligence-page > header {
		max-width: 54rem;
		padding-bottom: var(--space-7);
	}

	header p,
	.sequence,
	.article-meta {
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

	header > span,
	.article p {
		color: var(--color-ink-muted);
	}

	ol {
		margin: 0;
		padding: 0;
		border-top: var(--border-width) solid var(--color-border-strong);
		list-style: none;
	}

	li {
		display: grid;
		grid-template-columns: 2.5rem minmax(0, 1fr) auto;
		gap: var(--space-4);
		align-items: center;
		padding: var(--space-6) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.sequence {
		align-self: start;
		color: var(--color-secondary);
	}

	.article-meta {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-4);
		margin-bottom: var(--space-2);
		color: var(--color-ink-subtle);
	}

	.article > a {
		color: var(--color-ink);
		font-size: clamp(1.35rem, 3vw, 2rem);
		font-weight: 780;
		line-height: 1.2;
		text-decoration: none;
	}

	.article > a:hover,
	.open {
		color: var(--color-primary);
	}

	.article p {
		max-width: 54rem;
		margin: var(--space-3) 0 0;
	}

	.open {
		font-size: var(--font-size-lg);
	}

	@media (max-width: 38rem) {
		li {
			grid-template-columns: minmax(0, 1fr) auto;
		}

		.sequence {
			display: none;
		}
	}
</style>
