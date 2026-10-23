<script lang="ts">
	import type { TimelineEvent } from '#lib/api/contracts.ts';
	import ConfidenceMeter from './ConfidenceMeter.svelte';
	import EvidenceDisclosure from './EvidenceDisclosure.svelte';
	import SourceMetadata from './SourceMetadata.svelte';
	import StatusChip from './StatusChip.svelte';
	import UtcDate from './UtcDate.svelte';

	let { event }: { event: TimelineEvent } = $props();
</script>

<article>
	<div class="timeline-node" aria-hidden="true"></div>
	<header>
		<div class="event-labels">
			<StatusChip label={event.intelligence_type.toUpperCase()} tone={event.intelligence_type} />
			<span class="origin">ORIGIN / {event.origin.toUpperCase()}</span>
			<span class="event-type">{event.event_type.toUpperCase()}</span>
		</div>
		<h3>{event.title}</h3>
		<div class="observed"><span>OBSERVED</span><UtcDate value={event.observed_at} /></div>
	</header>

	<p class="summary">{event.summary}</p>

	<div class="event-grid">
		<div class="seen-window">
			<div>
				<span>FIRST SEEN</span>
				{#if event.first_seen}<UtcDate value={event.first_seen} />{:else}<strong
						>Not established</strong
					>{/if}
			</div>
			<div>
				<span>LAST SEEN</span>
				{#if event.last_seen}<UtcDate value={event.last_seen} />{:else}<strong
						>Not established</strong
					>{/if}
			</div>
			<p>Missing bounds remain unknown; they are not inferred from the observation date.</p>
		</div>
		<ConfidenceMeter value={event.confidence} />
	</div>

	<SourceMetadata source={event.source} nativeId={event.source_native_id} />

	<div class="associations">
		<div>
			<h4>Behaviors</h4>
			{#if event.behaviors.length}
				<ul>
					{#each event.behaviors as behavior (behavior.id)}
						<li title={behavior.description ?? undefined}>{behavior.name}</li>
					{/each}
				</ul>
			{:else}<p>No published behavior labels.</p>{/if}
			{#if event.behaviors_truncated}<p class="truncated">
					Additional behaviors are available through the API.
				</p>{/if}
		</div>
		<div>
			<h4>Techniques</h4>
			{#if event.techniques.length}
				<ul>
					{#each event.techniques as technique (technique.id)}
						<li title={technique.description ?? undefined}>
							<code>{technique.external_id}</code>
							{technique.name}
						</li>
					{/each}
				</ul>
			{:else}<p>No published technique labels.</p>{/if}
			{#if event.techniques_truncated}<p class="truncated">
					Additional techniques are available through the API.
				</p>{/if}
		</div>
	</div>

	<section class="event-evidence" aria-label={`Evidence for ${event.title}`}>
		<h4>Evidence</h4>
		{#if event.evidence.length}
			<div class="evidence-list">
				{#each event.evidence as evidence (evidence.id)}
					<EvidenceDisclosure {evidence} />
				{/each}
			</div>
		{:else}<p>No published evidence references.</p>{/if}
		{#if event.evidence_truncated}<p class="truncated">
				Additional evidence is available through the API.
			</p>{/if}
	</section>
</article>

<style>
	article {
		position: relative;
		display: grid;
		gap: var(--space-4);
		padding: 0 0 var(--space-7) var(--space-6);
		border-left: var(--border-width) solid var(--color-border-strong);
	}

	.timeline-node {
		position: absolute;
		top: var(--space-1);
		left: -0.4rem;
		width: 0.75rem;
		height: 0.75rem;
		border: var(--border-width) solid var(--color-primary);
		border-radius: 50%;
		background: var(--color-canvas);
		box-shadow: 0 0 var(--space-3) var(--color-primary-glow);
	}

	header {
		display: grid;
		gap: var(--space-2);
		padding-bottom: var(--space-3);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.event-labels,
	.observed,
	.seen-window,
	.associations ul {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
	}

	.event-labels {
		gap: var(--space-2) var(--space-3);
	}

	.origin,
	.event-type,
	.observed > span,
	.seen-window span,
	h4,
	.truncated {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	.origin {
		color: var(--color-secondary);
	}

	.event-type,
	.observed > span,
	.seen-window span {
		color: var(--color-ink-subtle);
	}

	h3 {
		margin: 0;
		font-size: clamp(1.25rem, 3vw, 1.75rem);
	}

	.observed {
		gap: var(--space-3);
		color: var(--color-ink-muted);
	}

	.summary,
	.associations p,
	.event-evidence > p {
		margin: 0;
		color: var(--color-ink-muted);
	}

	.event-grid {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(12rem, 0.6fr);
		gap: var(--space-6);
	}

	.seen-window {
		gap: var(--space-4) var(--space-6);
	}

	.seen-window > div {
		display: grid;
		gap: var(--space-1);
	}

	.seen-window strong {
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
		font-weight: 500;
	}

	.seen-window p {
		flex-basis: 100%;
		margin: 0;
		color: var(--color-ink-subtle);
		font-size: var(--font-size-xs);
	}

	.associations {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--space-5);
	}

	h4 {
		margin: 0 0 var(--space-2);
		color: var(--color-primary);
	}

	.associations ul {
		gap: var(--space-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.associations li {
		padding: var(--space-1) var(--space-2);
		border-left: 0.125rem solid var(--color-secondary);
		background: var(--color-secondary-faint);
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
	}

	.associations code {
		color: var(--color-secondary);
	}

	.event-evidence {
		padding-top: var(--space-3);
		border-top: var(--border-width) solid var(--color-border);
	}

	.evidence-list {
		display: grid;
		gap: var(--space-2);
	}

	.truncated {
		margin-top: var(--space-2) !important;
		color: var(--color-assessed) !important;
	}

	@media (max-width: 44rem) {
		article {
			padding-left: var(--space-4);
		}

		.event-grid,
		.associations {
			grid-template-columns: 1fr;
		}
	}
</style>
