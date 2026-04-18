export interface WikimediaRecentChange {
	id?: number;
	type?: string;
	title?: string;
	timestamp?: number;
	user?: string;
	bot?: boolean;
	meta?: {
		uri?: string;
		request_id?: string;
		id?: string;
		dt?: string;
		domain?: string;
		stream?: string;
	};
	wiki?: string;
}
