"""
Big Mood Detector CLI

Main command-line interface following Clean Architecture principles.
All commands are properly organized in the interfaces layer.
"""

import click

from big_mood_detector.interfaces.cli.commands import predict_command, process_command
from big_mood_detector.interfaces.cli.labeling import unified_label_group as label_group
from big_mood_detector.interfaces.cli.server import serve_command
from big_mood_detector.interfaces.cli.watch import watch_command


@click.group()
@click.version_option()
def cli() -> None:
    """
    Big Mood Detector - Clinical mood prediction from health data.

    Analyze Apple Health data to detect patterns associated with
    mood episodes using validated ML models.
    """
    pass


# Register all commands
cli.add_command(process_command)
cli.add_command(predict_command)
cli.add_command(serve_command)
cli.add_command(watch_command)
cli.add_command(label_group)


@cli.command(name="train")
@click.option("--data", type=click.Path(exists=True), help="Training data")
@click.option("--labels", type=click.Path(exists=True), help="Ground truth labels")
def train_command(data: str, labels: str) -> None:
    """Train personalized models (coming soon)."""
    click.echo("🚧 Train command coming soon!")
    click.echo("This will enable personal model fine-tuning.")


if __name__ == "__main__":
    cli()
