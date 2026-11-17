<script lang="ts">
	import type { AdvisoryResponse, UpdateRead } from '#lib/api/contracts.ts';
	import { advisorySectionLabels } from '#lib/advisories/presentation.ts';
	import StatePanel from './StatePanel.svelte';
	import StatusChip from './StatusChip.svelte';
	import UtcDate from './UtcDate.svelte';

	let {
		response,
		initialUpdates,
		updatesUnavailable = false,
		updatesRequestId = null,
		archivedVersion = null
	}: {
		response: AdvisoryResponse;
		initialUpdates: UpdateRead[];
		updatesUnavailable?: boolean;
		updatesRequestId?: string | null;
		archivedVersion?: number | null;
	} = $props();

	const advisory = $derived(response.data);
	const revision = $derived(advisory.revision);
	const isArchived = $derived(archivedVersion !== null);
	let updates = $state<UpdateRead[]>([]);
	let mayHaveMore = $state(false);
	let loadingMore = $state(false);
	let loadError = $state<string | null>(null);

	$effect(() => {
		updates = [...initialUpdates];
		mayHaveMore = initialUpdates.length === 25;
		loadError = null;
	});

	async function loadMoreUpdates() {
		if (!mayHaveMore || loadingMore || !updates.length) return;
		loadingMore = true;
		loadError = null;
		try {
			const response = await fetch(`/advisories/${advisory.slug}/updates`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
				body: JSON.stringify({ afterSequence: updates.at(-1)?.sequence })
			});
			const body = (await response.json()) as
				| { data: UpdateRead[] }
				| { error: { message: string } };
			if (!response.ok || 'error' in body) {
				loadError = 'error' in body ? body.error.message : 'More updates could not be loaded.';
				return;
			}
			updates = [...updates, ...body.data];
			mayHaveMore = body.data.length === 25;
		} catch {
			loadError = 'More updates could not be loaded.';
		} finally {
			loadingMore = false;
		}
	}
</script>

