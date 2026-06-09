from __future__ import annotations

from dataclasses import asdict

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.behavior.models import BehaviorSession
from apps.ml_engine.behavior_features import BehaviorFeatureExtractor
from apps.ml_engine.models import EvaluationDataset, EvaluationSubject


class Command(BaseCommand):
    help = 'Import real users from enrollment sessions as EvaluationSubjects.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usernames',
            nargs='+',
            required=True,
            help='Django usernames to import (e.g. --usernames user4 user5)',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        extractor = BehaviorFeatureExtractor()

        dataset, created = EvaluationDataset.objects.update_or_create(
            name='our_collection',
            defaults={
                'description': (
                    'Real users collected via our enrollment flow'
                ),
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} EvaluationDataset 'our_collection' (pk={dataset.pk})")

        for username in options['usernames']:
            user = User.objects.filter(username=username).first()
            if user is None:
                self.stderr.write(f"  User '{username}' not found — skipping.")
                continue

            sessions = list(
                BehaviorSession.objects
                .filter(user=user, is_enrollment=True)
                .exclude(ended_at=None)
                .order_by('started_at')
            )

            if not sessions:
                self.stderr.write(
                    f"  '{username}': no completed enrollment sessions — skipping."
                )
                continue

            all_features = []
            for session in sessions:
                try:
                    reps = extractor.extract_repetitions(session)
                    all_features.extend(reps)
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(f"  Session {session.id} failed: {exc}")

            if not all_features:
                self.stderr.write(
                    f"  '{username}': feature extraction yielded 0 vectors — skipping."
                )
                continue

            EvaluationSubject.objects.update_or_create(
                dataset=dataset,
                subject_id=username,
                defaults={
                    'feature_vectors': [asdict(f) for f in all_features],
                    'metadata': {
                        'n_sessions': len(sessions),
                        'n_repetitions': len(all_features),
                        'source': 'our_enrollment',
                    },
                },
            )
            self.stdout.write(
                f"  '{username}': {len(all_features)} vectors "
                f"from {len(sessions)} sessions."
            )

        self.stdout.write(
            self.style.SUCCESS("Done. Real users imported into 'our_collection'.")
        )
