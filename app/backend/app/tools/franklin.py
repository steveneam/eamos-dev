from __future__ import annotations

import httpx

from app.tools.base import FixtureBackedTool, ToolResult


def _extract_cdna(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


class FranklinTool(FixtureBackedTool):
    source = 'franklin'
    fixture_name = 'franklin_fixtures.json'

    def get_evidence(self, variant=None) -> ToolResult:
        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            return ToolResult(source=self.source, status='fixture', **fixture)
        try:
            token = self._get_bearer_token()
            if not token:
                fixture = self.load_fixture()
                return ToolResult(
                    source=self.source,
                    status='fallback',
                    request_identity=fixture['request_identity'],
                    summary=fixture['summary'],
                    warnings=['franklin_auth_unavailable'],
                    raw=None,
                )
            return self._fetch_live(token, variant)
        except Exception as exc:
            fixture = self.load_fixture()
            return ToolResult(source=self.source, status='fallback', warnings=[f'live_fetch_failed:{type(exc).__name__}'], **fixture)

    def _get_bearer_token(self) -> str | None:
        if self.settings.franklin_api_token:
            return self.settings.franklin_api_token

        if not self.settings.franklin_email or not self.settings.franklin_password:
            return None

        response = httpx.get(
            f'{self.settings.franklin_base_url}/v1/auth/login',
            params={'email': self.settings.franklin_email},
            headers={
                # Franklin login expects the raw Franklin password in Authorization.
                'Authorization': self.settings.franklin_password,
                'Accept': 'application/json',
            },
            timeout=10.0,
        )
        response.raise_for_status()
        token = response.json().get('token')
        if not token:
            raise RuntimeError('Franklin login response did not include a token.')
        return token

    def _fetch_live(self, token: str, variant) -> ToolResult:
        gene = variant.gene
        cdna = _extract_cdna(variant.transcript_hgvs)
        search_text = f"{gene}:{cdna}" if cdna else gene

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        parse_response = httpx.post(
            f'{self.settings.franklin_parse_base_url}/api/parse_search',
            json={'search_text_input': search_text},
            headers=headers,
            timeout=10.0,
        )
        parse_response.raise_for_status()
        parse_payload = parse_response.json()
        search_response = httpx.get(
            f'{self.settings.franklin_base_url}/v2/search/snp/',
            params={'search_text': search_text},
            headers=headers,
            timeout=10.0,
        )
        search_response.raise_for_status()
        search_payload = search_response.json()
        variant_block = parse_payload.get('best_variant_option') or parse_payload
        transcript = (
            variant_block.get('canonical_transcript')
            or variant_block.get('transcript')
            or 'N/A'
        )
        summary = {
            'search_text': search_text,
            'transcript': transcript,
            'functional_data': search_payload.get('classification', {}).get('acmg_classification', 'Unavailable')
            if isinstance(search_payload, dict)
            else 'Unavailable',
            'population_data': search_payload.get('annotations', {}).get('frequencies', {}).get('aggregated_frequency', 'Unavailable')
            if isinstance(search_payload, dict)
            else 'Unavailable',
            'in_silico_prediction': search_payload.get('annotations', {}).get('predictions', {}).get('aggregated_predictions', 'Unavailable')
            if isinstance(search_payload, dict)
            else 'Unavailable',
        }
        return ToolResult(
            source=self.source,
            status='live',
            request_identity={'search_text': search_text},
            summary=summary,
            raw={'parse_payload': parse_payload, 'search_payload': search_payload},
        )
