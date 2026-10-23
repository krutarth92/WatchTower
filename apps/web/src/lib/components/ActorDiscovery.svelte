<script lang="ts">
	import type { ActorDiscoveryResponse } from '#lib/api/contracts.ts';
	import UtcDate from './UtcDate.svelte';

	let { discovery }: { discovery: ActorDiscoveryResponse | null } = $props();

	const lanes = $derived([
		{
			key: 'recent',
			label: 'RECENTLY OBSERVED',
			description: 'Actors with the latest published observations',
			actors: discovery?.recent ?? []
		},
		{
			key: 'popular',
			label: 'ACTIVE IN THE INDEX',
			description: 'Actors with the strongest published relationship activity',
			actors: discovery?.popular ?? []
		}
	]);
</script>

<section class="discovery" aria-labelledby="discovery-title">
	<header>
		<p>LIVE ACTOR DISCOVERY / PUBLISHED DATA</p>
		<h2 id="discovery-title">Threat actors worth investigating</h2>
		<span>Updated from the intelligence index as published records are ingested.</span>
	</header>

	{#if discovery && (discovery.recent.length || discovery.popular.length)}
		<div class="lanes">
			{#each lanes as lane (lane.key)}
				<section aria-labelledby={`${lane.key}-actors`}>
					<div class="lane-heading">
						<div>
							<h3 id={`${lane.key}-actors`}>{lane.label}</h3>
							<p>{lane.description}</p>
						</div>
						<span>{String(lane.actors.length).padStart(2, '0')}</span>
					</div>
					<ol>
						{#each lane.actors as actor, index (actor.id)}
							<li>
								<span class="rank">{String(index + 1).padStart(2, '0')}</span>
								<div>
									<a href={`/actors/${actor.id}?fromSearch=%2Fsearch`}>{actor.canonical_name}</a>
									<p>
										{actor.description ||
											'Published actor profile with linked intelligence context.'}
									</p>
									<small>
										{actor.published_observation_count} observations · {actor.published_alias_count}
										aliases
										{#if actor.latest_observed_at}
											· latest <UtcDate value={actor.latest_observed_at} />
										{/if}
									</small>
								</div>
							</li>
						{/each}
					</ol>
				</section>
			{/each}
		</div>
	{:else}
		<p class="unavailable">
			Actor discovery will populate when published actor intelligence is available.
		</p>
	{/if}
</section>

<style>
	.discovery {
		padding-top: var(--space-5);
		border-top: var(--border-width) solid var(--color-border-strong);
	}

	header {
		max-width: 50rem;
		padding-bottom: var(--space-5);
	}
	header p,
	h3,
	.rank,
	small,
	.lane-heading > span {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}
	header p,
	h3 {
		margin: 0;
		color: var(--color-primary);
		font-weight: 700;
	}
	header h2 {
		margin: var(--space-2) 0;
		font-size: clamp(1.5rem, 4vw, 2.35rem);
	}
	header span,
	.lane-heading p,
	li p,
	.unavailable {
		color: var(--color-ink-muted);
	}

	.lanes {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--space-7);
	}

	.lane-heading {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-4);
		padding-bottom: var(--space-3);
		border-bottom: var(--border-width) solid var(--color-primary);
	}
	.lane-heading p {
		margin: var(--space-1) 0 0;
		font-size: var(--font-size-sm);
	}
	.lane-heading > span {
		color: var(--color-secondary);
	}

	ol {
		margin: 0;
		padding: 0;
		list-style: none;
	}
	li {
		display: grid;
		grid-template-columns: 2rem minmax(0, 1fr);
		gap: var(--space-3);
		padding: var(--space-4) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}
	.rank,
	small {
		color: var(--color-ink-subtle);
	}
	li a {
		color: var(--color-ink);
		font-size: var(--font-size-lg);
		font-weight: 750;
		text-decoration-color: var(--color-border-strong);
		text-underline-offset: var(--space-1);
	}
	li a:hover {
		color: var(--color-primary);
	}
	li p {
		display: -webkit-box;
		overflow: hidden;
		margin: var(--space-2) 0;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 2;
		line-clamp: 2;
	}

	@media (max-width: 48rem) {
		.lanes {
			grid-template-columns: 1fr;
			gap: var(--space-6);
		}
	}
</style>
