import type { AdvisorySectionType } from '#lib/api/contracts.ts';

export const advisorySectionLabels: Readonly<Record<AdvisorySectionType, string>> = {
	what_happened: 'What happened',
	actor_context: 'Actor context',
	technical_analysis: 'Technical analysis',
	detection: 'Detection',
	response: 'Response',
	mitigation: 'Mitigation',
	watchtower_assessment: 'WATCHTOWER assessment'
};