<article class="advisory-detail">
	<nav class="breadcrumbs" aria-label="Breadcrumb">
		<a href="/">Home</a><span aria-hidden="true">/</span><a href="/advisories">Intelligence</a><span
			aria-hidden="true">/</span
		><span>{revision.title}</span>
	</nav>

	{#if isArchived}
		<div class="archive-banner">
			<strong>Archived published revision v{archivedVersion}</strong>
			<span
				>This durable snapshot is read-only. <a href={`/advisories/${advisory.slug}`}
					>Open current revision</a
				>.</span
			>
		</div>
	{/if}

	<header class="article-header">
		<div class="article-kicker">
			<span>LIVING INTELLIGENCE</span><span>REVISION {revision.version}</span>
		</div>
		<h1>{revision.title}</h1>
		<p>{revision.summary}</p>
		<div class="publication-line">
			<span
				>Published {#if revision.published_at}<UtcDate
						value={revision.published_at}
					/>{:else}—{/if}</span
			>
			<span>Prepared by {revision.created_by}</span>
			{#if revision.published_by}<span>Published by {revision.published_by}</span>{/if}
		</div>
	</header>

	<div class="article-grid">
		<div class="article-body">
			{#each revision.sections as section (section.position)}
				<section class="article-section" aria-labelledby={`section-${section.position}`}>
					<div class="section-index">{String(section.position + 1).padStart(2, '0')}</div>
					<div>
						<StatusChip
							label={section.intelligence_type.toUpperCase()}
							tone={section.intelligence_type}
						/>
						<h2 id={`section-${section.position}`}>
							{advisorySectionLabels[section.section_type]}
						</h2>
						<p>{section.content}</p>
					</div>
				</section>
			{/each}

			{#if revision.evidence.length}
				<section class="evidence-list" aria-labelledby="evidence-title">
					<p class="section-label">SUPPORTING EVIDENCE</p>
					<h2 id="evidence-title">Sources and citations</h2>
					<ol>
						{#each revision.evidence as evidence, index (evidence.id)}
							<li>
								<span>{String(index + 1).padStart(2, '0')}</span>
								<div>
									<strong>{evidence.citation}</strong>{#if evidence.excerpt}<p>
											{evidence.excerpt}
										</p>{/if}
								</div>
							</li>
						{/each}
					</ol>
					<p class="evidence-boundary">
						This advisory contract provides citations and excerpts. It does not provide a public
						source locator, so WATCHTOWER does not fabricate a link.
					</p>
				</section>
			{/if}
		</div>

		<aside class="context-rail" aria-label="Advisory context">
			<section>
				<p>LINKED ACTORS</p>
				{#if revision.actors.length}
					<ul>
						{#each revision.actors as actor (actor.id)}<li>
								<a
									href={`/actors/${actor.id}?fromSearch=${encodeURIComponent(`/advisories/${advisory.slug}`)}`}
									>{actor.canonical_name}</a
								>
							</li>{/each}
					</ul>
				{:else}<span>None linked</span>{/if}
			</section>
			<section>
				<p>TECHNIQUES</p>
				{#if revision.techniques.length}
					<ul>
						{#each revision.techniques as technique (technique.id)}<li>
								<strong>{technique.external_id}</strong>
								{technique.name}
							</li>{/each}
					</ul>
				{:else}<span>None linked</span>{/if}
			</section>
			<section>
				<p>CAMPAIGNS</p>
				{#if revision.campaigns.length}
					<ul>
						{#each revision.campaigns as campaign (campaign.id)}<li>{campaign.name}</li>{/each}
					</ul>
				{:else}<span>None linked</span>{/if}
			</section>
			<section>
				<p>REVISION HISTORY</p>
				<ul>
					<li>
						<a href={`/advisories/${advisory.slug}`}>Current · v{advisory.published_revision}</a>
					</li>
					{#if revision.version > 1}<li>
							<a href={`/advisories/${advisory.slug}/revisions/${revision.version - 1}`}
								>Previous · v{revision.version - 1}</a
							>
						</li>{/if}
				</ul>
			</section>
		</aside>
	</div>

	{#if !isArchived}
		<section class="updates" aria-labelledby="updates-title">
			<header>
				<p class="section-label">ORDERED CHANGE LOG</p>
				<h2 id="updates-title">Advisory updates</h2>
			</header>
			{#if updatesUnavailable}
				<StatePanel
					state="error"
					title="Updates unavailable"
					message="The advisory remains available, but its update stream could not be loaded."
					requestId={updatesRequestId ?? undefined}
				/>
			{:else if updates.length}
				<ol>
					{#each updates as update (update.sequence)}
						<li>
							<div class="update-sequence">UPDATE {String(update.sequence).padStart(2, '0')}</div>
							<div>
								<StatusChip
									label={update.intelligence_type.toUpperCase()}
									tone={update.intelligence_type}
								/>
								<h3>{update.title}</h3>
								<p>{update.summary}</p>
								<small
									><UtcDate value={update.occurred_at} /> · applies to revision {update.revision_version}</small
								>
							</div>
						</li>
					{/each}
				</ol>
				{#if loadError}<p class="load-error" role="alert">{loadError}</p>{/if}
				{#if mayHaveMore}<button type="button" onclick={loadMoreUpdates} disabled={loadingMore}
						>{loadingMore ? 'Loading updates…' : 'Load more updates'}</button
					>{/if}
			{:else}
				<StatePanel
					state="empty"
					title="No timestamped updates"
					message="The current published revision has no additional update entries."
				/>
			{/if}
		</section>
	{/if}
</article>

<style>
	.advisory-detail {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: var(--space-5);
	}

	.breadcrumbs {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		margin: var(--space-3) 0 var(--space-6);
		color: var(--color-ink-subtle);
		font-size: var(--font-size-sm);
	}

	.breadcrumbs a,
	.archive-banner a,
	.context-rail a {
		color: var(--color-primary);
		text-decoration: none;
	}

	.archive-banner {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: var(--space-4);
		padding: var(--space-3) 0;
		border-block: var(--border-width) solid var(--color-assessed);
		color: var(--color-assessed);
	}

	.archive-banner span {
		color: var(--color-ink-muted);
	}

	.article-header {
		max-width: 70rem;
		padding: var(--space-7) 0;
	}

	.article-kicker,
	.publication-line,
	.section-label,
	.section-index,
	.context-rail section > p,
	.update-sequence,
	small {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	.article-kicker,
	.publication-line {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-5);
		color: var(--color-primary);
	}

	h1 {
		max-width: 24ch;
		margin: var(--space-3) 0;
		font-size: clamp(2.25rem, 6vw, 4.8rem);
		letter-spacing: -0.045em;
		line-height: 1;
	}

	.article-header > p {
		max-width: 54rem;
		color: var(--color-ink-muted);
		font-size: var(--font-size-lg);
	}

	.publication-line {
		margin-top: var(--space-5);
		color: var(--color-ink-subtle);
	}

	.article-grid {
		display: grid;
		grid-template-columns: minmax(0, 1.5fr) minmax(17rem, 0.5fr);
		gap: var(--space-8);
		align-items: start;
	}

	.article-section {
		display: grid;
		grid-template-columns: 2.5rem minmax(0, 1fr);
		gap: var(--space-4);
		padding: var(--space-6) 0;
		border-top: var(--border-width) solid var(--color-border);
	}

	.section-index,
	.update-sequence {
		color: var(--color-secondary);
	}

	.article-section h2,
	.evidence-list h2,
	.updates h2 {
		margin: var(--space-3) 0;
		font-size: clamp(1.55rem, 3vw, 2.4rem);
	}

	.article-section p,
	.evidence-list li p,
	.updates li p {
		margin: 0;
		color: var(--color-ink-muted);
		white-space: pre-wrap;
	}

	.context-rail {
		position: sticky;
		top: calc(var(--header-height) + var(--space-5));
	}

	.context-rail section {
		padding: var(--space-4) 0;
		border-top: var(--border-width) solid var(--color-border);
	}

	.context-rail section > p,
	.section-label {
		margin: 0 0 var(--space-3);
		color: var(--color-primary);
		font-weight: 700;
	}

	.context-rail ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.context-rail li {
		padding: var(--space-2) 0;
		color: var(--color-ink-muted);
	}

	.evidence-list,
	.updates {
		padding: var(--space-7) 0;
		border-top: var(--border-width) solid var(--color-border-strong);
	}

	.evidence-list ol,
	.updates ol {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.evidence-list li,
	.updates li {
		display: grid;
		grid-template-columns: 7rem minmax(0, 1fr);
		gap: var(--space-4);
		padding: var(--space-4) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.evidence-list li > span {
		color: var(--color-secondary);
		font-family: var(--font-mono);
	}

	.evidence-list li p,
	.updates li p {
		margin-top: var(--space-2);
	}

	.evidence-boundary,
	.load-error {
		color: var(--color-ink-subtle);
		font-size: var(--font-size-sm);
	}

	.updates {
		max-width: 70rem;
		margin-top: var(--space-7);
	}

	.updates h3 {
		margin: var(--space-3) 0;
		font-size: var(--font-size-lg);
	}

	.updates small {
		display: block;
		margin-top: var(--space-2);
		color: var(--color-ink-subtle);
	}

	.updates button {
		min-height: 2.75rem;
		margin-top: var(--space-5);
		padding: 0 var(--space-4);
		border: var(--border-width) solid var(--color-primary);
		background: transparent;
		color: var(--color-primary);
		font-weight: 700;
		cursor: pointer;
	}

	@media (max-width: 58rem) {
		.article-grid {
			grid-template-columns: 1fr;
			gap: var(--space-6);
		}

		.context-rail {
			position: static;
		}
	}

	@media (max-width: 40rem) {
		.archive-banner,
		.article-section,
		.evidence-list li,
		.updates li {
			grid-template-columns: 1fr;
		}

		.section-index {
			display: none;
		}
	}
</style>
