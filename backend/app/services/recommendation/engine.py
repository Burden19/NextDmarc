from app.services.recommendation.models import RecommendationItem, RecommendationResult


class RecommendationEngine:
    def analyze(
        self,
        *,
        tenant_id: str,
        report_db_id: str,
        total_records: int,
        spf_pass_count: int,
        dkim_pass_count: int,
        dmarc_pass_count: int,
        conformance_rate: float,
    ) -> RecommendationResult:
        safe_total = max(1, total_records)
        spf_rate = max(0.0, min(1.0, spf_pass_count / safe_total))
        dkim_rate = max(0.0, min(1.0, dkim_pass_count / safe_total))
        dmarc_rate = max(0.0, min(1.0, dmarc_pass_count / safe_total))
        normalized_conformance = max(0.0, min(1.0, conformance_rate))

        items: list[RecommendationItem] = []

        if spf_rate < 0.95:
            items.append(
                RecommendationItem(
                    code="spf_alignment_hardening",
                    title="Improve SPF Coverage",
                    detail=(
                        "SPF pass rate is below 95 percent; review includes and sender inventory."
                    ),
                    severity="medium",
                )
            )

        if dkim_rate < 0.95:
            items.append(
                RecommendationItem(
                    code="dkim_key_rotation_and_alignment",
                    title="Strengthen DKIM Alignment",
                    detail=(
                        "DKIM pass rate is below 95 percent; validate selectors "
                        "and signer consistency."
                    ),
                    severity="medium",
                )
            )

        if dmarc_rate < 0.9 or normalized_conformance < 0.9:
            items.append(
                RecommendationItem(
                    code="dmarc_policy_progression",
                    title="Advance DMARC Enforcement",
                    detail=(
                        "Conformance is below target; move policy from "
                        "monitoring to stricter enforcement in stages."
                    ),
                    severity="high",
                )
            )

        maturity_score = self._maturity_score(
            spf_rate=spf_rate,
            dkim_rate=dkim_rate,
            dmarc_rate=dmarc_rate,
            conformance_rate=normalized_conformance,
        )

        return RecommendationResult(
            tenant_id=tenant_id,
            report_db_id=report_db_id,
            maturity_score=maturity_score,
            maturity_level=self._maturity_level(maturity_score),
            items=items,
        )

    def _maturity_score(
        self,
        *,
        spf_rate: float,
        dkim_rate: float,
        dmarc_rate: float,
        conformance_rate: float,
    ) -> int:
        score = spf_rate * 25.0 + dkim_rate * 25.0 + dmarc_rate * 25.0 + conformance_rate * 25.0
        return int(round(max(0.0, min(100.0, score))))

    def _maturity_level(self, score: int) -> str:
        if score >= 85:
            return "advanced"
        if score >= 70:
            return "managed"
        if score >= 50:
            return "developing"
        return "foundational"
