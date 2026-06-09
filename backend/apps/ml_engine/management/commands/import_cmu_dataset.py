from __future__ import annotations

import random
from dataclasses import asdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.ml_engine.datasets.cmu_loader import load_cmu_subjects
from apps.ml_engine.models import EvaluationDataset, EvaluationSubject


class Command(BaseCommand):
    help = 'Import CMU Keystroke Dataset subjects into EvaluationDataset.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            required=True,
            help='Path to DSL-StrongPasswordData.csv',
        )
        parser.add_argument(
            '--n-subjects',
            type=int,
            default=15,
            help='How many subjects to import (randomly sampled, default 15)',
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=42,
            help='Random seed for reproducible subject selection (default 42)',
        )

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path'])
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        self.stdout.write(f"Loading CMU CSV from {csv_path} …")
        all_subjects = load_cmu_subjects(csv_path)
        self.stdout.write(f"Total CMU subjects in file: {len(all_subjects)}")

        n_subjects = options['n_subjects']
        if n_subjects > len(all_subjects):
            raise CommandError(
                f"Requested {n_subjects} subjects but only {len(all_subjects)} available."
            )

        random.seed(options['seed'])
        selected = sorted(random.sample(list(all_subjects.keys()), n_subjects))
        self.stdout.write(f"Selected ({n_subjects}, seed={options['seed']}): {selected}")

        dataset, created = EvaluationDataset.objects.update_or_create(
            name='cmu_keystroke',
            defaults={
                'description': (
                    'CMU Keystroke Dynamics Benchmark (Killourhy & Maxion 2009)'
                ),
                'source_url': 'https://www.cs.cmu.edu/~keystroke/',
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} EvaluationDataset 'cmu_keystroke' (pk={dataset.pk})")

        # Idempotent: clear previously imported subjects for this dataset.
        deleted_count, _ = EvaluationSubject.objects.filter(dataset=dataset).delete()
        if deleted_count:
            self.stdout.write(f"Cleared {deleted_count} existing subjects (re-import).")

        for subject_id in selected:
            features_list = all_subjects[subject_id]
            EvaluationSubject.objects.create(
                dataset=dataset,
                subject_id=subject_id,
                feature_vectors=[asdict(f) for f in features_list],
                metadata={
                    'n_repetitions': len(features_list),
                    'source': 'cmu',
                },
            )
            self.stdout.write(f"  {subject_id}: {len(features_list)} vectors")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Imported {len(selected)} subjects into "
                f"EvaluationDataset '{dataset.name}'."
            )
        )
